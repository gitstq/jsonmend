"""Truncation analysis and standalone completion helpers.

Streaming agents frequently emit JSON that ends mid-string, mid-token or with
a dangling comma/colon. The main repair path goes through the tokenizer, but
this module provides:

* :func:`analyze` - a string/comment-aware bracket/string state analysis;
* :func:`is_complete` - whether the text already forms complete JSON;
* :func:`complete_simple` - a small, dependency-free completion used by tools
  and mirrored by the browser playground.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from . import diagnostics as diag
from .diagnostics import Change


def analyze(text: str) -> Tuple[List[str], Optional[str]]:
    """Return (unclosed openers, open quote char).

    ``unclosed openers`` lists the still-open ``{`` / ``[`` characters from
    outermost to innermost. ``open quote`` is the quote that was never closed.
    """
    stack: List[str] = []
    in_str: Optional[str] = None
    n = len(text)
    i = 0
    while i < n:
        c = text[i]
        if in_str is not None:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
            i += 1
            continue
        if c in "\"'":
            in_str = c
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c in "{[":
            stack.append(c)
        elif c in "}]":
            want = "{" if c == "}" else "["
            if stack and stack[-1] == want:
                stack.pop()
            elif stack and want in stack:
                del stack[stack.index(want) :]
        i += 1
    return stack, in_str


def is_complete(text: str) -> bool:
    stack, in_str = analyze(text)
    return not stack and in_str is None


def complete_simple(text: str) -> Tuple[str, List[Change]]:
    """Close an open string and dangling brackets with safe tail handling."""
    changes: List[Change] = []
    work = text

    stack, in_str = analyze(work)
    if in_str is not None:
        if work.endswith("\\"):
            work = work[:-1]
        work += in_str
        changes.append(Change(diag.UNCLOSED_STRING, before="", after=in_str))

    work = work.rstrip()
    while work and work[-1] in ",:":
        if work[-1] == ",":
            work = work[:-1].rstrip()
            changes.append(Change(diag.TRAILING_COMMA, before=",", after=""))
        else:
            cut = max(work.rfind("{"), work.rfind(","), work.rfind("["))
            before = work[cut + 1 :] if cut >= 0 else work
            work = work[: cut + 1] if cut >= 0 else ""
            changes.append(Change(diag.DROPPED_TAIL, before=before, after=""))
        work = work.rstrip()

    stack, _ = analyze(work)
    closers = {"{": "}", "[": "]"}
    tail = "".join(closers[c] for c in reversed(stack))
    if tail:
        changes.append(Change(diag.BRACKET_CLOSED, before="", after=tail))
    return work + tail, changes
