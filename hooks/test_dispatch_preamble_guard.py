"""Self-test for dispatch-preamble-guard.py.

Run directly: python hooks/test_dispatch_preamble_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "dispatch-preamble-guard.py"
)

STAGING = "Stage your changes but do NOT commit. The main agent will run /commit after your report-back."
UNSTAGED = "Leave all changes unstaged. Never run `git add`. The main agent will run /commit by pathspec after your report-back."
COMMIT_OWN = "Commit your own work with /commit before your report-back, by pathspec, only the files you changed."
PARAPHRASE = "`run_in_background` is FORBIDDEN in builder subagents"
# Mirrors the paste of refs/builder-preamble.md's auto-background paragraph.
BACKGROUND = (
    f"{PARAPHRASE}. The harness auto-backgrounds any command past 120 seconds "
    "whether you asked it to or not."
)
READ_FILE_SHAPE = (
    "Read C:\\Users\\tecno\\.claude\\refs\\builder-preamble.md in full now and follow its fenced "
    "code block as your working preamble VERBATIM.\n\n"
    "run_in_background is FORBIDDEN in builder subagents."
)
SCREENSHOT = "save them under `.for_bepy/screenshots/12345-6789/`"
FULL_PROMPT = f"{STAGING}\n\n{BACKGROUND}\n\n{SCREENSHOT}\n\nDo the task."

# (prompt, expect_missing_nonempty, label)
CASES = [
    (FULL_PROMPT, False, "all three markers present"),
    (FULL_PROMPT.replace(STAGING, ""), True, "staging line missing"),
    (FULL_PROMPT.replace(BACKGROUND, ""), True, "run_in_background/FORBIDDEN line missing"),
    (FULL_PROMPT.replace(SCREENSHOT, ""), True, "screenshot id line missing"),
    (f"{UNSTAGED}\n\n{BACKGROUND}\n\nREAD-ONLY DISPATCH\n\nDo the task.", False, "READ-ONLY DISPATCH opts out of screenshot marker"),
    ("do the thing, no markers at all", True, "nothing present"),
    (f"READ-ONLY DISPATCH\n\n{STAGING}\n\n{BACKGROUND}\n\nDo the task.", True, "read-only + Stage your changes is denied"),
    (
        f"READ-ONLY DISPATCH\n\n{UNSTAGED}\n\n{BACKGROUND}\n\nDo the task.",
        False,
        "read-only + Leave all changes unstaged passes",
    ),
    (FULL_PROMPT, False, "non-read-only + Stage your changes passes"),
    (
        f"{COMMIT_OWN}\n\n{BACKGROUND}\n\n{SCREENSHOT}\n\nDo the task.",
        False,
        "Commit your own work with /commit satisfies the staging line",
    ),
    (
        # UNSTAGED alongside keeps the staging-line check satisfied, so only the
        # read-only + commit rule can deny this prompt.
        f"READ-ONLY DISPATCH\n\n{UNSTAGED}\n\n{COMMIT_OWN}\n\n{BACKGROUND}\n\nDo the task.",
        True,
        "read-only + Commit your own work is denied",
    ),
    (
        f"{STAGING}\n\n{PARAPHRASE}\n\n{SCREENSHOT}\n\nDo the task.",
        True,
        "paraphrase-only (no auto-background paragraph) is denied",
    ),
    (
        f"{UNSTAGED}\n\n{PARAPHRASE}\n\nREAD-ONLY DISPATCH\n\nDo the task.",
        True,
        "read-only + paraphrase-only is denied",
    ),
    (
        # builder-preamble.md named but no VERBATIM instruction: still a paraphrase.
        f"{STAGING}\n\nSee builder-preamble.md for rules. {PARAPHRASE}\n\n{SCREENSHOT}",
        True,
        "preamble file named without VERBATIM is denied",
    ),
    (
        # VERBATIM alone, without naming the file, is not the sanctioned shape.
        f"{STAGING}\n\nFollow the rules VERBATIM. {PARAPHRASE}\n\n{SCREENSHOT}",
        True,
        "VERBATIM without the preamble file is denied",
    ),
    (
        f"{STAGING}\n\n{READ_FILE_SHAPE}\n\n{SCREENSHOT}",
        False,
        "read-the-preamble-file + VERBATIM shape passes",
    ),
    (
        f"{UNSTAGED}\n\n{READ_FILE_SHAPE}\n\nREAD-ONLY DISPATCH\n\nDo the task.",
        False,
        "read-only + read-the-preamble-file shape passes",
    ),
    (
        f"{UNSTAGED}\n\n{BACKGROUND}\n\nREAD-ONLY DISPATCH\n\nDo the task.",
        False,
        "read-only + verbatim auto-background paragraph passes",
    ),
    (
        # Read-file shape that still drops FORBIDDEN stays denied by the older check.
        f"{STAGING}\n\nRead builder-preamble.md and follow it VERBATIM.\n\n{SCREENSHOT}",
        True,
        "read-file shape without run_in_background/FORBIDDEN is denied",
    ),
]


def check(case) -> bool:
    prompt, expect_missing_nonempty, label = case
    missing = guard.missing_markers(prompt)
    got = bool(missing)
    ok = got == expect_missing_nonempty
    print(f"{'PASS' if ok else 'FAIL'}: {label} (missing={missing})")
    return ok


fails = _testlib.run_cases(CASES, check)

# tool_name filtering: only Agent/Task dispatches are inspected at all.
for name in ("Agent", "Task"):
    if not _testlib.report(name in guard.DISPATCH_TOOLS, f"{name} is a recognized dispatch tool"):
        fails.append(f"{name} recognized")

for name in ("Bash", "Read", "Edit", "PowerShell"):
    if not _testlib.report(name not in guard.DISPATCH_TOOLS, f"{name} passes through untouched"):
        fails.append(f"{name} untouched")

# model presence: pure-presence check, exempting subagent_type "fork".
MODEL_CASES = [
    ({"model": "sonnet"}, False, "model present"),
    ({}, True, "model absent"),
    ({"model": ""}, True, "model empty string"),
    ({"model": "  "}, True, "model whitespace-only"),
    ({"subagent_type": "fork"}, False, "fork subagent_type exempt with no model"),
    ({"subagent_type": "fork", "model": "sonnet"}, False, "fork subagent_type with model still fine"),
    ({"subagent_type": "explore"}, True, "non-fork subagent_type still requires model"),
]


def check_model(case) -> bool:
    tool_input, expect_missing, label = case
    got = guard.model_missing(tool_input)
    ok = got == expect_missing
    print(f"{'PASS' if ok else 'FAIL'}: {label} (model_missing={got})")
    return ok


fails += [f"model: {label}" for (ti, expect, label) in MODEL_CASES if not check_model((ti, expect, label))]

# Dispatch templates that skills ship on disk must pass the guard as written: a
# template that drops the auto-background sentence is denied at dispatch time
# (every /code-check and /review-unpushed reviewer dispatch was blocked this way).
CLAUDE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_FILES = [
    "skills/code-check/SKILL.md",
    "skills/review-unpushed/SKILL.md",
    "refs/outbound-verify.md",
    "skills/name-brainstorm/angles.md",
    "skills/rate-it/panel.md",
    "skills/iterate-it/templates.md",
]


def extract_templates(text: str) -> list[str]:
    """Fenced code blocks and contiguous blockquote runs that mention both
    run_in_background and FORBIDDEN, i.e. the dispatch prompt templates."""
    blocks = []
    in_fence, cur = False, []
    quote = []
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_fence:
                blocks.append("\n".join(cur))
                cur = []
            in_fence = not in_fence
            continue
        if in_fence:
            cur.append(line)
        elif line.startswith(">"):
            quote.append(line[1:].lstrip(" "))
        elif quote:
            blocks.append("\n".join(quote))
            quote = []
    if quote:
        blocks.append("\n".join(quote))
    return [b for b in blocks if "run_in_background" in b and "FORBIDDEN" in b]


def check_template_file(rel: str) -> bool:
    templates = extract_templates((CLAUDE_ROOT / rel).read_text(encoding="utf-8"))
    ok = bool(templates)
    detail = f"{len(templates)} template(s)"
    for i, t in enumerate(templates):
        missing = guard.missing_markers(t)
        if missing:
            ok = False
            detail += f"; template {i} missing={missing}"
    print(f"{'PASS' if ok else 'FAIL'}: shipped template in {rel} passes the guard ({detail})")
    return ok


fails += [f"template: {rel}" for rel in TEMPLATE_FILES if not check_template_file(rel)]

# Negative: stripping the auto-background sentence from a shipped template is denied.
_cc = extract_templates((CLAUDE_ROOT / "skills/code-check/SKILL.md").read_text(encoding="utf-8"))
_stripped = _cc[0].replace(guard.AUTO_BG_PHRASE, "") if _cc else ""
if not _testlib.report(
    bool(_cc) and guard.AUTO_BG_PHRASE in _cc[0] and bool(guard.missing_markers(_stripped)),
    "code-check template without the auto-background sentence is denied",
):
    fails.append("template negative")

sys.exit(_testlib.summarize(fails, style="count"))
