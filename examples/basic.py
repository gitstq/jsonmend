"""Basic example: mend a typical LLM response that wraps dirty JSON."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json

from jsonmend import mend

llm_output = """Sure, here is the user profile you requested:

```json
{
  'name': 'Ada Lovelace',
  "active": True,
  "tags": ["math", "engines",], // created by the model
}
```

Let me know if you need edits.
"""

# return_report=True gives access to confidence and an explainable change list.
report = mend(llm_output, return_report=True)

print("value:")
print(json.dumps(report.value, indent=2, ensure_ascii=False))
print("\nconfidence:", report.confidence)
print("repairs applied:")
for change in report.changes:
    print(f"  - {change.code}")
