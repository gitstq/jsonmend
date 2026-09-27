import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import json
import unittest

from jsonmend.cleaner import clean


def loads_fixed(text):
    fixed, changes = clean(text)
    return json.loads(fixed), changes


class TestQuotes(unittest.TestCase):
    def test_single_quotes(self):
        v, _ = loads_fixed("{'a': 'x', 'b': 1}")
        self.assertEqual(v, {"a": "x", "b": 1})

    def test_double_quote_inside_single(self):
        v, _ = loads_fixed('''{'q': 'he said "hi"'}''')
        self.assertEqual(v, {"q": 'he said "hi"'})

    def test_smart_quotes(self):
        v, _ = loads_fixed("{“a”: “b”}")
        self.assertEqual(v, {"a": "b"})


class TestComments(unittest.TestCase):
    def test_line_comment(self):
        v, _ = loads_fixed('{"a": 1 // tail\n}')
        self.assertEqual(v, {"a": 1})

    def test_block_comment(self):
        v, _ = loads_fixed('{"a": /* c */ 1}')
        self.assertEqual(v, {"a": 1})

    def test_comment_like_in_string_preserved(self):
        v, _ = loads_fixed('{"u": "http://x"}')
        self.assertEqual(v, {"u": "http://x"})


class TestTrailingCommas(unittest.TestCase):
    def test_object(self):
        v, _ = loads_fixed('{"a": 1,}')
        self.assertEqual(v, {"a": 1})

    def test_array(self):
        v, _ = loads_fixed("[1, 2,]")
        self.assertEqual(v, [1, 2])

    def test_nested(self):
        v, _ = loads_fixed('{"a": [1, 2,], "b": 3,}')
        self.assertEqual(v, {"a": [1, 2], "b": 3})


class TestBareAndLiterals(unittest.TestCase):
    def test_bare_keys(self):
        v, _ = loads_fixed('{name: "x", age: 1}')
        self.assertEqual(v, {"name": "x", "age": 1})

    def test_python_literals(self):
        v, changes = loads_fixed('{"ok": True, "no": False, "x": None}')
        self.assertEqual(v, {"ok": True, "no": False, "x": None})
        self.assertTrue(changes)

    def test_undefined(self):
        v, _ = loads_fixed('{"x": undefined}')
        self.assertEqual(v, {"x": None})


class TestNumbers(unittest.TestCase):
    def test_hex_oct(self):
        v, _ = loads_fixed('{"h": 0x10, "o": 0o10}')
        self.assertEqual(v, {"h": 16, "o": 8})

    def test_leading_plus(self):
        v, changes = loads_fixed('{"x": +5}')
        self.assertEqual(v, {"x": 5})
        self.assertTrue(changes)

    def test_nan_infinity_become_null(self):
        v, _ = loads_fixed('{"a": NaN, "b": Infinity}')
        self.assertEqual(v, {"a": None, "b": None})


class TestMissingPunctuation(unittest.TestCase):
    def test_missing_comma_object(self):
        v, _ = loads_fixed('{"a": 1 "b": 2}')
        self.assertEqual(v, {"a": 1, "b": 2})

    def test_missing_comma_array(self):
        v, _ = loads_fixed("[1 2 3]")
        self.assertEqual(v, [1, 2, 3])

    def test_missing_colon(self):
        v, _ = loads_fixed('{"a" 1}')
        self.assertEqual(v, {"a": 1})


class TestControlAndIdempotence(unittest.TestCase):
    def test_raw_newline_in_string(self):
        v, changes = loads_fixed('{"a": "line1\nline2"}')
        self.assertEqual(v, {"a": "line1\nline2"})
        self.assertTrue(any(c.code == "control_char_escaped" for c in changes))

    def test_valid_json_roundtrip(self):
        original = {"a": [1, 2, 3], "b": {"c": "d"}, "e": None}
        fixed, changes = clean(json.dumps(original))
        self.assertEqual(json.loads(fixed), original)
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
