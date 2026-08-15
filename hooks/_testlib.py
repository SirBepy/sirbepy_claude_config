"""Shared scaffold for hooks/test_*.py suites: the by-path module loader and
the case-runner/summary mechanics every suite reimplemented independently.

Same-directory import works with no PYTHONPATH or package install because
every suite runs as `python hooks/test_x.py`: Python prepends the script's
own directory (hooks/) to sys.path[0], so a bare `import _testlib` resolves.
"""

import importlib.util
from pathlib import Path


def load_module(name: str, path: Path):
    """Load a hook by file path via spec_from_file_location + exec_module,
    since hook filenames contain hyphens and are not importable by name.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_cases(cases, check) -> list:
    """Run each case through check(case) -> ok:bool, which prints its own
    PASS/FAIL line. Label is case[-1] by convention across every suite.
    Returns the failing labels without printing a summary, so callers can
    combine several case lists before the final footer.
    """
    return [case[-1] for case in cases if not check(case)]


def report(ok: bool, label: str) -> bool:
    """Print a bare "PASS: label" / "FAIL: label" line and return ok, for
    ad hoc checks outside a cases list (e.g. stateful setup sequences).
    """
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    return ok


def summarize(fails: list, *, style: str = "list") -> int:
    """Print the ALL PASS / failure footer and return the matching exit
    code. style="count" prints an N FAILURE(S) footer instead of the label
    list, matching test_shortcut_create_guard's pre-existing format.
    """
    if style == "count":
        print(f"\n{'ALL PASS' if not fails else f'{len(fails)} FAILURE(S)'}")
    else:
        print("\nALL PASS" if not fails else f"\nFAILURES: {fails}")
    return 0 if not fails else 1
