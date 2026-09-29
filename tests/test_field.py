"""Tests for ``cronplain.field`` — parsing, expansion, and the day-field union rule."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from cronplain.field import (  # noqa: E402
    CronError,
    is_dom_dow_union,
    matches,
    parse,
    parse_field,
    MINUTE,
    HOUR,
    MONTH,
    DAY_OF_WEEK,
)


class TestFieldExpansion(unittest.TestCase):
    def test_star(self):
        self.assertEqual(len(parse_field("*", MINUTE)), 60)
        self.assertEqual(len(parse_field("*", HOUR)), 24)

    def test_single_and_list(self):
        self.assertEqual(parse_field("5", MINUTE), frozenset({5}))
        self.assertEqual(parse_field("0,30", MINUTE), frozenset({0, 30}))

    def test_range(self):
        self.assertEqual(parse_field("9-17", HOUR), frozenset(range(9, 18)))

    def test_step_over_full_range(self):
        self.assertEqual(parse_field("*/15", MINUTE), frozenset({0, 15, 30, 45}))

    def test_step_over_range(self):
        self.assertEqual(parse_field("10-20/5", MINUTE), frozenset({10, 15, 20}))

    def test_step_does_not_overflow_upper_bound(self):
        # 50, 55 — never 60.
        self.assertEqual(parse_field("50-59/5", MINUTE), frozenset({50, 55}))

    def test_month_names(self):
        self.assertEqual(parse_field("JAN", MONTH), frozenset({1}))
        self.assertEqual(parse_field("jan-mar", MONTH), frozenset({1, 2, 3}))

    def test_weekday_names_case_insensitive(self):
        self.assertEqual(parse_field("mon-fri", DAY_OF_WEEK), frozenset({1, 2, 3, 4, 5}))
        self.assertEqual(parse_field("SUN", DAY_OF_WEEK), frozenset({0}))

    def test_weekday_seven_folds_onto_zero(self):
        self.assertEqual(parse_field("7", DAY_OF_WEEK), frozenset({0}))
        self.assertEqual(parse_field("0,7", DAY_OF_WEEK), frozenset({0}))


class TestFieldErrors(unittest.TestCase):
    def test_wrong_field_count(self):
        for bad in ("* * * *", "* * * * * *", ""):
            with self.assertRaises(CronError):
                parse(bad)

    def test_out_of_range(self):
        for bad in ("60 * * * *", "* 24 * * *", "* * 0 * *", "* * * 13 *", "* * * * 8"):
            with self.assertRaises(CronError):
                parse(bad)

    def test_zero_step_rejected(self):
        with self.assertRaises(CronError):
            parse("*/0 * * * *")

    def test_backwards_range_rejected(self):
        with self.assertRaises(CronError):
            parse("0 17-9 * * *")

    def test_unknown_name_rejected(self):
        with self.assertRaises(CronError):
            parse("0 0 * FOO *")

    def test_empty_term_rejected(self):
        with self.assertRaises(CronError):
            parse("0,,5 * * * *")


class TestScheduleShape(unittest.TestCase):
    def test_whitespace_is_normalised(self):
        self.assertEqual(parse("  0\t 6   * * *  ").expression, "0 6 * * *")

    def test_to_dict_is_sorted(self):
        d = parse("*/20 2 * * *").to_dict()
        self.assertEqual(d["minute"], [0, 20, 40])
        self.assertEqual(d["hour"], [2])

    def test_dom_dow_union_detection(self):
        self.assertTrue(is_dom_dow_union(parse("0 0 1 * MON")))
        self.assertFalse(is_dom_dow_union(parse("0 0 1 * *")))
        self.assertFalse(is_dom_dow_union(parse("0 0 * * MON")))
        self.assertFalse(is_dom_dow_union(parse("0 0 * * *")))


class TestMatches(unittest.TestCase):
    """``matches`` is the only place the OR rule is implemented — worth pinning down."""

    def test_simple_clock_match(self):
        sched = parse("30 3 * * *")
        self.assertTrue(matches(sched, datetime(2026, 9, 29, 3, 30)))
        self.assertFalse(matches(sched, datetime(2026, 9, 29, 3, 31)))
        self.assertFalse(matches(sched, datetime(2026, 9, 29, 4, 30)))

    def test_seconds_are_ignored(self):
        sched = parse("0 0 * * *")
        self.assertTrue(matches(sched, datetime(2026, 9, 29, 0, 0, 59, 999999)))

    def test_weekday_mapping_uses_sunday_zero(self):
        # 2026-09-27 is a Sunday; 2026-09-28 a Monday.
        sunday = parse("0 0 * * 0")
        self.assertTrue(matches(sunday, datetime(2026, 9, 27, 0, 0)))
        self.assertFalse(matches(sunday, datetime(2026, 9, 28, 0, 0)))

    def test_dom_and_dow_are_unioned_not_intersected(self):
        sched = parse("0 0 1 * MON")
        # the 1st of the month, which is NOT a Monday -> still matches (OR semantics)
        self.assertTrue(matches(sched, datetime(2026, 10, 1, 0, 0)))
        # a Monday that is NOT the 1st -> also matches
        self.assertTrue(matches(sched, datetime(2026, 9, 28, 0, 0)))
        # neither -> no match
        self.assertFalse(matches(sched, datetime(2026, 9, 29, 0, 0)))

    def test_dom_only_behaves_like_and(self):
        sched = parse("0 0 15 * *")
        self.assertTrue(matches(sched, datetime(2026, 9, 15, 0, 0)))
        self.assertFalse(matches(sched, datetime(2026, 9, 16, 0, 0)))


if __name__ == "__main__":
    unittest.main()
