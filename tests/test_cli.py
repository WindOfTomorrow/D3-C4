"""Tests for ``cronplain.cli`` — exit codes, ``--check``, ``--json`` and ``--strict``.

Exit codes are the contract that makes this tool usable from a pre-commit hook, so
they get more attention here than the printed text.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from cronplain.cli import main  # noqa: E402


def run(argv, stdin: str = ""):
    """Invoke ``main`` with stdin/stdout/stderr captured. Returns (code, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    old_stdin = sys.stdin
    if stdin:
        sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = old_stdin
    return code, out.getvalue(), err.getvalue()


class TestExitCodes(unittest.TestCase):
    def test_valid_expression_exits_zero(self):
        code, out, err = run(["*/15 9-17 * * MON-FRI"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(),
                         "Every 15 minutes, between 09:00 and 17:59, on Monday to Friday")
        self.assertEqual(err, "")

    def test_invalid_expression_exits_one_and_reports_on_stderr(self):
        code, out, err = run(["nonsense"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("error:", err)

    def test_check_prints_nothing_on_success(self):
        code, out, err = run(["--check", "0 6 * * *"])
        self.assertEqual((code, out, err), (0, "", ""))

    def test_check_reports_invalid(self):
        code, out, err = run(["--check", "* * * *"])
        self.assertEqual(code, 1)
        self.assertIn("expected 5 fields", err)


class TestWarningsAndStrict(unittest.TestCase):
    def test_union_warning_goes_to_stdout_without_failing(self):
        code, out, _ = run(["0 0 1 * MON"])
        self.assertEqual(code, 0)
        self.assertIn("warning:", out)
        self.assertIn(" or ", out)

    def test_strict_promotes_warning_to_error(self):
        code, out, err = run(["--strict", "0 0 1 * MON"])
        self.assertEqual(code, 1)
        self.assertIn("EITHER", err)

    def test_strict_leaves_clean_expressions_alone(self):
        code, _, err = run(["--strict", "0 6 * * *"])
        self.assertEqual((code, err), (0, ""))


class TestJsonOutput(unittest.TestCase):
    def test_json_round_trip(self):
        code, out, _ = run(["--json", "*/20 2 1,15 * *"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["fields"]["minute"], [0, 20, 40])
        self.assertEqual(payload["fields"]["hour"], [2])
        self.assertEqual(payload["fields"]["day_of_month"], [1, 15])
        self.assertEqual(payload["expression"], "*/20 2 1,15 * *")
        self.assertIn("explanation", payload)


class TestStdinMode(unittest.TestCase):
    def test_reads_lines_from_stdin_and_skips_comments_and_blanks(self):
        code, out, _ = run(["-"], stdin="# a comment\n0 6 * * *\n\n30 3 * * *\n")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().splitlines(), ["At 06:00", "At 03:30"])

    def test_partial_failure_returns_the_worst_code(self):
        code, out, err = run(["-"], stdin="0 6 * * *\nbroken line here\n")
        self.assertEqual(code, 1)
        self.assertIn("At 06:00", out)
        self.assertIn("error:", err)

    def test_empty_stdin_is_an_error(self):
        code, _, err = run(["-"], stdin="\n\n")
        self.assertEqual(code, 1)
        self.assertIn("stdin was empty", err)


if __name__ == "__main__":
    unittest.main()
