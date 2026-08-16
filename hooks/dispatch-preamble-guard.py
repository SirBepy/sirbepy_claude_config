"""PreToolUse hook: block an Agent/Task dispatch whose prompt is missing one of
the three always-required canonical-preamble markers (todo 331).

Verbatim-only by design: this checks three literal substrings and nothing else.
The conditional orphan-check line is deliberately NOT enforced here - deciding
whether a dispatch runs a dev server is a heuristic guess, and this repo killed
three guess-based hooks in one day over exactly that failure mode (see
.claude/todos/PLAN.md, "Hook doctrine"). Pure string comparison only.

Screenshot-id check has an explicit opt-out: a prompt containing the literal
line `READ-ONLY DISPATCH` is read-only by the orchestrator's own declaration,
so it skips the screenshot marker. See refs/builder-preamble.md.
"""

import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[dispatch-preamble-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

DISPATCH_TOOLS = ("Agent", "Task")

STAGING_A = "Stage your changes but do NOT commit"
STAGING_B = "Leave all changes unstaged"
SCREENSHOT_MARKER = ".for_bepy/screenshots/"
READONLY_MARKER = "READ-ONLY DISPATCH"


def missing_markers(prompt: str) -> list[str]:
    missing = []
    if STAGING_A not in prompt and STAGING_B not in prompt:
        missing.append("staging line (\"Stage your changes but do NOT commit\" or \"Leave all changes unstaged\")")
    if "run_in_background" not in prompt or "FORBIDDEN" not in prompt:
        missing.append("run_in_background ... FORBIDDEN line")
    if READONLY_MARKER not in prompt and SCREENSHOT_MARKER not in prompt:
        missing.append(f"{SCREENSHOT_MARKER} id line (or the READ-ONLY DISPATCH opt-out)")
    return missing


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    if tool_name not in DISPATCH_TOOLS:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    prompt = tool_input.get("prompt", "") or ""

    missing = missing_markers(prompt)
    if not missing:
        sys.exit(0)

    deny(
        "[dispatch-preamble-guard] Dispatch prompt is missing required preamble marker(s): "
        + "; ".join(missing)
        + ". Paste the canonical block from refs/builder-preamble.md before dispatching."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[dispatch-preamble-guard] hook error, failing open: {e}\n")
        sys.exit(0)
