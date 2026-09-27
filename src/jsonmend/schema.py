"""A small, dependency-free JSON Schema subset.

Used in two ways:

* ``coerce(value, schema)`` validates and gently forces a parsed value into the
  schema -- type coercion, enum repair, ``default`` filling and ``required``
  checks -- returning issues and recorded changes;
* ``match_score(value, schema)`` scores how well a value fits a schema, which
  lets the mender choose the best of several JSON candidates.

Supported keywords: ``type`` (string or list), ``properties``, ``required``,
``items``, ``enum``, ``const``, ``default``, ``minimum``/``maximum``,
``minLength``/``maxLength``, ``pattern`` and ``additionalProperties``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from . import diagnostics as diag
from .diagnostics import Change, SchemaIssue

_TYPES = ("null", "boolean", "object", "array", "number", "integer", "string")


def _type_ok(value: Any, t: str) -> bool:
    if t == "null":
        return value is None
    if t == "boolean":
        return isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "string":
        return isinstance(value, str)
    if t == "array":
        return isinstance(value, list)
    if t == "object":
        return isinstance(value, dict)
    return True


def _types_of(schema: Dict[str, Any]) -> List[str]:
    t = schema.get("type")
    if t is None:
        return []
    return t if isinstance(t, list) else [t]


# --------------------------------------------------------------------------- #
# Coercion
# --------------------------------------------------------------------------- #
def _coerce_scalar(value: Any, t: str) -> Any:
    if t == "string":
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return "null"
        # Do not flatten objects/arrays into a string.
        return value
    if t in ("number", "integer"):
        if isinstance(value, bool):
            num = int(value)
        elif isinstance(value, str):
            num = float(value.strip().replace(",", "."))
        elif isinstance(value, (int, float)):
            num = value
        else:
            return value
        return int(num) if t == "integer" else num
    if t == "boolean":
        if isinstance(value, str):
            low = value.strip().lower()
            truthy = {"true", "1", "yes", "y", "on"}
            falsy = {"false", "0", "no", "n", "off"}
            if low in truthy:
                return True
            if low in falsy:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
    if t == "null":
        return None
    if t == "array":
        return [value]
    return value


def _check_enum(value: Any, schema: Dict[str, Any], path: str) -> Tuple[Any, List[SchemaIssue], List[Change]]:
    members = schema["enum"]
    issues: List[SchemaIssue] = []
    changes: List[Change] = []
    if value in members:
        return value, issues, changes
    # Try a normalized (string, trimmed, case-insensitive) match.
    if isinstance(value, str):
        norm = value.strip().lower()
        candidates = [m for m in members if isinstance(m, str) and m.strip().lower() == norm]
        if len(candidates) == 1:
            changes.append(Change(diag.SCHEMA_ENUM, before=value, after=candidates[0]))
            return candidates[0], issues, changes
    issues.append(SchemaIssue(path, diag.SCHEMA_ENUM, f"{value!r} is not one of {members!r}"))
    return value, issues, changes


def coerce(
    value: Any, schema: Dict[str, Any], path: str = "$"
) -> Tuple[Any, List[SchemaIssue], List[Change]]:
    issues: List[SchemaIssue] = []
    changes: List[Change] = []
    if not isinstance(schema, dict):
        return value, issues, changes

    if "const" in schema and value != schema["const"]:
        issues.append(SchemaIssue(path, "const_mismatch", f"expected const {schema['const']!r}"))

    if "enum" in schema:
        value, ei, ec = _check_enum(value, schema, path)
        issues.extend(ei)
        changes.extend(ec)

    types = _types_of(schema)
    if types and not any(_type_ok(value, t) for t in types):
        target = next((t for t in types if t in _TYPES), types[0])
        try:
            new_value = _coerce_scalar(value, target)
            if new_value is not value and _type_ok(new_value, target):
                changes.append(
                    Change(diag.SCHEMA_COERCED, start=-1, before=repr(value), after=repr(new_value))
                )
                value = new_value
        except (ValueError, TypeError):
            pass
        if not any(_type_ok(value, t) for t in types):
            issues.append(SchemaIssue(path, "type_mismatch", f"expected {types}, got {type(value).__name__}"))

    # Object
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                sub = props.get(name, {})
                if isinstance(sub, dict) and "default" in sub:
                    value[name] = sub["default"]
                    changes.append(Change(diag.SCHEMA_DEFAULT, before="<missing>", after=repr(sub["default"])))
                else:
                    issues.append(SchemaIssue(f"{path}.{name}", diag.SCHEMA_MISSING, f"required field '{name}' is missing"))
        for name, sub in props.items():
            if name in value:
                nv, ni, nc = coerce(value[name], sub, f"{path}.{name}")
                value[name] = nv
                issues.extend(ni)
                changes.extend(nc)
        if schema.get("additionalProperties") is False:
            for name in value.keys():
                if name not in props:
                    issues.append(SchemaIssue(f"{path}.{name}", "additional_property", f"additional property '{name}' not allowed"))

    # Array
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for idx, item in enumerate(value):
            nv, ni, nc = coerce(item, schema["items"], f"{path}[{idx}]")
            value[idx] = nv
            issues.extend(ni)
            changes.extend(nc)

    # String constraints
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            issues.append(SchemaIssue(path, "min_length", f"length {len(value)} < {schema['minLength']}"))
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            issues.append(SchemaIssue(path, "max_length", f"length {len(value)} > {schema['maxLength']}"))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            issues.append(SchemaIssue(path, "pattern", f"does not match pattern {schema['pattern']!r}"))

    # Number constraints
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(SchemaIssue(path, "minimum", f"{value} < minimum {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(SchemaIssue(path, "maximum", f"{value} > maximum {schema['maximum']}"))

    return value, issues, changes


# --------------------------------------------------------------------------- #
# Candidate scoring
# --------------------------------------------------------------------------- #
def match_score(value: Any, schema: Dict[str, Any]) -> float:
    if not isinstance(schema, dict):
        return 0.5
    if "const" in schema:
        return 1.0 if value == schema["const"] else 0.0
    if "enum" in schema:
        return 1.0 if value in schema["enum"] else 0.2

    types = _types_of(schema)
    if types:
        if not any(_type_ok(value, t) for t in types):
            return 0.0

    if isinstance(value, dict):
        props = schema.get("properties", {})
        if props:
            hit = sum(1 for p in props if p in value)
            return hit / len(props)
        return 0.8
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        if not value:
            return 0.6
        return sum(match_score(v, schema["items"]) for v in value) / len(value)
    return 1.0 if types else 0.7
