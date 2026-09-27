"""A small tolerant recursive-descent parser (fallback).

The repair pipeline normally produces text that the standard ``json`` module
parses directly. If that ever fails, this hand-written parser is used as a
safety net. It understands straight quotes (single or double), JavaScript
comments, trailing commas, Python/JS literals and common number forms.
"""

from __future__ import annotations

from typing import Any

_ESCAPES = {
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
_WORDS = {
    "true": True,
    "True": True,
    "false": False,
    "False": False,
    "null": None,
    "None": None,
    "undefined": None,
}


class TolerantParser:
    def __init__(self, text: str) -> None:
        self.s = text
        self.n = len(text)
        self.i = 0

    # ------------------------------------------------------------------ #
    def parse(self) -> Any:
        self._skip()
        value = self._value()
        return value

    def _skip(self) -> None:
        while self.i < self.n:
            c = self.s[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif c == "/" and self.i + 1 < self.n and self.s[self.i + 1] == "/":
                while self.i < self.n and self.s[self.i] != "\n":
                    self.i += 1
            elif c == "/" and self.i + 1 < self.n and self.s[self.i + 1] == "*":
                self.i += 2
                while self.i + 1 < self.n and not (
                    self.s[self.i] == "*" and self.s[self.i + 1] == "/"
                ):
                    self.i += 1
                self.i += 2
            else:
                return

    def _peek(self) -> str:
        return self.s[self.i] if self.i < self.n else ""

    # ------------------------------------------------------------------ #
    def _value(self) -> Any:
        c = self._peek()
        if c == "{":
            return self._object()
        if c == "[":
            return self._array()
        if c in "\"'":
            return self._string()
        if c.isdigit() or c in "+-.":
            return self._number()
        if c.isalpha() or c == "_":
            return self._word()
        # Cannot make sense of it: advance to avoid an infinite loop.
        self.i += 1
        return None

    def _object(self) -> dict:
        self.i += 1  # {
        obj: dict = {}
        while True:
            self._skip()
            if self._peek() == "}":
                self.i += 1
                return obj
            if self._peek() in "\"'":
                key = self._string()
            else:
                key = str(self._value())
            self._skip()
            if self._peek() == ":":
                self.i += 1
            self._skip()
            obj[key] = self._value()
            self._skip()
            if self._peek() == ",":
                self.i += 1
                self._skip()
                if self._peek() == "}":  # trailing comma
                    self.i += 1
                    return obj
            elif self._peek() == "}":
                self.i += 1
                return obj

    def _array(self) -> list:
        self.i += 1  # [
        arr: list = []
        while True:
            self._skip()
            if self._peek() == "]":
                self.i += 1
                return arr
            arr.append(self._value())
            self._skip()
            if self._peek() == ",":
                self.i += 1
                self._skip()
                if self._peek() == "]":  # trailing comma
                    self.i += 1
                    return arr
            elif self._peek() == "]":
                self.i += 1
                return arr

    def _string(self) -> str:
        quote = self.s[self.i]
        self.i += 1
        buf = []
        while self.i < self.n:
            c = self.s[self.i]
            if c == "\\":
                nxt = self.s[self.i + 1] if self.i + 1 < self.n else ""
                if nxt in _ESCAPES:
                    buf.append(_ESCAPES[nxt])
                    self.i += 2
                    continue
                if nxt in "uU" and self.i + 5 < self.n:
                    hexd = self.s[self.i + 2 : self.i + 6]
                    try:
                        buf.append(chr(int(hexd, 16)))
                        self.i += 6
                        continue
                    except ValueError:
                        pass
                buf.append(nxt)
                self.i += 2
                continue
            if c == quote:
                self.i += 1
                return "".join(buf)
            buf.append(c)
            self.i += 1
        return "".join(buf)  # unterminated

    def _number(self) -> Any:
        start = self.i
        if self.s[self.i] in "+-":
            self.i += 1
        if self.i + 1 < self.n and self.s[self.i] == "0" and self.s[self.i + 1] in "xXoObB":
            p = self.s[self.i + 1]
            self.i += 2
            allowed = "0123456789abcdefABCDEF" if p in "xX" else (
                "01234567" if p in "oO" else "01"
            )
            while self.i < self.n and self.s[self.i] in allowed:
                self.i += 1
            raw = self.s[start : self.i]
            base = 16 if p in "xX" else (8 if p in "oO" else 2)
            try:
                return int(raw.lstrip("+-"), base) * (-1 if raw.startswith("-") else 1)
            except ValueError:
                return 0
        while self.i < self.n and self.s[self.i].isdigit():
            self.i += 1
        is_float = False
        if self._peek() == ".":
            is_float = True
            self.i += 1
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        if self._peek() in "eE":
            is_float = True
            self.i += 1
            if self._peek() in "+-":
                self.i += 1
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
        raw = self.s[start : self.i]
        try:
            return float(raw) if is_float else int(raw, 10)
        except ValueError:
            return 0

    def _word(self) -> Any:
        start = self.i
        while self.i < self.n and (self.s[self.i].isalnum() or self.s[self.i] == "_"):
            self.i += 1
        word = self.s[start : self.i]
        if word in _WORDS:
            return _WORDS[word]
        if word.lstrip("+-") in {"NaN", "Infinity"}:
            return None
        return word  # bare word treated as a string value


def parse(text: str) -> Any:
    """Parse tolerant JSON, raising ``ValueError`` only on an empty input."""
    if not text or not text.strip():
        raise ValueError("empty input")
    return TolerantParser(text).parse()
