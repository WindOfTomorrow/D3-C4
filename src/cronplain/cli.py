"""Command-line front end: ``cronplain "<expression>"``.

Exit codes are the reason this module exists rather than a two-line ``__main__``:
``cronplain --check`` is meant to be usable from a pre-commit hook or a CI step, so
"valid" and "invalid" have to map onto distinct codes, and warnings must be able to
fail the build without being mistaken for a syntax error.

===== ==========================================================
code  meaning
===== ==========================================================
0     the expression parsed (possibly with warnings)
1     the expression is not a valid five-field cron line
2     bad command line (argparse's own convention)
===== ==========================================================
"""

from __future__ import annotations

import argparse
import json
import sys

from cronplain import __version__
from cronplain.explain import describe, warnings
from cronplain.field import CronError, parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronplain",
        description="Explain a five-field cron expression in plain English.",
        epilog="Use '-' (or pipe without an argument) to read expressions from stdin, one per line.",
    )
    parser.add_argument("expression", nargs="?", default="-",
                        help="the cron expression, or '-' for stdin")
    parser.add_argument("--json", action="store_true",
                        help="emit the expanded fields as JSON instead of English")
    parser.add_argument("--check", action="store_true",
                        help="validate only; print nothing on success")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings (e.g. the day-of-month OR day-of-week trap) as errors")
    parser.add_argument("--version", action="version", version=f"cronplain {__version__}")
    return parser


def _one(expression: str, args: argparse.Namespace) -> tuple[int, str]:
    """Render a single expression. Returns ``(exit_code, text_to_print)``."""
    try:
        schedule = parse(expression)
    except CronError as exc:
        return 1, f"error: {exc}"

    note_list = warnings(schedule)
    if args.strict and note_list:
        joined = "; ".join(note_list)
        return 1, f"error: {expression}: {joined}"

    if args.check:
        return 0, ""

    lines = []
    if args.json:
        payload = {"expression": schedule.expression, "explanation": describe(schedule),
                   "fields": schedule.to_dict(), "warnings": note_list}
        lines.append(json.dumps(payload, indent=2, sort_keys=True))
    else:
        lines.append(describe(schedule))
        lines.extend(f"warning: {n}" for n in note_list)
    return 0, "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.expression == "-":
        sources = [line.strip() for line in sys.stdin if line.strip()
                   and not line.lstrip().startswith("#")]
        if not sources:
            print("error: no expression given and stdin was empty", file=sys.stderr)
            return 1
    else:
        sources = [args.expression]

    worst = 0
    for expression in sources:
        code, text = _one(expression, args)
        if text:
            stream = sys.stdout if code == 0 else sys.stderr
            print(text, file=stream)
        worst = max(worst, code)
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
