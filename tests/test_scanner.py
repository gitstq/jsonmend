import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import unittest

from jsonmend.scanner import find_candidates, fence_spans, structural_spans


class TestFences(unittest.TestCase):
    def test_basic_fenced(self):
        text = 'before\n```json\n{"a": 1}\n```\nafter'
        cands = find_candidates(text)
        self.assertEqual(len(cands), 1)
        self.assertTrue(cands[0].fenced)
        self.assertIn('"a": 1', cands[0].text)

    def test_fence_language_variants(self):
        for lang in ("json", "JSON", "JavaScript", ""):
            text = f"```{lang}\n[1, 2]\n```"
            cands = find_candidates(text)
            self.assertEqual(len(cands), 1, lang)
            self.assertTrue(cands[0].fenced, lang)

    def test_unterminated_fence(self):
        text = '```json\n{"a": 1'
        cands = find_candidates(text)
        self.assertEqual(len(cands), 1)
        self.assertTrue(cands[0].fenced)
        self.assertFalse(cands[0].complete)

    def test_multiple_fences(self):
        text = '```json\n{"a":1}\n```\nprose\n```json\n{"b":2}\n```'
        self.assertEqual(len(fence_spans(text)), 2)


class TestStructural(unittest.TestCase):
    def test_plain_object(self):
        cands = find_candidates('{"a": 1}')
        self.assertEqual(len(cands), 1)
        self.assertFalse(cands[0].fenced)
        self.assertTrue(cands[0].complete)

    def test_braces_inside_string_ignored(self):
        text = '{"a": "x } ] y", "b": 2}'
        complete, partial = structural_spans(text)
        self.assertEqual(len(complete), 1)
        self.assertIsNone(partial)

    def test_fence_markers_inside_string(self):
        text = '{"a": "use ``` here", "b": 1}'
        cands = find_candidates(text)
        self.assertEqual(len(cands), 1)
        self.assertFalse(cands[0].fenced)

    def test_multiple_objects(self):
        text = '{"a": 1} and {"b": 2}'
        complete, _ = structural_spans(text)
        self.assertEqual(len(complete), 2)

    def test_partial_span(self):
        text = 'prefix {"a": [1, 2'
        cands = find_candidates(text)
        self.assertEqual(len(cands), 1)
        self.assertFalse(cands[0].complete)

    def test_bare_scalar(self):
        cands = find_candidates("123")
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0].text, "123")

    def test_empty(self):
        self.assertEqual(find_candidates("   "), [])


if __name__ == "__main__":
    unittest.main()
