"""Allow ``python3 -m cronplain "<expression>"`` without installing the package."""

from cronplain.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
