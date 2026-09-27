"""Schema example: repair an LLM response and coerce it to a JSON Schema."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json

from jsonmend import mend

schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "default": 0},
        "role": {"enum": ["admin", "user"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["name", "age", "role"],
}

# The model used bare keys, sent age as text, role in the wrong case, and a
# numeric tag. jsonmend repairs and then coerces.
dirty = '```json\n{name: "Grace", age: "36", role: ADMIN, tags: ["ops", 42]}\n```'

report = mend(dirty, schema=schema, return_report=True)

print(json.dumps(report.value, indent=2, ensure_ascii=False))
print("\nrepairs:")
for change in report.changes:
    print(f"  - [{change.severity}] {change.code}")
for issue in report.schema_issues:
    print(f"  ! {issue.path}: {issue.message}")
