"""Character-level scanning and JSON candidate extraction.

LLMs rarely return *just* JSON. They wrap it in Markdown fences, surround it
with prose, and sometimes emit several JSON blobs. This module:

* detects `````json ... ````` fenced blocks (including a fence that was cut
  off mid-stream);
* performs a single, string/comment-aware structural scan to locate balanced
  ``{...}`` / ``[...]`` spans and any unbalanced (truncated) outer span;
* returns ranked :class:`Candidate` regions for the repair pipeline.

The scanner never uses regex to match braces, so braces that legitimately
appear inside strings or comments cannot confuse it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Quote classes (straight + curly). Open and close of the same class.
_DOUBLE_QUOTES = {'"', "\u201c", "\u201d"}
_SINGLE_QUOTES = {"'", "\u2018", "\u2019"}
_ALL_QUOTES = _DOUBLE_QUOTES | _SINGLE_QUOTES

_FENCE_OPEN = re.compile(r"(?m)^[ \t]{0,3}```[ \t]*([A-Za-z0-9_.+-]*)[ \t]*\r?\n")
_FENCE_CLOSE = re.compile(r"(?m)^[ \t]{0,3}```[ \t]*\r?$")
# A bare (braceless) fragment is only a JSON candidate if it already looks like
# a legal JSON scalar -- a number, true/false/null, or a quoted string -- so
# plain prose such as "hello" is not mistaken for JSON.
_SCALAR_RE = re.compile(
    r"^(?:"
    r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|"
    r"true|false|null|"
    r'"(?:[^"\\]|\\.)*"|'
    r"'(?:[^'\\]|\\.)*'"
    r")$"
)


@dataclass
class Candidate:
    """A region of the original text that might contain JSON."""

    text: str
    start: int
    end: int
    complete: bool
    fenced: bool = False
    lang: str = ""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        kind = "fenced" if self.fenced else "structural"
        state = "complete" if self.complete else "partial"
        return f"<Candidate {kind} {state} [{self.start}:{self.end}]>"


# --------------------------------------------------------------------------- #
# Low level structural scan
# --------------------------------------------------------------------------- #
def structural_spans(text: str) -> Tuple[List[Tuple[int, int]], Optional[Tuple[int, int]]]:
    """Return (complete outer spans, optional partial outer span).

    Coordinates are offsets into ``text``; complete spans use exclusive ends.
    A partial span is an outer opener whose matching closer never arrived.
    """
    complete: List[Tuple[int, int]] = []
    stack: List[Tuple[str, int]] = []
    root = -1

    n = len(text)
    i = 0
    while i < n:
        ch = text[i]

        # --- strings ---
        if ch in _ALL_QUOTES:
            quote_class = _DOUBLE_QUOTES if ch in _DOUBLE_QUOTES else _SINGLE_QUOTES
            i += 1
            while i < n:
                c = text[i]
                if c == "\\":
                    i += 2
                    continue
                if c in quote_class:
                    i += 1
                    break
                i += 1
            continue

        # --- line comment ---
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] != "\n":
                i += 1
            continue

        # --- block comment ---
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        # --- openers / closers ---
        if ch in "{[":
            if not stack:
                root = i
            stack.append((ch, i))
        elif ch in "}]":
            want = "{" if ch == "}" else "["
            if stack and stack[-1][0] == want:
                stack.pop()
                if not stack:
                    complete.append((root, i + 1))
            elif stack:
                # Mismatched closer: recover by finding a matching opener.
                depth = next(
                    (d for d in range(len(stack) - 1, -1, -1) if stack[d][0] == want),
                    None,
                )
                if depth is not None:
                    del stack[depth:]
                    if not stack:
                        complete.append((root, i + 1))
                # a truly stray closer is ignored.
        i += 1

    partial = None
    if stack:
        outer = stack[0][1]
        partial = (outer, n)
    return complete, partial


# --------------------------------------------------------------------------- #
# Markdown fences
# --------------------------------------------------------------------------- #
def fence_spans(text: str) -> List[Candidate]:
    spans: List[Candidate] = []
    pos = 0
    while True:
        m = _FENCE_OPEN.search(text, pos)
        if not m:
            break
        content_start = m.end()
        closer = _FENCE_CLOSE.search(text, content_start)
        lang = m.group(1).lower()
        if closer is not None:
            body = text[content_start : closer.start()]
            rtrim = body.rstrip()
            shift = len(body) - len(rtrim)
            spans.append(
                Candidate(
                    text=rtrim.strip(),
                    start=content_start,
                    end=closer.start() - shift,
                    complete=True,
                    fenced=True,
                    lang=lang,
                )
            )
            pos = closer.end()
        else:
            body = text[content_start:]
            rtrim = body.rstrip()
            spans.append(
                Candidate(
                    text=rtrim.strip(),
                    start=content_start,
                    end=len(text),
                    complete=False,
                    fenced=True,
                    lang=lang,
                )
            )
            pos = len(text)
    return spans


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def find_candidates(text: str, *, fenced_only: bool = False) -> List[Candidate]:
    """Locate JSON candidates, fenced blocks taking priority."""
    if not text or not text.strip():
        return []

    fences = fence_spans(text)
    if fences:
        return fences

    if fenced_only:
        return []

    complete, partial = structural_spans(text)
    candidates: List[Candidate] = []
    for start, end in complete:
        candidates.append(
            Candidate(text=text[start:end], start=start, end=end, complete=True)
        )
    if candidates:
        return candidates

    if partial is not None:
        start, end = partial
        candidates.append(
            Candidate(text=text[start:end], start=start, end=end, complete=False)
        )
        return candidates

    # No structural braces at all: accept only a genuine JSON scalar
    # (number / true / false / null / quoted string), never bare prose.
    stripped = text.strip()
    if stripped and _SCALAR_RE.match(stripped):
        offset = text.find(stripped)
        candidates.append(
            Candidate(text=stripped, start=offset, end=offset + len(stripped), complete=True)
        )
    return candidates
