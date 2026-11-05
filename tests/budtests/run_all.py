"""Run the in-process suites: every module in this folder but support and run_all, or the
modules named on the command line; print one line per suite and exit 1 when any fails."""

import importlib
import inspect
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from budtestlibrary import BudTestCase  # noqa: E402

import tests.budtests.support  # noqa: E402,F401

SKIP = {"__init__", "support", "run_all", "config", "parameters", "suites"}


def suite_classes(module_name: str) -> list[type]:
    """The BudTestCase classes a suite module defines, in source order."""
    module = importlib.import_module(f"tests.budtests.{module_name}")
    found = [
        value
        for value in vars(module).values()
        if inspect.isclass(value)
        and issubclass(value, BudTestCase)
        and value.__module__ == module.__name__
    ]
    return sorted(found, key=lambda cls: inspect.getsourcelines(cls)[1])


def main(names: list[str]) -> int:
    """Run the selected suite modules and report each class's result."""
    available = sorted(p.stem for p in HERE.glob("*.py") if p.stem not in SKIP)
    unknown = [name for name in names if name not in available]
    if unknown:
        print("unknown suite(s): " + ", ".join(unknown))
        return 2
    results = []
    for module_name in names or available:
        for cls in suite_classes(module_name):
            results.append((f"{module_name}.{cls.__name__}", cls().run()))
    for name, passed in results:
        print(f"{'PASSED' if passed else 'FAILED'}  {name}")
    print(f"{sum(p for _, p in results)} of {len(results)} suites passed")
    return 0 if results and all(passed for _, passed in results) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
