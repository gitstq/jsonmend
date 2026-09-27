import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), '..', 'src'))

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from jsonmend.cli import main


class TestCLI(unittest.TestCase):
    def run_cli(self, argv, stdin_text=None):
        out, err = io.StringIO(), io.StringIO()
        old_stdin = None
        if stdin_text is not None:
            import sys

            old_stdin = sys.stdin
            sys.stdin = io.StringIO(stdin_text)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = main(argv)
        finally:
            if old_stdin is not None:
                import sys

                sys.stdin = old_stdin
        return code, out.getvalue(), err.getvalue()

    def test_content_compact(self):
        code, out, _ = self.run_cli(["-c", '{"a": 1,}', "--compact"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"a": 1})

    def test_stdin_single_quotes(self):
        code, out, _ = self.run_cli([], stdin_text="{'a': 1}")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"a": 1})

    def test_check_valid_exit_zero(self):
        code, _, err = self.run_cli(["-c", '{"a": 1}', "--check"])
        self.assertEqual(code, 0)
        self.assertIn("valid", err)

    def test_check_dirty_exit_one(self):
        code, _, err = self.run_cli(["-c", '{"a": 1,}', "--check"])
        self.assertEqual(code, 1)
        self.assertIn("trailing_comma_removed", err)

    def test_many(self):
        code, out, _ = self.run_cli(["-c", '{"a":1} x {"b":2}', "--many", "--compact"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [{"a": 1}, {"b": 2}])

    def test_diagnostics_to_stderr(self):
        code, _, err = self.run_cli(["-c", '{"a": 1,}', "--diagnostics"])
        self.assertEqual(code, 0)
        self.assertIn("confidence", err)

    def test_indent(self):
        code, out, _ = self.run_cli(["-c", '{"a":1}', "--indent", "4"])
        self.assertIn("\n    ", out)


if __name__ == "__main__":
    unittest.main()
