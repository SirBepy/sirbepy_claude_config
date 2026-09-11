"""Stop hook (todo 427): makes CLAUDE.md's testing floor ("run every fast
check the project has before claiming done") a gate a turn cannot pass while
red, instead of prose Claude has to remember under pressure.

*** NOT WIRED INTO settings.json BY THIS DISPATCH - READ THIS BEFORE WIRING. ***
A Stop hook blocks EVERY session on this machine from ending its current
turn if it misfires. Four other live sessions share this checkout today; a
bad matcher or a bug here would take turn-completion away from all of them
at once, with the dev away and nobody able to edit settings.json mid-turn to
turn it off. The todo itself calls this the highest-blast-radius item in its
batch. This file (plus testing-floor-flag.py and _testing_floor_lib.py) is
the complete, tested artifact; wiring it into settings.json is a decision
for Joe to make while watching the first few live turns, not something this
dispatch is allowed to flip on unattended.

Escape hatch (must exist before any blocking logic does - see the todo's own
ordering requirement): set the env var CLAUDE_TESTING_FLOOR_SKIP to any
truthy string, or create the file `_testing_floor_lib.resolve_skip_flag_path()`
points at (hooks/.testing-floor-skip by default) - either makes this hook
exit 0 unconditionally, every time, for every session, with no settings.json
edit and no in-conversation phrase for a session to have "seen" first. Both
are dev-controlled, external to the transcript, and read fresh on every
invocation.

Retry cap: `_testing_floor_lib.DEFAULT_CAP` (3) consecutive blocks against
the SAME unfixed edit (a fresh Edit/Write resets the counter via
testing-floor-flag.py, so genuine fix attempts are never penalised - only a
turn that ends again without editing anything spends the budget). At the
cap, the flag is cleared and the turn is allowed to end with checks still
red - a gate with no way out gets disabled entirely, which is worse than no
gate (the todo's own framing).

Activation gate: no-ops unless testing-floor-flag.py (a PostToolUse hook)
already wrote a per-session pending-state file this session - i.e. unless
THIS turn's own Edit/Write/MultiEdit/NotebookEdit touched a recognised
source file. A prose-only turn, a read-only turn, or a turn that only
touched a config/doc file therefore never even reaches the check-running
code below.

Subagent exclusion: never fires when the payload carries `agent_id` (reuses
agent-todo-write-guard.py's own `is_agent_call` test, per this dispatch's
instruction to reuse rather than reinvent it). A dispatched builder has its
own verify-floor obligation in its dispatch prompt; this gate is for the
top-level session only.

Fails open on its own errors: every unexpected exception in `evaluate()` is
caught in `main()` and treated as "allow the turn to end" (see the bottom
try/except too). A hook that traps a turn because ITS OWN code broke is
strictly worse than a missed check - the same principle every other Stop
hook in this repo already follows (em-dash-guard.py, ui-screenshot-
reminder.py, status-marker-guard.py all fail open on the identical shape of
try/except).

Does not run e2e/Playwright or any slow suite - CLAUDE.md explicitly keeps
those out of the fast-checks floor, and a Stop hook is the worst place to
violate that (todo's own Notes section).
"""

import json
import os
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload
    from _testing_floor_lib import (
        ESCAPE_ENV_VAR,
        clear_state,
        is_agent_call,
        read_state,
        resolve_cap,
        resolve_skip_flag_path,
        resolve_state_dir,
        run_checks,
        write_state,
    )
except Exception as e:
    sys.stderr.write(f"[testing-floor-guard] FATAL: cannot import helpers ({e}); failing open.\n")
    sys.exit(0)


def evaluate(
    payload: dict,
    *,
    state_dir: Path,
    skip_flag_path: Path,
    cap: int,
    run_checks_fn=run_checks,
    env: dict | None = None,
):
    """Pure decision core: returns a dict to print+block on, or None to
    allow the turn to end silently. Every dependency (state dir, skip-flag
    path, cap, the check runner, and the environment mapping) is a
    parameter so a test never touches this repo's real hooks/ directory or
    real environment - see the module docstring's determinism requirement.
    """
    env = os.environ if env is None else env

    # Subagent exclusion FIRST: a dispatched agent is never this gate's target.
    if is_agent_call(payload):
        return None

    # Escape hatch SECOND, before any state is even read: a dev-set flag
    # must win over every other branch below, unconditionally.
    if env.get(ESCAPE_ENV_VAR) or skip_flag_path.exists():
        return None

    session_id = payload.get("session_id") or ""
    if not session_id:
        # Can't scope state safely without one - fail open rather than
        # guess at a shared/global flag no session actually owns.
        return None

    flag_path = state_dir / session_id
    if not flag_path.is_file():
        # Activation gate: testing-floor-flag.py never marked this session
        # dirty, so this turn touched no recognised source file (or hasn't
        # yet). Nothing to verify.
        return None

    state = read_state(flag_path)
    attempts = int(state.get("attempts") or 0)
    root = state.get("root") or "."

    if attempts >= cap:
        # Retry cap already spent on this unfixed edit - release rather
        # than run the check again, so a genuinely unfixable failure
        # terminates here instead of blocking forever.
        clear_state(flag_path)
        return None

    ok, summary = run_checks_fn(Path(root))
    if ok:
        clear_state(flag_path)
        return None

    attempts += 1
    write_state(flag_path, {"attempts": attempts, "root": root})
    return {
        "decision": "block",
        "reason": (
            f"[testing-floor-guard] Fast checks still failing (attempt {attempts}/{cap}): "
            f"{summary} Fix the failure and end the turn again, or use the documented escape "
            f"hatch (CLAUDE_TESTING_FLOOR_SKIP env var, or the skip-flag file) if ending with "
            f"the failure visible is the right call this time."
        ),
    }


def main() -> None:
    payload = read_payload()
    result = evaluate(
        payload,
        state_dir=resolve_state_dir(),
        skip_flag_path=resolve_skip_flag_path(),
        cap=resolve_cap(),
    )
    if result is not None:
        print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        # Fail open: a bug in THIS hook must never trap a turn. Every path
        # through evaluate() above already tries to avoid raising, but this
        # is the backstop if one does anyway (e.g. a read_payload() JSON
        # parse failure before evaluate() is even called).
        sys.stderr.write(f"[testing-floor-guard] hook error, failing open: {e}\n")
        sys.exit(0)
