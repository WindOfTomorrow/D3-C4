"""cronplain — read a cron expression and say what it means in plain English.

The package is deliberately dependency-free: everything is built on the standard
library, so ``python3 -c "import cronplain"`` works on a stock interpreter with no
installation step beyond being on ``sys.path``.

Public surface
--------------
``parse(expression)``
    Returns a :class:`~cronplain.field.Schedule` describing every field.
``explain(expression)``
    Returns a one-line English description of when the job runs.
``CronError``
    Raised for anything that is not a valid five-field cron expression.

Example
-------
>>> from cronplain import explain
>>> explain("*/15 9-17 * * MON-FRI")
'Every 15 minutes, between 09:00 and 17:59, on Monday to Friday'
"""

from cronplain.explain import explain
from cronplain.field import CronError, Schedule, parse

__all__ = ["explain", "parse", "CronError", "Schedule", "__version__"]

__version__ = "0.3.1"
