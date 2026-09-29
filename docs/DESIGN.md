# cronplain — design notes

Short notes on the three decisions that shaped the code, kept here rather than in
comments so they can be read in one sitting.

## 1. Why the output is a sentence and not a table

A table of expanded field values is more precise, but it does not answer the question
people actually have, which is "when does this thing run". So `explain` produces one
sentence and `--json` carries the precise form for anything that needs it. The two
are generated from the same parsed object, which keeps them from drifting apart.

The sentence is built with templates rather than a grammar:

- an **arithmetic ladder** is described by its shape (`9-17` -> "between 09:00 and
  17:59", `*/15` -> "every 15 minutes");
- anything that is *not* a ladder falls back to an explicit list.

That fallback is deliberate. A template engine that only handles the pretty cases
will eventually mis-describe the others; falling back to a list costs a few words and
is never wrong. The one rule that is not negotiable is rule 3 in `explain.py`'s
module docstring: **never print something that reads as an intersection when the
scheduler will union.**

### A bug worth remembering

The first version of the ladder detector compared the value set against
`range(field.lo, field.hi + 1, gap)` — the whole field, not the observed span. That
worked for `*/15` (which really does span the field) and silently failed for `9-17`,
a completely ordinary hour range. The symptom was cosmetic (nine hours listed one per
line instead of one clause), which is precisely why it survived a first test pass.
The fix checks the observed span: `values == range(first, last + 1, gap)`.

## 2. The day-of-month OR day-of-week rule

Vixie cron runs a job when **either** restricted day field matches. This is old,
documented, and constantly forgotten. Two consequences for this codebase:

- `day_of_month` and `day_of_week` cannot be treated as independent filters. The rule
  lives in exactly one function, `field.matches`, so there is one place to audit.
- The English output has to say "or" out loud, and the CLI emits a warning by default.
  `--strict` promotes the warning to a non-zero exit for use in CI, where a silent
  fifty-per-year job is more expensive than a failed build.

## 3. Exit codes as an interface

`cronplain` is meant to be callable from a pre-commit hook, so the exit codes are part
of the contract:

| code | meaning |
|---|---|
| 0 | parsed, possibly with warnings |
| 1 | not a valid five-field cron line (or a warning under `--strict`) |
| 2 | bad command line (argparse's own convention) |

Errors go to stderr, results to stdout, so `cronplain --check` can be used as a pure
predicate with its output discarded.

## 4. What is intentionally out of scope

- **`@daily`-style macros.** They are a crontab file feature, not a five-field
  expression, and supporting them would mean accepting a second grammar.
- **Nicknames such as `@reboot`.** Same reason.
- **Next-run-time calculation.** Useful, but it needs a timezone and a start instant,
  which turns a pure parser into a stateful scheduler. That belongs in a different tool.
- **Second-level granularity.** Five fields means five fields; six-field dialects vary
  too much between implementations to guess.
