"""Diagnostic data structures for jsonmend.

Every repair is recorded as a :class:`Change` so that the otherwise
"black box" process of fixing broken JSON becomes explainable. The codes
below are stable and may be matched programmatically (for example in CI).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# Stable fix codes
# --------------------------------------------------------------------------- #
REMOVED_FENCE = "removed_fence"
REMOVED_COMMENT = "removed_comment"
SINGLE_QUOTES = "single_quotes_to_double"
SMART_QUOTES = "smart_quotes_normalized"
TRAILING_COMMA = "trailing_comma_removed"
BARE_KEY = "bare_key_quoted"
LITERAL_NORMALIZED = "literal_normalized"
NUMBER_NORMALIZED = "number_normalized"
MISSING_COMMA = "missing_comma_added"
MISSING_COLON = "missing_colon_added"
CONTROL_CHAR = "control_char_escaped"
NULL_SUBSTITUTED = "null_substituted"
UNCLOSED_STRING = "unterminated_string_closed"
BRACKET_CLOSED = "bracket_closed"
DROPPED_TAIL = "incomplete_tail_dropped"
SCHEMA_COERCED = "schema_value_coerced"
SCHEMA_DEFAULT = "schema_default_added"
SCHEMA_ENUM = "schema_enum_fixed"
SCHEMA_MISSING = "schema_required_missing"

MINOR = "minor"
MAJOR = "major"

# Human readable (English) descriptions for each code.
_CODE_TEXT = {
    REMOVED_FENCE: "Removed a Markdown code fence",
    REMOVED_COMMENT: "Removed a JavaScript-style comment",
    SINGLE_QUOTES: "Converted single-quoted strings to double quotes",
    SMART_QUOTES: "Normalized curly/smart quotes to straight quotes",
    TRAILING_COMMA: "Removed a trailing comma",
    BARE_KEY: "Quoted a bare object key",
    LITERAL_NORMALIZED: "Normalized a Python/JS literal to a JSON literal",
    NUMBER_NORMALIZED: "Normalized a non-standard number",
    MISSING_COMMA: "Inserted a missing comma",
    MISSING_COLON: "Inserted a missing colon",
    CONTROL_CHAR: "Escaped a raw control character inside a string",
    NULL_SUBSTITUTED: "Substituted an unsupported value with null",
    UNCLOSED_STRING: "Closed an unterminated string",
    BRACKET_CLOSED: "Closed an unbalanced array/object",
    DROPPED_TAIL: "Dropped an incomplete trailing fragment",
    SCHEMA_COERCED: "Coerced a value to the schema type",
    SCHEMA_DEFAULT: "Filled a missing field with its schema default",
    SCHEMA_ENUM: "Adjusted a value to the nearest enum member",
    SCHEMA_MISSING: "A required field is missing",
}

# Which codes are considered "major" (more destructive) for confidence.
_MAJOR_CODES = {
    UNCLOSED_STRING,
    BRACKET_CLOSED,
    DROPPED_TAIL,
    NULL_SUBSTITUTED,
    SCHEMA_MISSING,
}


@dataclass
class Change:
    """A single repair applied to the input."""

    code: str
    message: str = ""
    start: int = -1
    end: int = -1
    severity: str = MINOR
    before: str = ""
    after: str = ""

    def __post_init__(self) -> None:
        if not self.message:
            self.message = _CODE_TEXT.get(self.code, self.code)
        if not self.severity or self.severity == MINOR:
            self.severity = MAJOR if self.code in _MAJOR_CODES else MINOR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "start": self.start,
            "end": self.end,
            "severity": self.severity,
            "before": self.before,
            "after": self.after,
        }


@dataclass
class SchemaIssue:
    path: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "code": self.code, "message": self.message}


@dataclass
class MendResult:
    """The full outcome of a mend operation."""

    value: Any = None
    ok: bool = False
    repaired: bool = False
    confidence: float = 1.0
    changes: List[Change] = field(default_factory=list)
    schema_issues: List[SchemaIssue] = field(default_factory=list)
    candidates: int = 0
    chosen: int = -1
    error: Optional[str] = None

    @property
    def change_codes(self) -> List[str]:
        return [c.code for c in self.changes]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "repaired": self.repaired,
            "confidence": round(self.confidence, 4),
            "value": self.value,
            "candidates": self.candidates,
            "chosen": self.chosen,
            "changes": [c.to_dict() for c in self.changes],
            "schema_issues": [s.to_dict() for s in self.schema_issues],
            "error": self.error,
        }


def confidence_for(changes: List[Change], schema_issues: Optional[List[SchemaIssue]] = None) -> float:
    """Derive a 0..1 confidence from the applied changes."""
    score = 1.0
    for ch in changes:
        score -= 0.08 if ch.severity == MAJOR else 0.02
    score -= 0.03 * len(schema_issues or [])
    if changes:
        score = min(score, 0.99)
    return max(0.0, round(score, 4))
