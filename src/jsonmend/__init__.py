"""jsonmend — mend the broken JSON that LLMs/agents return.

Extract JSON from Markdown fences and prose, fix quotes/comments/trailing
commas/literals, complete truncated or streaming JSON, and optionally coerce
the result to a JSON Schema. **Zero third-party dependencies.**

Quick usage::

    from jsonmend import mend

    value = mend('Here you go:\\n```json\\n{"a": 1, "b": 2,}\\n```')
    # -> {"a": 1, "b": 2}
"""

from __future__ import annotations

from .diagnostics import (
    Change,
    MendResult,
    SchemaIssue,
)
from .mend import extract_json, loads, loads_many, mend, mend_file
from .streaming import StreamMender, feed_stream, iter_jsonl

__version__ = "1.0.0"

__all__ = [
    "mend",
    "loads",
    "loads_many",
    "extract_json",
    "mend_file",
    "StreamMender",
    "feed_stream",
    "iter_jsonl",
    "MendResult",
    "Change",
    "SchemaIssue",
    "__version__",
]
