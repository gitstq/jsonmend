"""Streaming example: repair JSON that arrives token-by-token (e.g. SSE)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import json

from jsonmend import StreamMender

# The full document the agent is streaming; imagine these deltas arriving
# over the network one at a time.
full = '{"summary": "ok", "scores": [10, 20, 30]}'
deltas = [full[i : i + 4] for i in range(0, len(full), 4)]

mender = StreamMender()
for n, delta in enumerate(deltas):
    value = mender.feed(delta)
    print(f"after chunk {n + 1}: {json.dumps(value, ensure_ascii=False)}")

result = mender.finish()
print("\nfinal:", json.dumps(result.value, ensure_ascii=False))
print("naturally complete:", mender.complete)
