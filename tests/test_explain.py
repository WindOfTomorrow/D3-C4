"""Tests for ``cronplain.explain`` — the English rendering.

Phrases are asserted exactly rather than by substring where the exact string is the
contract users see.  ``test_documentation_examples`` re-checks the two examples in
the package docstring, so the docs cannot silently drift away from the output.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from cronplain.explain import describe, explain, warnings  # noqa: E402
from cronplain.field import parse  # noqa: E402


class TestDocumentationExamples(unittest.TestCase):
    def test_documentation_examples(self):
        self.assertEqual(explain("*/15 9-17 * * MON-FRI"),
                         "Every 15 minutes, between 09:00 and 17:59, on Monday to Friday")
        self.assertEqual(explain("30 3 * * *"), "At 03:30")


class TestTimePhrases(unittest.TestCase):
    def test_every_minute(self):
        self.assertEqual(explain("* * * * *"), "Every minute")

    def test_clock_time(self):
        self.assertEqual(explain("0 0 * * *"), "At 00:00")
        self.assertEqual(explain("5 23 * * *"), "At 23:05")

    def test_every_hour_at_minute(self):
        self.assertEqual(explain("0 * * * *"), "Every hour at minute 0")

    def test_step_minutes(self):
        self.assertEqual(explain("*/15 * * * *"), "Every 15 minutes")
        self.assertEqual(explain("*/30 * * * *"), "Every 30 minutes")

    def test_hour_range_with_step_minutes(self):
        self.assertEqual(explain("0 */6 * * *"), "At minute 0, every 6 hours")

    def test_hour_range(self):
        self.assertEqual(explain("30 9-17 * * *"),
                         "At minute 30, between 09:00 and 17:59")

    def test_single_hour_with_multiple_minutes(self):
        self.assertEqual(explain("0,30 12 * * *"),
                         "Every 30 minutes, during the 12:00 hour")

    def test_minute_range(self):
        self.assertEqual(explain("0-30 6 * * *"),
                         "Between minute 0 and 30, during the 06:00 hour")


class TestDayAndMonthPhrases(unittest.TestCase):
    def test_day_of_month_list(self):
        self.assertEqual(explain("0 12 1,15,28 * *"),
                         "At 12:00, on the 1st, 15th and 28th of the month")

    def test_ordinal_suffixes_are_english(self):
        self.assertIn("21st", explain("0 0 21 * *"))
        self.assertIn("22nd", explain("0 0 22 * *"))
        self.assertIn("23rd", explain("0 0 23 * *"))
        self.assertIn("11th", explain("0 0 11 * *"))
        self.assertIn("12th", explain("0 0 12 * *"))
        self.assertIn("13th", explain("0 0 13 * *"))

    def test_month_range(self):
        self.assertEqual(explain("0 0 * JAN-MAR *"), "At 00:00, in January to March")

    def test_single_weekday(self):
        self.assertEqual(explain("5 4 * * SUN"), "At 04:05, on Sunday")

    def test_weekday_range(self):
        self.assertEqual(explain("0 9 * * 1-5"), "At 09:00, on Monday to Friday")

    def test_dom_dow_union_is_spelled_out_with_or(self):
        text = explain("0 0 1 * MON")
        self.assertIn(" or ", text)
        self.assertEqual(text, "At 00:00, on the 1st of the month or on Monday")

    def test_fully_specified(self):
        self.assertEqual(explain("0 0 1 1 *"), "At 00:00, on the 1st of the month, in January")


class TestWarnings(unittest.TestCase):
    def test_union_warning_is_raised(self):
        notes = warnings(parse("0 0 1 * MON"))
        self.assertEqual(len(notes), 1)
        self.assertIn("EITHER", notes[0])

    def test_no_warning_for_plain_expressions(self):
        for expression in ("* * * * *", "0 0 * * *", "0 0 1 * *", "0 0 * * MON"):
            self.assertEqual(warnings(parse(expression)), [], expression)


class TestDescribeInterface(unittest.TestCase):
    def test_describe_matches_explain(self):
        schedule = parse("*/5 * * * *")
        self.assertEqual(describe(schedule), explain("*/5 * * * *"))

    def test_no_trailing_period(self):
        # Downstream tools paste this into log lines; a sentence-final period there
        # just looks like a typo.
        self.assertFalse(explain("30 3 * * *").endswith("."))


if __name__ == "__main__":
    unittest.main()
