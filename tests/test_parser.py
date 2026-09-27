import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import unittest

from jsonmend.parser import parse


class TestTolerantParser(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(parse('{"a": [1, true, null]}'), {"a": [1, True, None]})

    def test_single_quotes(self):
        self.assertEqual(parse("{'a': 'x'}"), {"a": "x"})

    def test_trailing_comma(self):
        self.assertEqual(parse('{"a": 1,}'), {"a": 1})
        self.assertEqual(parse("[1, 2,]"), [1, 2])

    def test_python_literals(self):
        self.assertEqual(parse('{"t": True, "f": False, "n": None}'),
                         {"t": True, "f": False, "n": None})

    def test_hex_number(self):
        self.assertEqual(parse('{"x": 0x10}'), {"x": 16})

    def test_bare_word_is_string(self):
        self.assertEqual(parse('{"x": hello}'), {"x": "hello"})

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse("   ")


if __name__ == "__main__":
    unittest.main()
