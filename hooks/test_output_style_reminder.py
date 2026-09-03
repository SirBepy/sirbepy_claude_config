"""Self-test for output-style-reminder.py (todo 452).

Run directly: python hooks/test_output_style_reminder.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "output-style-reminder.py"

STYLE_MD = """---
name: Silent
description: No assistant prose, everything goes in short send_message bubbles
keep-coding-instructions: true
---

# Silent Style Active

1. **Write nothing outside tool calls** - Assistant text is not rendered.
2. **Lead with the result** - first sentence answers the question.
"""

STYLE_MD_NO_RULES = """---
name: Quiet
description: A minimal style with no numbered rules
---

Just prose, no list.
"""

STYLE_MD_WITH_COMMENT = """---
name: Terse
description: fallback description
---

<!-- reminder: Keep every reply under two sentences. -->

# Terse Style Active
"""


def make_repo(tmp_path: Path, output_style, style_files: dict, settings_file="settings.json"):
    (tmp_path / "output-styles").mkdir()
    for fname, content in style_files.items():
        (tmp_path / "output-styles" / fname).write_text(content, encoding="utf-8")
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    settings = {"outputStyle": output_style} if output_style is not None else {}
    (tmp_path / settings_file).write_text(json.dumps(settings), encoding="utf-8")
    return hooks_dir


def run_hook_in(tmp_path: Path):
    guard_copy = tmp_path / "hooks" / "output-style-reminder.py"
    guard_copy.write_text(_GUARD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(guard_copy)],
        input=json.dumps({"prompt": "hello"}),
        capture_output=True,
        text=True,
    )
    return proc


def check_silent_for(style_name, label):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        make_repo(tmp_path, style_name, {"silent.md": STYLE_MD})
        proc = run_hook_in(tmp_path)
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        return _testlib.report(ok, label)


def check_reminder_for(style_name, style_files, expect_substring, label):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        make_repo(tmp_path, style_name, style_files)
        proc = run_hook_in(tmp_path)
        ok = proc.returncode == 0 and expect_substring in proc.stdout
        return _testlib.report(ok, label)


def main() -> int:
    fails = []

    for builtin in ["default", "Proactive", "Concise", "Explanatory", "Learning"]:
        if not check_silent_for(builtin, "silent for builtin: %s" % builtin):
            fails.append(builtin)

    if not check_silent_for(None, "silent when outputStyle missing"):
        fails.append("missing outputStyle")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "output-styles").mkdir()
        hooks_dir = tmp_path / "hooks"
        hooks_dir.mkdir()
        (tmp_path / "settings.json").write_text("{ not valid json", encoding="utf-8")
        proc = run_hook_in(tmp_path)
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        if not _testlib.report(ok, "fails safe on malformed settings.json"):
            fails.append("malformed settings")

    if not check_reminder_for(
        "Silent", {"silent.md": STYLE_MD}, "Write nothing outside tool calls",
        "custom style reminder uses rule 1",
    ):
        fails.append("rule 1 extraction")

    if not check_reminder_for(
        "Quiet", {"quiet.md": STYLE_MD_NO_RULES},
        "A minimal style with no numbered rules",
        "falls back to frontmatter description with no rule list",
    ):
        fails.append("description fallback")

    if not check_reminder_for(
        "Terse", {"terse.md": STYLE_MD_WITH_COMMENT},
        "Keep every reply under two sentences.",
        "explicit reminder comment wins over description",
    ):
        fails.append("comment override")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        make_repo(tmp_path, "NoSuchStyle", {"silent.md": STYLE_MD})
        proc = run_hook_in(tmp_path)
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        if not _testlib.report(ok, "silent when named style has no matching file"):
            fails.append("unmatched style name")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        make_repo(tmp_path, None, {"silent.md": STYLE_MD}, settings_file="settings.local.json")
        (tmp_path / "settings.json").write_text(
            json.dumps({"outputStyle": "Silent"}), encoding="utf-8"
        )
        proc = run_hook_in(tmp_path)
        ok = proc.returncode == 0 and "Silent" in proc.stdout
        if not _testlib.report(ok, "falls back to settings.json when settings.local.json has no outputStyle"):
            fails.append("settings.json fallback")

    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
