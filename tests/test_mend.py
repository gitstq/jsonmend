import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import json
import os
import unittest

from jsonmend import extract_json, loads_many, mend
from jsonmend.mend import mend_file

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestFixturesRecover(unittest.TestCase):
    def test_all_fixtures_recover(self):
        files = sorted(f for f in os.listdir(FIXTURES) if f.endswith(".txt"))
        self.assertTrue(files)
        for name in files:
            with self.subTest(fixture=name):
                result = mend_file(os.path.join(FIXTURES, name), return_report=True)
                self.assertTrue(result.ok, name)
                # Output must be strict, standard JSON (no NaN/Infinity).
                dumped = json.dumps(result.value)
                def reject(_):
                    raise ValueError()
                json.loads(dumped, parse_constant=reject)

    def test_fenced_fixture_value(self):
        result = mend_file(os.path.join(FIXTURES, "01_fenced.json.txt"), return_report=True)
        self.assertEqual(result.value["name"], "demo")
        self.assertEqual(result.value["owner"]["id"], 7)
        self.assertIn("web", result.value["tags"])


class TestConfidence(unittest.TestCase):
    def test_valid_is_full_confidence(self):
        r = mend('{"a": 1}', return_report=True)
        self.assertEqual(r.confidence, 1.0)
        self.assertFalse(r.repaired)

    def test_repaired_below_one(self):
        r = mend('{"a": 1,}', return_report=True)
        self.assertLess(r.confidence, 1.0)
        self.assertTrue(r.repaired)


class TestManyAndExtract(unittest.TestCase):
    def test_many(self):
        values = loads_many('{"a": 1} prose {"b": 2}')
        self.assertEqual(values, [{"a": 1}, {"b": 2}])

    def test_extract(self):
        frags = extract_json('```json\n{"a": 1}\n```')
        self.assertEqual(len(frags), 1)
        self.assertIn('"a": 1', frags[0])


class TestErrors(unittest.TestCase):
    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            mend("   ")

    def test_empty_report_not_ok(self):
        r = mend("", return_report=True)
        self.assertFalse(r.ok)


class TestSchemaIntegration(unittest.TestCase):
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "default": 0},
            "role": {"enum": ["admin", "user"]},
        },
        "required": ["name", "age", "role"],
    }

    def test_dirty_agent_output_coerced(self):
        dirty = '```json\n{name: "Ada", role: ADMIN, }\n```'
        r = mend(dirty, schema=self.schema, return_report=True)
        self.assertEqual(r.value["name"], "Ada")
        self.assertEqual(r.value["age"], 0)
        self.assertEqual(r.value["role"], "admin")


if __name__ == "__main__":
    unittest.main()
