"""Context-aware cleaner / rebuilder.

The cleaner does *not* try to regex-patch a string into validity. Instead it:

1. Tokenizes the input with a forgiving character scanner that understands
   straight and curly quotes, JavaScript comments, Python/JS literals,
   non-standard numbers, bare identifiers and unterminated strings;
2. Rebuilds canonical JSON text from those tokens using a small grammar stack,
   inserting missing commas/colons, dropping trailing commas, and -- at the
   end (or at a closer) -- safely rolling an incomplete fragment back to the
   last complete element and closing every still-open bracket.

The output is balanced, properly quoted JSON even when the input was cut off
mid-token; :class:`~jsonmend.diagnostics.Change` records explain what changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from . import diagnostics as diag
from .diagnostics import Change

# Quote classes (straight + curly)
_DOUBLE = {'"', "\u201c", "\u201d"}
_SINGLE = {"'", "\u2018", "\u2019"}
_QUOTES = _DOUBLE | _SINGLE

_LITERALS = {
    "true": "true",
    "True": "true",
    "TRUE": "true",
    "false": "false",
    "False": "false",
    "FALSE": "false",
    "null": "null",
    "None": "null",
    "NULL": "null",
    "none": "null",
    "undefined": "null",
}
_NULL_WORDS = {"NaN", "nan", "Infinity", "infinity", "-Infinity", "+Infinity"}

_HEX = re.compile(r"^[0-9a-fA-F]+$")


@dataclass
class Token:
    kind: str  # '{','}','[',']',':',',','str','num','lit'
    value: Any = None
    pos: int = -1
    unclosed: bool = False
    bare: bool = False


# --------------------------------------------------------------------------- #
# String reading
# --------------------------------------------------------------------------- #
_SIMPLE_ESCAPES = {
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "\\": "\\",
    "/": "/",
    '"': '"',
    "'": "'",
}


def _read_string(s: str, i: int) -> Tuple[Token, List[Change]]:
    n = len(s)
    opener = s[i]
    quote_class = _DOUBLE if opener in _DOUBLE else _SINGLE
    is_single = opener in _SINGLE
    curly = opener not in ('"', "'")
    start = i
    i += 1
    buf: List[str] = []
    changes: List[Change] = []
    unclosed = False
    raw_control = False

    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 < n:
                nxt = s[i + 1]
                if nxt in _SIMPLE_ESCAPES:
                    buf.append(_SIMPLE_ESCAPES[nxt])
                    i += 2
                    continue
                if nxt in "uU" and i + 5 < n:
                    hexd = s[i + 2 : i + 6]
                    if _HEX.match(hexd):
                        try:
                            buf.append(chr(int(hexd, 16)))
                            i += 6
                            continue
                        except (ValueError, OverflowError):  # pragma: no cover
                            pass
                # Unknown escape: drop the backslash, keep the next char.
                buf.append(nxt)
                i += 2
                continue
            # Trailing backslash at EOF: drop it, string is unterminated.
            unclosed = True
            i += 1
            continue
        if c in quote_class:
            i += 1
            break
        if c in "\n\r\t":
            raw_control = True
            buf.append(c)
            i += 1
            continue
        buf.append(c)
        i += 1
    else:  # pragma: no cover - while/else guard
        unclosed = True
    if i >= n and not (i > start and s[i - 1] in quote_class):
        unclosed = True

    if curly:
        changes.append(Change(diag.SMART_QUOTES, start=start, end=i, before=opener, after='"'))
    if is_single:
        changes.append(Change(diag.SINGLE_QUOTES, start=start, end=i))
    if raw_control:
        changes.append(Change(diag.CONTROL_CHAR, start=start, end=i))
    if unclosed:
        changes.append(Change(diag.UNCLOSED_STRING, start=start, end=i))
    return Token("str", "".join(buf), start, unclosed=unclosed), changes


# --------------------------------------------------------------------------- #
# Identifier / number reading
# --------------------------------------------------------------------------- #
def _read_identifier(s: str, i: int) -> Tuple[Token, List[Change]]:
    n = len(s)
    start = i
    j = i
    # A leading sign is only consumed when it introduces a word such as
    # +Infinity or -NaN.
    if s[j] in "+-" and j + 1 < n and s[j + 1].isalpha():
        j += 1
    while j < n and (s[j].isalnum() or s[j] == "_"):
        j += 1
    word = s[start:j]
    changes: List[Change] = []

    if word in _LITERALS:
        mapped = _LITERALS[word]
        if word not in ("true", "false", "null"):
            changes.append(
                Change(diag.LITERAL_NORMALIZED, start=start, end=j, before=word, after=mapped)
            )
        return Token("lit", mapped, start), changes
    if word.lstrip("+-") in {"NaN", "nan", "Infinity", "infinity"}:
        changes.append(Change(diag.NULL_SUBSTITUTED, start=start, end=j, before=word, after="null"))
        return Token("lit", "null", start), changes

    changes.append(Change(diag.BARE_KEY, start=start, end=j, before=word, after=f'"{word}"'))
    return Token("str", word, start, bare=True), changes


def _read_number(s: str, i: int) -> Tuple[Token, List[Change]]:
    n = len(s)
    start = i
    j = i
    if s[j] in "+-":
        j += 1
    # Hex / octal / binary prefixed forms.
    if j + 1 < n and s[j] == "0" and s[j + 1] in "xXoObB":
        p = s[j + 1]
        k = j + 2
        allowed = "0123456789abcdefABCDEF" if p in "xX" else (
            "01234567" if p in "oO" else "01"
        )
        while k < n and s[k] in allowed:
            k += 1
        raw = s[start:k]
        base = 16 if p in "xX" else (8 if p in "oO" else 2)
        try:
            val = int(raw.lstrip("+-"), base)
            if raw.startswith("-"):
                val = -val
            normalized = str(val)
        except ValueError:
            normalized = "0"
        changes = [Change(diag.NUMBER_NORMALIZED, start=start, end=k, before=raw, after=normalized)]
        return Token("num", normalized, start), changes

    while j < n and s[j].isdigit():
        j += 1
    is_float = False
    if j < n and s[j] == ".":
        is_float = True
        j += 1
        while j < n and s[j].isdigit():
            j += 1
    if j < n and s[j] in "eE":
        is_float = True
        j += 1
        if j < n and s[j] in "+-":
            j += 1
        while j < n and s[j].isdigit():
            j += 1
    raw = s[start:j] or "0"
    changes: List[Change] = []
    try:
        if is_float:
            normalized = repr(float(raw))
            if normalized in ("inf", "-inf", "nan"):
                changes.append(Change(diag.NULL_SUBSTITUTED, before=raw, after="null"))
                normalized = "null"
                return Token("lit", "null", start), changes
        else:
            normalized = str(int(raw, 10))
    except ValueError:
        normalized = "0"
    if normalized != raw and not (raw.startswith("+") and normalized == raw[1:]):
        changes.append(Change(diag.NUMBER_NORMALIZED, start=start, end=j, before=raw, after=normalized))
    elif raw.startswith("+"):
        changes.append(Change(diag.NUMBER_NORMALIZED, start=start, end=j, before=raw, after=normalized))
    return Token("num", normalized, start), changes


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #
def tokenize(s: str) -> Tuple[List[Token], List[Change]]:
    n = len(s)
    tokens: List[Token] = []
    changes: List[Change] = []
    i = 0
    while i < n:
        c = s[i]
        if c in " \t\r\n":
            i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = i + 2
            while j < n and s[j] != "\n":
                j += 1
            changes.append(Change(diag.REMOVED_COMMENT, start=i, end=j, before=s[i:j]))
            i = j
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = i + 2
            while j + 1 < n and not (s[j] == "*" and s[j + 1] == "/"):
                j += 1
            j = min(n, j + 2)
            changes.append(Change(diag.REMOVED_COMMENT, start=i, end=j, before=s[i:j]))
            i = j
            continue
        if c in "{[}]:,":
            tokens.append(Token(c, None, i))
            i += 1
            continue
        if c in _QUOTES:
            t, ch = _read_string(s, i)
            tokens.append(t)
            changes.extend(ch)
            i = _advance_after_string(s, i)
            continue
        if c.isalpha() or c == "_" or (c in "+-" and i + 1 < n and s[i + 1].isalpha()):
            t, ch = _read_identifier(s, i)
            tokens.append(t)
            changes.extend(ch)
            i = _end_of_word(s, i)
            continue
        if c.isdigit() or c in "+-.":
            t, ch = _read_number(s, i)
            tokens.append(t)
            changes.extend(ch)
            i = _end_of_number(s, t.pos, t.kind)
            continue
        # Unrecognized character: skip it (do not emit into JSON).
        i += 1
    return tokens, changes


def _advance_after_string(s: str, start: int) -> int:
    """Re-walk a string token to find the offset just past it."""
    n = len(s)
    opener = s[start]
    qclass = _DOUBLE if opener in _DOUBLE else _SINGLE
    i = start + 1
    while i < n:
        if s[i] == "\\":
            i += 2
            continue
        if s[i] in qclass:
            return i + 1
        i += 1
    return n


def _end_of_word(s: str, start: int) -> int:
    j = start
    if s[j] in "+-" and j + 1 < len(s) and s[j + 1].isalpha():
        j += 1
    while j < len(s) and (s[j].isalnum() or s[j] == "_"):
        j += 1
    return j


def _end_of_number(s: str, start: int, kind: str) -> int:
    n = len(s)
    j = start
    if s[j] in "+-":
        j += 1
    if j + 1 < n and s[j] == "0" and s[j + 1] in "xXoObB":
        p = s[j + 1]
        k = j + 2
        allowed = "0123456789abcdefABCDEF" if p in "xX" else (
            "01234567" if p in "oO" else "01"
        )
        while k < n and s[k] in allowed:
            k += 1
        return k
    while j < n and s[j].isdigit():
        j += 1
    if j < n and s[j] == ".":
        j += 1
        while j < n and s[j].isdigit():
            j += 1
    if j < n and s[j] in "eE":
        j += 1
        if j < n and s[j] in "+-":
            j += 1
        while j < n and s[j].isdigit():
            j += 1
    return j


# --------------------------------------------------------------------------- #
# Rebuilder
# --------------------------------------------------------------------------- #
@dataclass
class Frame:
    kind: str  # 'object' | 'array'
    state: str
    safe_len: int
    pending_comma: bool = False
    just_colon: bool = False


def _encode_string(value: str) -> str:
    import json

    return json.dumps(value, ensure_ascii=False)


def clean(s: str) -> Tuple[str, List[Change]]:
    """Repair a single JSON-ish fragment into canonical JSON text."""
    tokens, changes = tokenize(s)
    out: List[str] = []
    stack: List[Frame] = []

    def emit(v: str) -> None:
        out.append(v)

    def emit_value(t: Token) -> None:
        if t.kind == "str":
            emit(_encode_string(t.value))
        elif t.kind == "num":
            emit(str(t.value))
        elif t.kind == "lit":
            emit(str(t.value))

    def rollback(f: Frame, code: str, pos: int) -> None:
        if len(out) > f.safe_len:
            before = "".join(out[f.safe_len :])
            del out[f.safe_len :]
            changes.append(Change(code, start=pos, before=before, after=""))

    def finalize_top(closer_from_input: bool, pos: int) -> None:
        f = stack[-1]
        if f.kind == "object":
            if f.state == "want_key" and f.pending_comma:
                rollback(f, diag.TRAILING_COMMA, pos)
            elif f.state == "want_value" and f.just_colon:
                rollback(f, diag.DROPPED_TAIL, pos)
        else:
            if f.state == "want_value" and f.pending_comma:
                rollback(f, diag.TRAILING_COMMA, pos)
        closer = "}" if f.kind == "object" else "]"
        emit(closer)
        if not closer_from_input:
            changes.append(Change(diag.BRACKET_CLOSED, start=pos, before="", after=closer))
        stack.pop()
        p = stack[-1] if stack else None
        if p is not None:
            if p.kind == "array" and p.state == "want_value":
                p.state = "after_value"
                p.safe_len = len(out)
                p.pending_comma = False
            elif p.kind == "object" and p.state == "want_value":
                p.state = "after_value"
                p.safe_len = len(out)
                p.just_colon = False

    k = 0
    while k < len(tokens):
        t = tokens[k]
        kind = t.kind
        f = stack[-1] if stack else None

        # --- openers ---
        if kind in ("{", "["):
            target = "object" if kind == "{" else "array"
            if f is not None and f.state == "after_value":
                if f.kind == "array":
                    emit(",")
                    changes.append(Change(diag.MISSING_COMMA, start=t.pos))
                    f.state = "want_value"
                else:
                    emit(",")
                    changes.append(Change(diag.MISSING_COMMA, start=t.pos))
                    f.state = "want_value"
            emit("{" if kind == "{" else "[")
            init_state = "want_key" if target == "object" else "want_value"
            stack.append(Frame(target, init_state, len(out)))
            k += 1
            continue

        # --- closers ---
        if kind in ("}", "]"):
            target = "object" if kind == "}" else "array"
            if f is None:
                k += 1
                continue
            if f.kind != target:
                # Close inner frames until the matching kind is on top.
                guard = 0
                while stack and stack[-1].kind != target and guard < 1000:
                    finalize_top(False, t.pos)
                    guard += 1
                if stack and stack[-1].kind == target:
                    finalize_top(True, t.pos)
                k += 1
                continue
            finalize_top(True, t.pos)
            k += 1
            continue

        # --- comma ---
        if kind == ",":
            if f is not None and f.state == "after_value":
                emit(",")
                f.pending_comma = True
                f.state = "want_key" if f.kind == "object" else "want_value"
            # duplicate / misplaced commas are ignored
            k += 1
            continue

        # --- colon ---
        if kind == ":":
            if f is not None and f.kind == "object" and f.state == "want_colon":
                emit(":")
                f.state = "want_value"
                f.just_colon = True
            k += 1
            continue

        # --- value / key tokens ---
        if f is None:
            emit_value(t)
            k += 1
            continue

        if f.kind == "object":
            if f.state == "want_key":
                key = t.value if kind == "str" else _scalar_to_key(t)
                emit(_encode_string(str(key)))
                f.state = "want_colon"
                # Consume an optional following colon, or insert one.
                if k + 1 < len(tokens) and tokens[k + 1].kind == ":":
                    emit(":")
                    f.state = "want_value"
                    f.just_colon = True
                    k += 2
                    continue
                emit(":")
                changes.append(Change(diag.MISSING_COLON, start=t.pos))
                f.state = "want_value"
                f.just_colon = True
                k += 1
                continue
            if f.state == "want_value":
                emit_value(t)
                f.state = "after_value"
                f.safe_len = len(out)
                f.just_colon = False
                f.pending_comma = False
                k += 1
                continue
            # after_value: a string starts a new key; anything else is a value.
            emit(",")
            changes.append(Change(diag.MISSING_COMMA, start=t.pos))
            if kind == "str":
                f.state = "want_key"
            else:
                f.state = "want_value"
            continue

        # array
        if f.state == "want_value":
            emit_value(t)
            f.state = "after_value"
            f.safe_len = len(out)
            f.pending_comma = False
            k += 1
            continue
        # after_value: insert a comma then the value.
        emit(",")
        changes.append(Change(diag.MISSING_COMMA, start=t.pos))
        f.state = "want_value"

    # EOF: force-close every remaining frame.
    while stack:
        finalize_top(False, len(s))

    return "".join(out), changes


def _scalar_to_key(t: Token) -> str:
    if t.kind == "lit":
        return str(t.value)
    if t.kind == "num":
        return str(t.value)
    return str(t.value)
