import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import json
import unittest

from jsonmend.streaming import StreamMender, feed_stream, iter_jsonl


class TestStreamMender(unittest.TestCase):
    def _feed_chars(self, text):
        m = StreamMender()
        snapshots = []
        for ch in text:
            snapshots.append(m.feed(ch))
        return m, snapshots

    def test_object_char_by_char(self):
        expected = {"a": 1, "b": [1, 2], "c": "x"}
        text = json.dumps(expected)
        m, snapshots = self._feed_chars(text)
        self.assertTrue(m.complete)
        result = m.finish()
        self.assertEqual(result.value, expected)
        self.assertEqual(result.confidence, 1.0)

    def test_fenced_stream(self):
        text = '```json\n{"a": 1, "b": 2}\n```'
        m, _ = self._feed_chars(text)
        result = m.finish()
        self.assertEqual(result.value, {"a": 1, "b": 2})

    def test_truncated_prefix_never_raises(self):
        text = '{"items": [1, 2, 3'
        m, snapshots = self._feed_chars(text)
        self.assertFalse(m.complete)
        result = m.finish()
        self.assertEqual(result.value, {"items": [1, 2, 3]})

    def test_schema_stream(self):
        schema = {"type": "object", "properties": {"n": {"type": "integer"}}}
        m = StreamMender(schema=schema)
        for ch in '{"n": "7"}':
            m.feed(ch)
        result = m.finish()
        self.assertEqual(result.value, {"n": 7})


class TestHelpers(unittest.TestCase):
    def test_feed_stream(self):
        chunks = ['{"a":', ' 1}']
        values = list(feed_stream(chunks))
        self.assertEqual(values[-1], {"a": 1})

    def test_iter_jsonl(self):
        lines = ['{"a": 1,}', "prose", '{"b": 2}']
        values = list(iter_jsonl(lines))
        self.assertEqual(values, [{"a": 1}, {"b": 2}])


if __name__ == "__main__":
    unittest.main()
