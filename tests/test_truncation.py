import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import unittest

from jsonmend.truncation import analyze, complete_simple, is_complete


class TestAnalyze(unittest.TestCase):
    def test_complete(self):
        self.assertTrue(is_complete('{"a": [1, 2]}'))
        self.assertTrue(is_complete("[1, 2, 3]"))
        self.assertTrue(is_complete('"scalar"'))

    def test_incomplete(self):
        self.assertFalse(is_complete('{"a": 1'))
        self.assertFalse(is_complete("[1, 2"))
        self.assertFalse(is_complete('{"a": "x'))

    def test_analyze_reports_openers(self):
        stack, in_str = analyze('{"a": [1,')
        self.assertEqual(stack, ["{", "["])
        self.assertIsNone(in_str)

    def test_open_string(self):
        _, in_str = analyze('{"a": "xy')
        self.assertEqual(in_str, '"')


class TestCompleteSimple(unittest.TestCase):
    def test_close_string(self):
        fixed, changes = complete_simple('{"a": "xy')
        self.assertTrue(is_complete(fixed))
        self.assertIn('"xy"', fixed)
        self.assertTrue(any(c.code == "unterminated_string_closed" for c in changes))

    def test_trailing_comma(self):
        fixed, _ = complete_simple("[1, 2,")
        self.assertEqual(fixed, "[1, 2]")

    def test_key_without_value(self):
        fixed, changes = complete_simple('{"a": 1, "b":')
        self.assertTrue(is_complete(fixed))
        self.assertEqual(fixed, '{"a": 1}')
        self.assertTrue(any(c.code == "incomplete_tail_dropped" for c in changes))

    def test_nested(self):
        fixed, _ = complete_simple('{"a": {"b": [1,')
        self.assertTrue(is_complete(fixed))

    def test_already_complete_unchanged(self):
        fixed, changes = complete_simple('{"a": 1}')
        self.assertEqual(fixed, '{"a": 1}')
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
