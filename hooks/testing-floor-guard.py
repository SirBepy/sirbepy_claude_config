"""Stop hook (todo 427): makes CLAUDE.md's testing floor ("run every fast
check the project has before claiming done") a gate a turn cannot pass while
red, instead of prose Claude has to remember under pressure.

Wired in settings.json since 2026-10-08 (Stop, plus testing-floor-flag.py on
PostToolUse).
A Stop hook blocks EVERY session on this machine from ending its current
turn if it misfires, so any change here needs both test suites green before
it lands, and the escape hatch below is the first thing to reach for if a
session ever cannot end a turn.

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

Question exemption: a turn whose last report_turn_status (read from the
payload's own transcript) is "question" is waiting on the dev, not claiming
done, so it ends without running checks or spending an attempt; the flag is
kept and the next non-question turn is checked. An unreadable transcript or a
failing reader means no exemption.

Close exemption: a turn that already called the close_session MCP tool is
never blocked and runs no checks, because the host ends the session when the
turn completes and a block would only keep a "closed" chat open.

Dont-test exemption: a real user prompt anywhere in the session transcript that
says to skip testing ("don't test", "skip tests", "no need to test") ends the
gate for the rest of the session, per CLAUDE.md's standing-instruction rule.

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
reminder.py both fail open on the identical shape of try/except).

Does not run e2e/Playwright or any slow suite - CLAUDE.md explicitly keeps
those out of the fast-checks floor, and a Stop hook is the worst place to
violate that (todo's own Notes section).
"""

import json
import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import is_injected_user_entry, is_tool_result_entry, iter_turn_tool_uses, read_payload
    from _testing_floor_lib import (
        ESCAPE_ENV_VAR,
        clear_state,
        is_agent_call,
        read_state,
        resolve_cap,
        resolve_skip_flag_path,
        resolve_state_dir,
        run_checks,
        running_background_agents,
        write_state,
    )
except Exception as e:
    sys.stderr.write(f"[testing-floor-guard] FATAL: cannot import helpers ({e}); failing open.\n")
    sys.exit(0)


def last_turn_status(transcript_path: str) -> str | None:
    """The status argument of this turn's LAST report_turn_status call,
    lower-cased, or None when the turn made none or the transcript cannot be
    read. Same turn scoping as send-message-stop-guard.py: only tool calls
    after the latest real user entry count, so an earlier turn's "question"
    never exempts a later turn. Any parse trouble reads as None, which
    leaves the gate behaving exactly as it did before this reader existed.
    """
    if not transcript_path:
        return None
    try:
        status = None
        for name, tool_input in iter_turn_tool_uses(transcript_path):
            if name.rsplit("__", 1)[-1] == "report_turn_status" and isinstance(tool_input, dict):
                value = tool_input.get("status")
                status = value.strip().lower() if isinstance(value, str) else None
        return status
    except Exception:
        return None


def turn_called_tool(transcript_path: str, tool_name: str) -> bool:
    """True when this turn made a call to the tool whose bare name (the part
    after the last "__") is `tool_name`. Same turn scoping as last_turn_status;
    any parse trouble reads as False, which leaves the gate running its checks.
    """
    if not transcript_path:
        return False
    try:
        return any(name.rsplit("__", 1)[-1] == tool_name for name, _input in iter_turn_tool_uses(transcript_path))
    except Exception:
        return False


def closed_this_turn(transcript_path: str) -> bool:
    return turn_called_tool(transcript_path, "close_session")


# An explicit "don't test" from the dev stands for the rest of the session
# (CLAUDE.md, Testing & verification floor). Deliberately narrow: a verb that
# means "do not" directly in front of "test(s)", so "add tests" never matches.
_DONT_TEST_RE = re.compile(
    r"\b(?:don'?t|do not|never|skip|no need to|without)\s+"
    r"(?:(?:run|running|write|writing|do|doing)\s+)?(?:the\s+|any\s+|more\s+)?tests?"
    # The phrase must end there (optionally after a filler word), so a scoped
    # request like "don't test the CSS" never switches the floor off.
    r"(?:\s+(?:this|it|that|these|those|here|please|now|yet|anything|everything|for now|at all)){0,3}"
    r"\s*(?:[.,!?;:]|$)",
    re.IGNORECASE | re.MULTILINE,
)


def _user_text(entry: dict) -> str:
    content = (entry.get("message", {}) or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def dev_said_dont_test(transcript_path: str) -> bool:
    """True when any real user prompt in this session's transcript says to skip
    testing. Tool results, harness-injected entries and assistant text never
    count, so a quoted phrase cannot switch the gate off. Any read trouble is
    False, which leaves the gate running its checks."""
    if not transcript_path:
        return False
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if (
                    entry.get("type") == "user"
                    and not is_tool_result_entry(entry)
                    and not is_injected_user_entry(entry)
                    and _DONT_TEST_RE.search(_user_text(entry))
                ):
                    return True
    except OSError:
        return False
    return False


def evaluate(
    payload: dict,
    *,
    state_dir: Path,
    skip_flag_path: Path,
    cap: int,
    run_checks_fn=run_checks,
    env: dict | None = None,
    running_agents_fn=running_background_agents,
    status_fn=last_turn_status,
    closed_fn=closed_this_turn,
    dont_test_fn=dev_said_dont_test,
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

    # A turn that ends on report_turn_status "question" is waiting on the dev
    # (a design iteration whose tests are knowingly red until he approves
    # the design), so it is not a "done" claim to verify. Allowed without
    # running checks or spending an attempt, and the flag stays so the next
    # turn that does not end on a question is checked as usual. Keyed to the
    # payload's own transcript only, never a shared marker, so a concurrent
    # session's floor is unaffected.
    try:
        turn_status = status_fn(payload.get("transcript_path") or "")
    except Exception:
        turn_status = None
    if turn_status == "question":
        return None

    # A session that already called close_session ends when this turn
    # completes, so a block here has no later turn to fix anything in: it only
    # leaves a chat open that was reported closed. Allowed without
    # running checks or spending an attempt; the flag is left for /close's own
    # verification record.
    try:
        closing = bool(closed_fn(payload.get("transcript_path") or ""))
    except Exception:
        closing = False
    if closing:
        return None

    # The dev said not to test: no checks, no attempt spent, flag kept.
    if dont_test_fn(payload.get("transcript_path") or ""):
        return None

    state = read_state(flag_path)
    attempts = int(state.get("attempts") or 0)
    root = state.get("root") or "."
    paths = state.get("paths") or []

    # This session's own background builders are still editing: their files
    # are half-written, so defer. The flag stays, and the first turn ending
    # after they all report runs the check.
    transcript_path = payload.get("transcript_path")
    if transcript_path and running_agents_fn(transcript_path):
        return None

    if attempts >= cap:
        # Retry cap already spent on this unfixed edit - release rather
        # than run the check again, so a genuinely unfixable failure
        # terminates here instead of blocking forever.
        clear_state(flag_path)
        return None

    # paths: this session's accumulated edited-source-paths list (written
    # by testing-floor-flag.py), forwarded so the "scripts repo" row can
    # target py_compile + the matching self-test instead of running the
    # whole ci/run_all.py suite. An old state file with no "paths" key at
    # all (state() default [] above) means that row has nothing targeted
    # to verify and passes - it never falls back to the full suite.
    ok, summary = run_checks_fn(Path(root), paths=paths)
    if ok:
        clear_state(flag_path)
        return None

    attempts += 1
    write_state(flag_path, {"attempts": attempts, "root": root, "paths": paths})
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
