"""PreToolUse hook (todo 1153): inject a memory file when its trigger fires.

Thin wrapper; the format, table and matching live in _memory_triggers.py
(read its docstring for the frontmatter a memory declares). Edit, Write, Read
and Skill calls get the matched memory as additionalContext, once per session.
An Agent dispatch is held once (exit 2) with the memory text in the message,
because a subagent starts with none of this context and the orchestrator must
pass it into the dispatch prompt; the retry is not held again.

Fails open on any error and writes nothing to the tool call's path: this runs
on every covered tool call in every session.
"""

import json
import os
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)


def main() -> int:
    try:
        import _memory_triggers
        payload = json.loads(sys.stdin.read().lstrip("﻿") or "{}")
        code, out, err = _memory_triggers.run_hook(payload)
    except Exception as e:
        sys.stderr.write(f"[memory-trigger] hook error, failing open: {e}\n")
        return 0
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main())
