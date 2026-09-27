"""Incremental repair for partial, streaming JSON.

Agents that stream tokens (SSE, tool-use deltas) produce JSON that is only
valid *once complete*. :class:`StreamMender` keeps a growing buffer and, after
each chunk, returns the best value it can derive from the prefix -- already
finished elements are available immediately, and the unfinished tail is safely
handled. Once the structure closes naturally, ``complete`` becomes true.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator, List, Optional

from . import diagnostics as diag
from .diagnostics import MendResult

_TRUNCATION_CODES = {diag.BRACKET_CLOSED, diag.DROPPED_TAIL}


class StreamMender:
    """Accumulate chunks and expose the current best value."""

    def __init__(self, schema: Optional[dict] = None, *, coerce: bool = True) -> None:
        self.buffer = ""
        self.schema = schema
        self.coerce = coerce
        self._last: Optional[MendResult] = None

    # ------------------------------------------------------------------ #
    def feed(self, chunk: str) -> Any:
        """Append ``chunk`` and return the best value derivable so far."""
        # Local import to avoid a module cycle.
        from .mend import mend

        self.buffer += chunk
        result = mend(
            self.buffer,
            schema=self.schema,
            coerce=self.coerce,
            return_report=True,
        )
        self._last = result
        return result.value

    @property
    def complete(self) -> bool:
        """True only when the buffer already forms complete JSON on its own."""
        if self._last is None or not self._last.ok:
            return False
        return not any(c in _TRUNCATION_CODES for c in self._last.change_codes)

    def finish(self) -> MendResult:
        """Finalize and return the full :class:`MendResult`."""
        from .mend import mend

        result = mend(self.buffer, schema=self.schema, coerce=self.coerce, return_report=True)
        self._last = result
        return result


def feed_stream(
    chunks: Iterable[str], schema: Optional[dict] = None
) -> Iterator[Any]:
    """Yield the current best value after each incoming chunk."""
    mender = StreamMender(schema=schema)
    for chunk in chunks:
        yield mender.feed(chunk)


def iter_jsonl(lines: Iterable[str], schema: Optional[dict] = None) -> Iterator[Any]:
    """Parse one (possibly dirty) JSON document per line, JSONL style."""
    from .mend import mend

    for line in lines:
        if not line.strip():
            continue
        result = mend(line, schema=schema, return_report=True)
        if result.ok:
            yield result.value
