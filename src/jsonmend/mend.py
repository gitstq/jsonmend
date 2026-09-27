"""High-level orchestration for jsonmend.

Public functions:

* :func:`mend` / :func:`loads` - repair one JSON document;
* :func:`loads_many` - repair every JSON document in the text;
* :func:`extract_json` - return raw candidate fragments;
* :func:`mend_file` - read a file and repair it.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, Tuple

from . import diagnostics as diag
from . import schema as schema_mod
from .cleaner import clean
from .diagnostics import Change, MendResult
from .parser import parse as tolerant_parse
from .scanner import Candidate, find_candidates


# --------------------------------------------------------------------------- #
# Single candidate repair
# --------------------------------------------------------------------------- #
def _reject_constant(name: str) -> Any:
    # NaN / Infinity / -Infinity are Python-accepted but not standard JSON.
    raise ValueError(f"non-standard constant: {name}")


def _repair_candidate(cand: Candidate) -> Tuple[Any, List[Change], bool, Optional[str]]:
    text = cand.text
    try:  # already valid standard JSON?
        return json.loads(text, parse_constant=_reject_constant), [], True, None
    except Exception:
        pass
    cleaned, changes = clean(text)
    try:
        return json.loads(cleaned, parse_constant=_reject_constant), changes, True, None
    except Exception as exc:
        try:
            return tolerant_parse(cleaned), changes, True, None
        except Exception:
            return None, changes, False, str(exc)


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def mend(
    source: str,
    *,
    schema: Optional[dict] = None,
    coerce: bool = True,
    strict: bool = False,
    many: bool = False,
    return_report: bool = False,
) -> Any:
    """Repair broken JSON text and return the Python value.

    With ``return_report=True`` a :class:`~jsonmend.diagnostics.MendResult`
    is returned instead. With ``strict=True`` no repair is attempted.
    """
    text = source if isinstance(source, str) else str(source)

    if strict:
        result = MendResult()
        try:
            result.value = json.loads(text)
            result.ok = True
            result.confidence = 1.0
        except Exception as exc:
            result.ok = False
            result.error = str(exc)
            result.confidence = 0.0
        return result if return_report else (_safe(result))

    candidates = find_candidates(text)
    repaired: List[Tuple[Candidate, Any, List[Change], bool, Optional[str], int]] = []
    for idx, cand in enumerate(candidates):
        value, changes, ok, error = _repair_candidate(cand)
        if cand.fenced:
            changes = [Change(diag.REMOVED_FENCE, start=cand.start)] + changes
        repaired.append((cand, value, changes, ok, error, idx))

    ok_results = [r for r in repaired if r[3]]

    if many:
        values = [r[1] for r in ok_results]
        all_changes: List[Change] = [c for r in ok_results for c in r[2]]
        result = MendResult(
            value=values,
            ok=bool(ok_results),
            repaired=bool(all_changes),
            confidence=diag.confidence_for(all_changes),
            changes=all_changes,
            candidates=len(candidates),
        )
        return result if return_report else values

    if not ok_results:
        last_error = next((r[4] for r in reversed(repaired) if r[4]), "no JSON found")
        result = MendResult(
            ok=False,
            confidence=0.0,
            candidates=len(candidates),
            error=last_error,
        )
        if return_report:
            return result
        raise ValueError(f"jsonmend could not recover JSON: {last_error}")

    def rank(r: Tuple[Candidate, Any, List[Change], bool, Optional[str], int]) -> tuple:
        cand, value, changes, _ok, _err, _idx = r
        if schema is not None:
            return (
                -round(schema_mod.match_score(value, schema), 4),
                len(changes),
                -len(cand.text),
            )
        return (len(changes), -len(cand.text))

    chosen = min(ok_results, key=rank)
    cand, value, changes, _ok, _err, chosen_idx = chosen

    schema_issues = []
    if schema is not None and coerce:
        value, schema_issues, sch_changes = schema_mod.coerce(value, schema)
        changes = changes + sch_changes

    result = MendResult(
        value=value,
        ok=True,
        repaired=bool(changes),
        confidence=diag.confidence_for(changes, schema_issues),
        changes=changes,
        schema_issues=schema_issues,
        candidates=len(candidates),
        chosen=chosen_idx,
    )
    return result if return_report else value


def _safe(result: MendResult) -> Any:
    if result.ok:
        return result.value
    raise ValueError(f"strict parse failed: {result.error}")


# --------------------------------------------------------------------------- #
# Convenience API
# --------------------------------------------------------------------------- #
def loads(source: str, **kwargs: Any) -> Any:
    """Tolerant alias for :func:`mend`."""
    return mend(source, **kwargs)


def loads_many(source: str, *, schema: Optional[dict] = None) -> List[Any]:
    """Parse every JSON document embedded in ``source``."""
    result = mend(source, schema=schema, many=True, return_report=True)
    return result.value if result.ok else []


def extract_json(source: str) -> List[str]:
    """Return the raw candidate JSON fragments (fences stripped)."""
    return [c.text for c in find_candidates(source)]


def mend_file(path: str, **kwargs: Any) -> Any:
    """Read ``path`` and repair its contents."""
    with open(path, "r", encoding="utf-8") as fh:
        return mend(fh.read(), **kwargs)
