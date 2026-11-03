"""PreToolUse hook: block an Agent/Task dispatch whose prompt is missing one of
the three always-required canonical-preamble markers (todo 331).

Verbatim-only by design: this checks three literal substrings and nothing else.
The conditional orphan-check line is deliberately NOT enforced here - deciding
whether a dispatch runs a dev server is a heuristic guess, and this repo killed
three guess-based hooks in one day over exactly that failure mode (see
.claude/todos/PLAN.md, "Hook doctrine"). Pure string comparison only.

The staging line accepts three literal options: "Stage your changes but do NOT
commit", "Leave all changes unstaged", or "Commit your own work with /commit"
(the last for a dispatch that is deliberately allowed to commit its own files).
A READ-ONLY DISPATCH may never combine with the first or third: it has nothing
to stage or commit.

Screenshot-id check has an explicit opt-out: a prompt containing the literal
line `READ-ONLY DISPATCH` is read-only by the orchestrator's own declaration,
so it skips the screenshot marker. See refs/builder-preamble.md.

Also checks the dispatch's own `model` input is present and non-empty (todo
799), same pure-presence shape as the prompt-marker checks above. Exempts
`subagent_type: "fork"`: a fork dispatch always inherits the parent model by
design, so it has no `model` param to give.
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
STAGING_C = "Commit your own work with /commit"
SCREENSHOT_MARKER = ".for_bepy/screenshots/"
READONLY_MARKER = "READ-ONLY DISPATCH"
# First sentence of the auto-background paragraph in refs/builder-preamble.md.
AUTO_BG_PHRASE = "The harness auto-backgrounds any command past 120 seconds"
# The compact dispatch shape (skills/mega-todos/build-dispatch.ps1) tells the
# builder to read the preamble file and follow it VERBATIM instead of pasting it.
PREAMBLE_FILE = "builder-preamble.md"
READ_VERBATIM = "VERBATIM"
READONLY_REPLACEMENT_LINE = (
    "Leave all changes unstaged. Never run `git add`. "
    "The main agent will run /commit by pathspec after your report-back."
)


def missing_markers(prompt: str) -> list[str]:
    missing = []
    if STAGING_A not in prompt and STAGING_B not in prompt and STAGING_C not in prompt:
        missing.append(
            "staging line (\"Stage your changes but do NOT commit\", "
            "\"Leave all changes unstaged\", or \"Commit your own work with /commit\")"
        )
    if "run_in_background" not in prompt or "FORBIDDEN" not in prompt:
        missing.append("run_in_background ... FORBIDDEN line")
    # A one-line "run_in_background is FORBIDDEN" paraphrase satisfies the check
    # above yet drops the paragraph that tells a builder what to do when a
    # command auto-backgrounds (2026-10-13: a paraphrased preamble left a
    # builder parked ~45 minutes, ~410k tokens). Require the paragraph itself,
    # or the compact read-the-file shape that points the builder at it.
    elif not (AUTO_BG_PHRASE in prompt or (PREAMBLE_FILE in prompt and READ_VERBATIM in prompt)):
        missing.append(
            f"auto-background paragraph (\"{AUTO_BG_PHRASE}...\") from refs/builder-preamble.md, "
            f"or an instruction naming {PREAMBLE_FILE} to be followed {READ_VERBATIM}"
        )
    if READONLY_MARKER not in prompt and SCREENSHOT_MARKER not in prompt:
        missing.append(f"{SCREENSHOT_MARKER} id line (or the READ-ONLY DISPATCH opt-out)")
    # A READ-ONLY DISPATCH has nothing to stage - "Stage your changes" invites
    # exactly the `git add -A` it should never run (2026-10-08: a
    # /cleanup-memory deep-pass subagent staged two unrelated untracked files
    # this way). Use the always-true unstaged variant instead.
    if READONLY_MARKER in prompt and STAGING_A in prompt:
        missing.append(
            f"READ-ONLY DISPATCH combined with the \"{STAGING_A}\" staging line - "
            f"replace it with: \"{READONLY_REPLACEMENT_LINE}\""
        )
    # A read-only dispatch must never commit either.
    if READONLY_MARKER in prompt and STAGING_C in prompt:
        missing.append(
            f"READ-ONLY DISPATCH combined with the \"{STAGING_C}\" staging line - "
            f"a read-only dispatch must never commit; replace it with: \"{READONLY_REPLACEMENT_LINE}\""
        )
    return missing


def model_missing(tool_input: dict) -> bool:
    """True if `model` is absent/empty and this isn't a fork dispatch.

    A `subagent_type: "fork"` dispatch always inherits the parent model by
    design, so it legitimately has no `model` param - never flagged.
    """
    if tool_input.get("subagent_type") == "fork":
        return False
    return not (tool_input.get("model") or "").strip()


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    if tool_name not in DISPATCH_TOOLS:
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    prompt = tool_input.get("prompt", "") or ""

    missing = missing_markers(prompt)
    if model_missing(tool_input):
        missing.append("model (must be passed explicitly, e.g. 'sonnet' - see CLAUDE.md's Subagent model section; exempt only for subagent_type: \"fork\")")
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
