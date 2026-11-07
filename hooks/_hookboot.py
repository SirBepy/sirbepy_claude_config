"""Import bootstrap for the hook stack: retries a shared module that another
session is mid-way through writing, then gets out of the way.

Every hook that imports `_hooklib` puts `import _hookboot` as the first line
of its guarded `try:` block. This module pre-imports `_hooklib` and retries
once after a short sleep on ANY failure: a half-written file (truncated, so a
SyntaxError, or an ImportError for a symbol not yet defined) is back to normal
well inside a second, while a genuinely broken module fails again on the retry.

It never decides the hook's policy. A module that is still broken after the
retry is left unimported, so the hook's own `from _hooklib import ...` raises
the real error and the hook's existing branch runs: fail-closed guards exit 2
(a broken `_hooklib` stays loud, never a silently disabled guard), fail-open
hooks exit 0. Because the retry covers every importer, one bad edit to a
shared file costs a sub-second stall on the calls that race it instead of
blocking every Bash, PowerShell, Write and Edit call until someone repairs it.

There is no tool-matcher escape from a genuinely broken `_hooklib`: the Write
and Edit guards fail closed on the same import, so the session cannot repair
it from inside. Recover from a terminal outside Claude Code (`git -C
~/.claude checkout -- hooks/_hooklib.py`), or write the file in ONE Write call
so no reader ever sees it half-finished.

Keep this file tiny and stdlib-only: it is the one module every hook imports
before anything else can be retried.
"""

import importlib
import os
import sys
import time

DEFAULT_RETRY_DELAY_S = 0.4
DELAY_ENV = "CLAUDE_HOOK_IMPORT_RETRY_DELAY_S"
SHARED_MODULES = ("_hooklib",)


def _delay_s() -> float:
    try:
        return max(0.0, float(os.environ.get(DELAY_ENV, DEFAULT_RETRY_DELAY_S)))
    except ValueError:
        return DEFAULT_RETRY_DELAY_S


def preload(*names: str, retries: int = 1) -> list:
    """Import each module, retrying `retries` times after a sleep. Returns the
    names still unimported; the caller's own import raises their real error."""
    still_broken = []
    for name in names:
        for attempt in range(retries + 1):
            try:
                importlib.import_module(name)
                break
            except Exception:
                sys.modules.pop(name, None)
                if attempt < retries:
                    time.sleep(_delay_s())
                    importlib.invalidate_caches()
                else:
                    still_broken.append(name)
    return still_broken


preload(*SHARED_MODULES)
