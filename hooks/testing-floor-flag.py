"""PostToolUse hook (todo 427, NOT wired - see testing-floor-guard.py's
module docstring for the wiring ban and why): marks a session as "has an
unverified source-file edit" whenever this turn's own Edit/Write/MultiEdit/
NotebookEdit touches a file `_testing_floor_lib.is_source_file` recognises.

This is the activation gate half of the design (approach step 2 of the
todo): a Stop hook that ran fast checks on every turn - including a turn
that only read files, answered a question, or edited a `.md` file - would
try to run the test suite on every conversational turn. This hook is what
makes that NOT happen: `testing-floor-guard.py` only ever runs checks when
this file has written a flag for the current session.

Deliberately dumb: it does not itself decide pass/fail, run any check, or
block anything. It only records "something worth verifying changed" plus
where to verify it (`root`), and resets the per-session retry-attempt
counter to 0 - a fresh edit deserves a fresh attempt budget, so one stubborn
early failure can't eat the whole session's cap before Claude even tries a
fix (see testing-floor-guard.py for how attempts are then spent).

Also accumulates `state["paths"]`: every edited file path this session has
seen so far (deduped by exact string, as received from `tool_input` -
absolute or repo-relative, whichever the tool call gave), appended to
across calls rather than overwritten. testing-floor-guard.py forwards this
list to `run_checks` so the "scripts repo" row can target py_compile and
the matching self-test at the edited files instead of running the whole
`ci/run_all.py` suite (todo 427 defect 1). The attempts-reset above is
unaffected: a fresh edit still resets attempts to 0 even though paths
carries forward.

Never fires for a dispatched agent (mirrors testing-floor-guard.py's own
exclusion): a subagent's edits are covered by its own dispatch-level verify
floor, not this session's gate, and a dispatch's session_id may not even be
the orchestrator's - flagging it here would gate the wrong session or a
session nobody is watching to unblock.

Fails open on any error: a broken flag-writer must never itself throw a
tool call into an error state, and must never leave the ACTIVATION gate
accidentally stuck ON (worse than accidentally off - "off" just means a
missed check, matching this hook's own non-blocking nature).
"""

import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import git_repo_root, read_payload
    from _testing_floor_lib import (
        EDIT_TOOL_SUFFIXES,
        is_agent_call,
        is_source_file,
        read_state,
        resolve_state_dir,
        write_state,
    )
except Exception as e:
    sys.stderr.write(f"[testing-floor-flag] FATAL: cannot import helpers ({e}); failing open.\n")
    sys.exit(0)


def main() -> None:
    payload = read_payload()

    if is_agent_call(payload):
        sys.exit(0)

    tool_name = payload.get("tool_name") or ""
    suffix = tool_name.rsplit("__", 1)[-1] if "__" in tool_name else tool_name
    if suffix not in EDIT_TOOL_SUFFIXES:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not file_path or not is_source_file(file_path):
        sys.exit(0)

    session_id = payload.get("session_id") or ""
    if not session_id:
        sys.exit(0)

    root = git_repo_root(str(Path(file_path).parent)) or payload.get("cwd") or "."
    state_dir = resolve_state_dir()
    flag_path = state_dir / session_id
    paths = list(read_state(flag_path).get("paths") or [])
    if file_path not in paths:
        paths.append(file_path)
    write_state(flag_path, {"attempts": 0, "root": root, "paths": paths})
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[testing-floor-flag] hook error, failing open: {e}\n")
        sys.exit(0)
