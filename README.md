# cronplain

Turn a five-field cron expression into a sentence you can read out loud.

```
$ cronplain "*/15 9-17 * * MON-FRI"
Every 15 minutes, between 09:00 and 17:59, on Monday to Friday
```

Most of us can decode `0 6 * * *` at a glance. Far fewer can decode `*/20 2 1,15 * *`
without counting on their fingers, and almost nobody spots the day-of-month trap
below until a job fires fifty times in a month instead of twelve.

`cronplain` exists to make that reading step mechanical. It is a single-purpose
tool: it parses, it explains, it validates. It does not schedule anything, and it
never runs your jobs.

## Install and run

No dependencies, standard library only. From a checkout, without installing:

```
PYTHONPATH=src python3 -m cronplain "0 22 * * 5"
At 22:00, on Friday
```

There is also a console entry point for the usual route:

```
python3 -m pip install -e .
cronplain "*/5 * * * *"
Every 5 minutes
```

## What it does

**Explain.** Print the schedule in plain English.

```
$ cronplain "30 3 1 * *"
At 03:30, on the 1st of the month

$ cronplain "*/20 2 1,15 * *"
Every 20 minutes, during the 02:00 hour, on the 1st and 15th of the month

$ cronplain "0 0 29 2 *"
At 00:00, on the 29th of the month, in February
```

**Validate.** `--check` prints nothing and exits non-zero when the expression is
not a valid five-field line, which makes it usable from a pre-commit hook or a CI
step:

```
$ cronplain --check "* * * *"; echo "exit=$?"
error: expected 5 fields (minute hour day-of-month month day-of-week), got 4
exit=1
```

**Machine-readable output.** `--json` emits the expanded field values alongside
the sentence:

```
$ cronplain --json "*/20 2 1,15 * *"
{
  "expression": "*/20 2 1,15 * *",
  "explanation": "Every 20 minutes, during the 02:00 hour, on the 1st and 15th of the month",
  "fields": {
    "minute": [0, 20, 40],
    "hour": [2],
    "day_of_month": [1, 15],
    "day_of_week": [0, 1, 2, 3, 4, 5, 6],
    "month": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
  },
  "warnings": []
}
```

**Read a crontab from stdin.** One expression per line; blank lines and lines
starting with `#` are skipped, so you can pipe a real crontab in:

```
$ awk '/^[^#]/ && NF >= 5 {print $1, $2, $3, $4, $5}' /etc/crontab | cronplain -
```

## The day-of-month trap

This is the reason the tool prints warnings at all.

Day-of-month and day-of-week are **not** intersected. When both are restricted,
Vixie cron runs the job when **either** field matches:

```
$ cronplain "0 0 1 * MON"
At 00:00, on the 1st of the month or on Monday
warning: day-of-month and day-of-week are both restricted: cron runs the job when EITHER matches, not when both do
```

Read that carefully: twelve runs a year (the 1st of each month) *plus* roughly
fifty-two more (every Monday), not the four "first Monday of the month" runs the
author almost certainly meant. Use `--strict` to make this warning fail the build.

## Field syntax

```
minute  hour  day-of-month  month  day-of-week
 0-59   0-23      1-31      1-12      0-6
```

| Term | Meaning |
|---|---|
| `*` | every value in the field |
| `5` | exactly 5 |
| `9-17` | the range 9 through 17, inclusive |
| `*/15` | every 15th value from the field's minimum |
| `10-20/5` | 10, 15, 20 |
| `1,15,28` | any of 1, 15 or 28 |
| `JAN`..`DEC` | month names, case-insensitive |
| `SUN`..`SAT` | weekday names, case-insensitive |

Two details worth stating explicitly, because they differ between cron
implementations:

- Day-of-week is `0`-`6` with **`0` = Sunday**. The value `7` is accepted and
  folded onto `0`.
- Step values never overflow the upper bound: `50-59/5` is `50` and `55`, not `60`.

## Tests

```
python3 -m unittest discover -s tests -t .
PYTHONPATH=src python3 -m doctest src/cronplain/explain.py
```

`make check` runs both plus a syntax check of every file.

## Layout

```
src/cronplain/field.py     parsing, expansion, and the OR rule
src/cronplain/explain.py   the English rendering
src/cronplain/cli.py       argument parsing and exit codes
src/cronplain/__main__.py  python3 -m cronplain
tests/                     54 unit tests
docs/DESIGN.md             why it is built this way
examples/crontab.sample    a sample to pipe into the tool
```

## About this repository

This repository is also a **measurement instrument**.

It is maintained as the subject of a study on how source-code search engines decide
which public repositories to index, and how long that decision takes to change. The
study needs a small, honest, *real* project rather than a synthetic fixture — a
repository of random strings would confound "is it interesting?" with "is it
indexed?", which is exactly the question under investigation.

Concretely, that means:

- The code here is genuine and usable. Nothing in it is a placeholder, and if you
  find `cronplain` useful, please use it.
- The repository's star count, its visibility in code search, and its commit
  timestamps are all read as data points over a period of several weeks.
- Star counts are **never** bought, traded, or otherwise manufactured. If you star
  this repository, that is a genuine signal and it will be recorded as one.
- No third-party code is bundled, no credentials of any kind are present, and the
  project deliberately has zero runtime dependencies.

If you would rather not participate, please simply ignore the repository — no other
action is needed, and none of the measurements depend on any particular visitor.

## License

MIT. See `LICENSE`.
