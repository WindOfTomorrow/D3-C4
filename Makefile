# cronplain — development tasks.
#
# Every target runs with the plain system interpreter: the project has no runtime
# dependencies, and the test suite adds `src` to sys.path itself, so there is nothing
# to install and no virtualenv to activate.

PYTHON ?= python3
SRC    := src/cronplain

.PHONY: help run json test doctest compile check clean

help:
	@echo "make run E='*/15 9-17 * * MON-FRI'   explain one expression"
	@echo "make test                              unit tests"
	@echo "make doctest                           examples embedded in docstrings"
	@echo "make check                             compile + test + doctest"
	@echo "make clean                             remove __pycache__ directories"

# Example:  make run E='0 6 * * *'
E ?= */15 9-17 * * MON-FRI
run:
	PYTHONPATH=src $(PYTHON) -m cronplain "$(E)"

json:
	PYTHONPATH=src $(PYTHON) -m cronplain --json "$(E)"

test:
	$(PYTHON) -m unittest discover -s tests -t .

doctest:
	PYTHONPATH=src $(PYTHON) -m doctest $(SRC)/field.py $(SRC)/explain.py

compile:
	$(PYTHON) -m compileall -q $(SRC) tests

check: compile test doctest

clean:
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	find . -name '*.py[co]' -delete
