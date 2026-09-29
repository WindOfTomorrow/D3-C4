"""Turn a parsed :class:`~cronplain.field.Schedule` into an English sentence.

The wording aims to be readable rather than machine-parseable, so the output is
built from a small set of templates rather than from a full grammar.  Three rules
keep it predictable:

1. Time phrases are always 24-hour with two-digit hours (``09:05``, ``23:00``).
   The audience is people reading server crontabs, where 12-hour clocks cause more
   confusion than they remove.
2. Fields that are unrestricted contribute nothing to the sentence.  ``0 6 * * *``
   is "At 06:00", not "At 06:00, every day of every month".
3. An arithmetic ladder is described by its shape, not by listing its members.
   ``9-17`` is "between 09:00 and 17:59"; ``*/15`` is "every 15 minutes".  Anything
   that is not a ladder falls back to an explicit list, so the sentence is never
   *wrong* — occasionally blunt, but never wrong.
"""

from __future__ import annotations

from cronplain.field import Schedule, parse

DOW_NAMES = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
MONTH_NAMES = ("", "January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December")


def _ordinal(n: int) -> str:
    """``1 -> 1st``, ``11 -> 11th``, ``22 -> 22nd``."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _ladder(values) -> tuple[int, int, int] | None:
    """Return ``(first, last, gap)`` when ``values`` forms an even ladder.

    ``{9..17}`` -> ``(9, 17, 1)``; ``{0, 15, 30, 45}`` -> ``(0, 45, 15)``;
    ``{1, 15, 28}`` -> ``None``.

    The check is *against the values themselves*, not against the field's full
    range — an earlier version compared with ``range(lo, hi + 1, gap)``, which
    silently failed to recognise ``9-17`` (a perfectly ordinary hour range) and
    printed all nine hours instead.
    """
    ordered = sorted(values)
    if len(ordered) < 2:
        return None
    gap = ordered[1] - ordered[0]
    if gap < 1:
        return None
    if ordered != list(range(ordered[0], ordered[-1] + 1, gap)):
        return None
    return ordered[0], ordered[-1], gap


def _join(items) -> str:
    """``['a'] -> 'a'``, ``['a','b'] -> 'a and b'``, ``['a','b','c'] -> 'a, b and c'``.

    Accepts any iterable: several call sites hand over generator expressions, and an
    earlier version crashed on them because it asked for ``len()`` immediately.
    """
    items = list(items)
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


# ---------------------------------------------------------------------------
# per-field phrases
# ---------------------------------------------------------------------------

def _minute_phrase(schedule: Schedule) -> str:
    """Describe the minute field, lowercase so the caller can capitalise it."""
    minutes = sorted(schedule.minute)
    if len(minutes) == 60:
        return "every minute"
    if len(minutes) == 1:
        return f"at minute {minutes[0]}"
    shape = _ladder(schedule.minute)
    if shape:
        first, last, gap = shape
        if gap == 1:
            return f"between minute {first} and {last}"
        return f"every {gap} minutes"
    return "at minutes " + _join(str(m) for m in minutes)


def _hour_phrase(schedule: Schedule) -> tuple[str, bool]:
    """Describe the hour field. Returns ``(phrase, absorbed)``.

    ``absorbed`` is True when the minute field has already been expressed by the
    phrase (``30 3`` -> "at 03:30"), so the caller must not describe it again.
    """
    hours = sorted(schedule.hour)
    minutes = sorted(schedule.minute)

    if len(hours) == 24:
        # Unrestricted hour: contribute nothing. Without this guard the ladder
        # branch below would happily announce "between 00:00 and 23:59" for "*".
        return "", False

    if len(hours) == 1:
        hour = hours[0]
        if len(minutes) == 1:
            return f"at {hour:02d}:{minutes[0]:02d}", True
        return f"during the {hour:02d}:00 hour", False

    shape = _ladder(schedule.hour)
    if shape:
        first, last, gap = shape
        if gap == 1:
            return f"between {first:02d}:00 and {last:02d}:59", False
        return f"every {gap} hours", False

    return "at hours " + _join(f"{h:02d}:00" for h in hours), False


def _dow_phrase(schedule: Schedule) -> str:
    if len(schedule.day_of_week) == 7:
        return ""
    days = sorted(schedule.day_of_week)
    if len(days) == 1:
        return f"on {DOW_NAMES[days[0]]}"
    shape = _ladder(schedule.day_of_week)
    if shape and shape[2] == 1 and shape[0] > 0:
        # A contiguous run that does not wrap past Sunday reads better as a range:
        # "Monday to Friday" rather than "Sunday and Monday and ...".
        return f"on {DOW_NAMES[shape[0]]} to {DOW_NAMES[shape[1]]}"
    return "on " + _join(DOW_NAMES[d] for d in days)


def _dom_phrase(schedule: Schedule) -> str:
    if len(schedule.day_of_month) == 31:
        return ""
    days = sorted(schedule.day_of_month)
    if len(days) == 1:
        return f"on the {_ordinal(days[0])} of the month"
    shape = _ladder(schedule.day_of_month)
    if shape and shape[2] == 1:
        return f"on the {_ordinal(shape[0])} to {_ordinal(shape[1])} of the month"
    return "on the " + _join(_ordinal(d) for d in days) + " of the month"


def _month_phrase(schedule: Schedule) -> str:
    if len(schedule.month) == 12:
        return ""
    months = sorted(schedule.month)
    if len(months) == 1:
        return f"in {MONTH_NAMES[months[0]]}"
    shape = _ladder(schedule.month)
    if shape and shape[2] == 1:
        return f"in {MONTH_NAMES[shape[0]]} to {MONTH_NAMES[shape[1]]}"
    return "in " + _join(MONTH_NAMES[m] for m in months)


# ---------------------------------------------------------------------------
# public surface
# ---------------------------------------------------------------------------

def warnings(schedule: Schedule) -> list[str]:
    """Return human-readable notes about traps this expression walks into.

    Currently one check: the day-of-month / day-of-week **union**.  See
    :func:`cronplain.field.is_dom_dow_union` for why it matters.
    """
    notes: list[str] = []
    if schedule.dom_dow_union:
        notes.append(
            "day-of-month and day-of-week are both restricted: cron runs the job "
            "when EITHER matches, not when both do"
        )
    return notes


def describe(schedule: Schedule) -> str:
    """Render an already-parsed schedule as English (no trailing period)."""
    clauses: list[str] = []
    hour_all = len(schedule.hour) == 24
    minute_all = len(schedule.minute) == 60

    if minute_all and hour_all:
        clauses.append("Every minute")
    elif hour_all and len(schedule.minute) == 1:
        # "Every hour at minute 5" reads far better than "At minute 5".
        clauses.append(f"Every hour at minute {sorted(schedule.minute)[0]}")
    else:
        hour_clause, absorbed = _hour_phrase(schedule)
        minute_clause = _minute_phrase(schedule)
        if absorbed:
            clauses.append(hour_clause.capitalize())
        elif hour_clause:
            clauses.append(minute_clause.capitalize() + ", " + hour_clause)
        else:
            clauses.append(minute_clause.capitalize())

    dom_clause = _dom_phrase(schedule)
    dow_clause = _dow_phrase(schedule)
    visible = [dom_clause, _month_phrase(schedule), dow_clause]

    if schedule.dom_dow_union:
        # Two restricted day fields are OR-ed.  Writing them as two comma-separated
        # clauses would read as an intersection — which is simply wrong — so they
        # are merged into one clause with an explicit "or".
        day_words = [f"on {dom_clause.removeprefix('on ')}",
                     f"on {dow_clause.removeprefix('on ')}"]
        clauses.extend(c for c in (_month_phrase(schedule),) if c)
        clauses.append(" or ".join(day_words))
    else:
        clauses.extend(c for c in visible if c)

    return ", ".join(clauses)


def explain(expression: str) -> str:
    """Describe a five-field cron expression in one English sentence.

    >>> explain("*/15 9-17 * * MON-FRI")
    'Every 15 minutes, between 09:00 and 17:59, on Monday to Friday'
    >>> explain("30 3 * * *")
    'At 03:30'
    """
    return describe(parse(expression))
