"""PreToolUse hook (todo 404): hard-blocks a dispatched agent writing or
editing a backlog file directly under `.claude/todos/` (never `done/` or
`.claims/` - see `todos_target_dir` below).

`refs/delegation-doctrine.md`'s "Out-of-scope findings" section states the
rule in prose: a subagent never writes into `.claude/todos/`, no matter how
well-formed the finding - only the orchestrator can allocate an id without
racing a concurrent session, and an out-of-band write bypasses the
claim/id-allocation guard the backlog contract defines. A PreToolUse guard
was considered and rejected for this once (todo 291, 2026-08-12) on the
theory that the report-back channel alone was enough. It was not: on
2026-08-19, a `/mega-todos` builder wrote `.claude/todos/391-...md` directly
mid-dispatch, bypassing the report-back channel even though its own dispatch
prompt carried the "never write into .claude/todos/" line verbatim. It got
lucky on the id; the original todo 291 incident's `263-...` write collided
with an already-taken id in the same run.

The rejection's remaining open question - whether a PreToolUse hook can even
tell a subagent's write from the orchestrator's - is settled, not assumed.
Probed 2026-09-10 (recorded in `refs/delegation-doctrine.md`) and
re-verified live on 2026-09-11 for this build (this hook's own probe
predecessor captured a real dispatched-agent Write payload; see the todo's
Notes and this repo's commit history for the captured field list): the
PreToolUse payload `hooks/_hooklib.py`'s `read_payload` returns carries
`agent_id` (and `agent_type`) if, and only if, the call comes from a
dispatched agent - a top-level orchestrator's own denied Write to the same
path carries neither key. `agent_id` presence is therefore the matcher this
hook denies on.

Deliberately a hard block, unlike `todo-duplicate-guard.py`'s advisory
duplicate check: there is no legitimate case for a subagent to create or
edit a backlog `.md` here (claiming and heartbeating a todo write to
`.claims/`, a sibling directory `todos_target_dir` already excludes, never
to a `\\d+-*.md` file in `todos/` itself), so a false positive would only
ever block a write the doctrine already says should not happen - the
subagent's correct move is always to report the finding instead.
"""

import importlib.util
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[agent-todo-write-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)


def _load_todos_target_dir():
    """Import `todos_target_dir` from `todo-duplicate-guard.py` by path
    (hyphenated filename, not importable by name) rather than re-implementing
    its path-shape logic - same technique `hooks/_testlib.py`'s `load_module`
    uses for the test suites of both guards.
    """
    spec = importlib.util.spec_from_file_location(
        "todo_duplicate_guard", _HOOKS_DIR / "todo-duplicate-guard.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.todos_target_dir


try:
    todos_target_dir = _load_todos_target_dir()
except Exception as e:
    sys.stderr.write(f"[agent-todo-write-guard] FATAL: cannot load todos_target_dir from todo-duplicate-guard.py ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)


def is_agent_call(payload: dict) -> bool:
    """True when this PreToolUse call came from a dispatched agent, not the
    top-level orchestrator session. `agent_id` is present if, and only if,
    the call comes from a dispatched agent (probed 2026-09-10, re-verified
    2026-09-11 - see module docstring).
    """
    return bool(payload.get("agent_id"))


def main() -> None:
    payload = read_payload()
    if (payload.get("tool_name") or "") not in ("Write", "Edit"):
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if todos_target_dir(file_path) is None:
        sys.exit(0)

    if not is_agent_call(payload):
        sys.exit(0)

    deny(
        "[agent-todo-write-guard] A dispatched agent may not create or edit a file directly "
        "under .claude/todos/ - only the orchestrator allocates ids and resolves duplicates "
        "there (see refs/delegation-doctrine.md's \"Out-of-scope findings\" section). Put this "
        "finding in your report's \"Out-of-scope findings\" section instead; the orchestrator "
        "will file it as a properly allocated todo after your dispatch returns."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[agent-todo-write-guard] hook error, failing open: {e}\n")
        sys.exit(0)
