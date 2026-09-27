import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import unittest

from jsonmend.schema import coerce, match_score


class TestTypeCoercion(unittest.TestCase):
    def test_string_to_number(self):
        v, issues, changes = coerce("12", {"type": "integer"})
        self.assertEqual(v, 12)
        self.assertTrue(any(c.code == "schema_value_coerced" for c in changes))

    def test_number_to_string(self):
        v, _, _ = coerce(5, {"type": "string"})
        self.assertEqual(v, "5")

    def test_string_to_boolean(self):
        v, _, _ = coerce("yes", {"type": "boolean"})
        self.assertIs(v, True)
        v, _, _ = coerce("no", {"type": "boolean"})
        self.assertIs(v, False)

    def test_scalar_to_array(self):
        v, _, _ = coerce(3, {"type": "array", "items": {"type": "integer"}})
        self.assertEqual(v, [3])

    def test_type_mismatch_issue(self):
        v, issues, _ = coerce({"a": 1}, {"type": "string"})
        self.assertTrue(any(i.code == "type_mismatch" for i in issues))


class TestDefaultsAndRequired(unittest.TestCase):
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer", "default": 0},
            "b": {"type": "string"},
        },
        "required": ["a", "b"],
    }

    def test_default_filled(self):
        v, issues, changes = coerce({}, self.schema)
        self.assertEqual(v["a"], 0)
        self.assertTrue(any(c.code == "schema_default_added" for c in changes))
        self.assertTrue(any(i.code == "schema_required_missing" for i in issues))


class TestEnum(unittest.TestCase):
    schema = {"enum": ["Red", "Green", "Blue"]}

    def test_exact(self):
        v, issues, _ = coerce("Red", self.schema)
        self.assertEqual(v, "Red")
        self.assertEqual(issues, [])

    def test_case_insensitive_repair(self):
        v, issues, changes = coerce("green", self.schema)
        self.assertEqual(v, "Green")
        self.assertTrue(any(c.code == "schema_enum_fixed" for c in changes))

    def test_no_match_issue(self):
        v, issues, _ = coerce("Purple", self.schema)
        self.assertTrue(any(i.code == "schema_enum_fixed" for i in issues))


class TestNested(unittest.TestCase):
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"type": "integer"},
            }
        },
    }

    def test_array_items_coerced(self):
        v, issues, _ = coerce({"items": ["1", "2", "3"]}, self.schema)
        self.assertEqual(v, {"items": [1, 2, 3]})
        self.assertEqual(issues, [])


class TestMatchScore(unittest.TestCase):
    def test_perfect(self):
        self.assertEqual(match_score({"a": 1}, {"type": "object", "properties": {"a": {}}}), 1.0)

    def test_partial(self):
        score = match_score({"a": 1}, {"type": "object", "properties": {"a": {}, "b": {}}})
        self.assertEqual(score, 0.5)

    def test_wrong_type(self):
        self.assertEqual(match_score("x", {"type": "integer"}), 0.0)


if __name__ == "__main__":
    unittest.main()
