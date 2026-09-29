"""Field parsing for five-field cron expressions.

A cron line has five fields, in this order::

    minute  hour  day-of-month  month  day-of-week
     0-59   0-23      1-31      1-12      0-6

Each field accepts a comma-separated list of terms; a term is one of ``*``, a
single value, a range ``lo-hi``, or any of those followed by ``/step``.  Month
and day-of-week also accept the three-letter names (``JAN``, ``MON``, ...).

Two quirks are worth knowing, because they trip people up constantly and both are
reproduced faithfully here:

* Day-of-week is 0-6 with **0 = Sunday**.  The value ``7`` is accepted and folded
  onto ``0``; ``cron`` has always done this, even though the manual page lists the
  range as 0-6.
* Day-of-month and day-of-week are **not** intersected.  When both are restricted,
  the job runs when *either* matches.  That is the historical behaviour of Vixie
  cron, and it surprises almost everyone the first time.  :func:`is_dom_dow_union`
  reports whether an expression is in that state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MONTH_NAMES = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

DOW_NAMES = {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3, "THU": 4, "FRI": 5, "SAT": 6,
}

_NAME_RE = re.compile(r"^[A-Za-z]{3}$")


class CronError(ValueError):
    """Raised when an expression cannot be read as a five-field cron line."""


@dataclass(frozen=True)
class FieldSpec:
    """Static description of one cron field."""

    name: str
    lo: int
    hi: int
    names: dict[str, int] = field(default_factory=dict)
    #: accept ``lo``+1 as a synonym for ``lo`` (only day-of-week does this)
    wrap_high: bool = False

    def resolve(self, token: str) -> int:
        """Turn ``"3"`` / ``"JAN"`` / ``"SUN"`` into a number, or raise."""
        upper = token.upper()
        if _NAME_RE.match(upper) and upper in self.names:
            return self.names[upper]
        if not token.isdigit():
            raise CronError(f"{self.name}: {token!r} is not a number or a known name")
        value = int(token)
        if self.wrap_high and value == self.hi + 1:
            return self.lo
        if not (self.lo <= value <= self.hi):
            raise CronError(f"{self.name}: {value} is outside {self.lo}-{self.hi}")
        return value


MINUTE = FieldSpec("minute", 0, 59)
HOUR = FieldSpec("hour", 0, 23)
DAY_OF_MONTH = FieldSpec("day-of-month", 1, 31)
MONTH = FieldSpec("month", 1, 12, names=MONTH_NAMES)
DAY_OF_WEEK = FieldSpec("day-of-week", 0, 6, names=DOW_NAMES, wrap_high=True)

FIELDS = (MINUTE, HOUR, DAY_OF_MONTH, MONTH, DAY_OF_WEEK)


def parse_term(term: str, spec: FieldSpec) -> set[int]:
    """Expand a single comma-free term into the set of values it selects.

    ``"*/5"`` -> ``{0, 5, 10, ..., 55}``, ``"9-17"`` -> nine values, and so on.
    """
    if not term:
        raise CronError(f"{spec.name}: empty term")

    base, slash, step_text = term.partition("/")
    if slash:
        if not step_text.isdigit() or int(step_text) == 0:
            raise CronError(f"{spec.name}: step must be a positive integer, got {step_text!r}")
        step = int(step_text)
    else:
        step = 1

    if base == "*":
        lo, hi = spec.lo, spec.hi
    elif "-" in base:
        lo_text, _, hi_text = base.partition("-")
        lo, hi = spec.resolve(lo_text), spec.resolve(hi_text)
        if lo > hi:
            raise CronError(f"{spec.name}: range {base!r} runs backwards")
    else:
        lo = hi = spec.resolve(base)

    return set(range(lo, hi + 1, step))


def parse_field(text: str, spec: FieldSpec) -> frozenset[int]:
    """Expand one whole field (possibly a comma-separated list)."""
    terms = text.split(",")
    values: set[int] = set()
    for term in terms:
        values |= parse_term(term.strip(), spec)
    if not values:
        raise CronError(f"{spec.name}: selects nothing")
    return frozenset(values)


@dataclass(frozen=True)
class Schedule:
    """A parsed five-field expression.

    Every field is stored as a frozen set of integers so a :class:`Schedule` is
    hashable and safe to use as a cache key.
    """

    expression: str
    minute: frozenset[int]
    hour: frozenset[int]
    day_of_month: frozenset[int]
    month: frozenset[int]
    day_of_week: frozenset[int]

    @property
    def dom_restricted(self) -> bool:
        """True when day-of-month is narrower than ``*``."""
        return len(self.day_of_month) != 31

    @property
    def dow_restricted(self) -> bool:
        """True when day-of-week is narrower than ``*``."""
        return len(self.day_of_week) != 7

    @property
    def dom_dow_union(self) -> bool:
        """True when the schedule is in the day-of-month **OR** day-of-week state.

        See :func:`is_dom_dow_union`; this is the reason the two fields cannot be
        treated as independent filters.
        """
        return self.dom_restricted and self.dow_restricted

    def to_dict(self) -> dict[str, list[int]]:
        """Plain-data view, handy for ``--json`` output and for tests."""
        return {
            "minute": sorted(self.minute),
            "hour": sorted(self.hour),
            "day_of_month": sorted(self.day_of_month),
            "month": sorted(self.month),
            "day_of_week": sorted(self.day_of_week),
        }


def parse(expression: str) -> Schedule:
    """Parse a five-field cron expression.

    Raises :class:`CronError` with a message naming the offending field.
    """
    if expression is None:
        raise CronError("empty expression")
    text = " ".join(expression.split())
    if not text:
        raise CronError("empty expression")

    parts = text.split(" ")
    if len(parts) != 5:
        raise CronError(
            f"expected 5 fields (minute hour day-of-month month day-of-week), got {len(parts)}"
        )

    values = [parse_field(part, spec) for part, spec in zip(parts, FIELDS)]
    return Schedule(expression=text, minute=values[0], hour=values[1],
                    day_of_month=values[2], month=values[3], day_of_week=values[4])


def is_dom_dow_union(schedule: Schedule) -> bool:
    """Report whether day-of-month and day-of-week will be OR-ed together.

    Vixie cron runs a job when **either** restricted day field matches.  So
    ``0 0 1 * MON`` means *the first of the month* **or** *every Monday* — twelve
    runs a year plus fifty-two, not four.  Many crontab authors write exactly that
    line expecting the intersection.

    >>> is_dom_dow_union(parse("0 0 1 * MON"))
    True
    >>> is_dom_dow_union(parse("0 0 1 * *"))
    False
    """
    return schedule.dom_dow_union


def matches(schedule: Schedule, when) -> bool:
    """Return whether a :class:`datetime.datetime` falls on this schedule.

    The day-of-month / day-of-week union rule described above is applied here.
    Seconds and microseconds are ignored.
    """
    if when.minute not in schedule.minute or when.hour not in schedule.hour:
        return False
    if when.month not in schedule.month:
        return False
    # Python's weekday(): Monday == 0.  Cron's: Sunday == 0.
    cron_dow = (when.weekday() + 1) % 7
    hit_dom = when.day in schedule.day_of_month
    hit_dow = cron_dow in schedule.day_of_week
    if schedule.dom_dow_union:
        return hit_dom or hit_dow
    return hit_dom and hit_dow
