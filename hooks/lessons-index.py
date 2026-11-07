"""SessionStart hook (todo 1154): put the global lessons index in every session.

Cross-project lessons live as memory-format files in ~/.claude/lessons/ (or
$CLAUDE_LESSONS_DIR), promoted there by skills/cleanup-memory/lessons_sweep.py.
That sweep also writes INDEX.md, a small index capped at INDEX_BYTE_CAP bytes,
because CLAUDE.md has no headroom for lessons. This hook injects INDEX.md as
SessionStart additionalContext; the individual lessons that declare `triggers:`
load later through hooks/memory-trigger.py, which scans the same folder.

Prints nothing when the folder or the index is absent, re-applies the byte cap
at read time (a hand-edited index cannot grow the injection), and fails open on
any error: this runs at the start of every session.
"""

import json
import os
import sys

INDEX_BYTE_CAP = 4096


def lessons_dir() -> str:
    return os.environ.get("CLAUDE_LESSONS_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "lessons")


def capped_index(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read(INDEX_BYTE_CAP + 1)
    if len(raw) <= INDEX_BYTE_CAP:
        return raw.decode("utf-8", errors="replace").strip()
    cut = raw[:INDEX_BYTE_CAP].rsplit(b"\n", 1)[0]
    return cut.decode("utf-8", errors="replace").strip() + "\n- (index truncated at the byte cap)"


def main() -> int:
    try:
        sys.stdin.read()
        index = os.path.join(lessons_dir(), "INDEX.md")
        if not os.path.isfile(index):
            return 0
        text = capped_index(index)
        if not text:
            return 0
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}))
    except Exception as e:
        sys.stderr.write(f"[lessons-index] hook error, failing open: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
