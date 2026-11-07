"""Self-test for question-preview-style-guard.py (todo 1207).

Run directly: python hooks/test_question_preview_style_guard.py
Exits 0 on all-pass, 1 on any failure.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "question-preview-style-guard.py"
guard = _testlib.load_module("question_preview_style_guard", _GUARD_PATH)


def card(preview):
    return {"questions": [{"question": "Which layout?", "header": "Layout", "options": [
        {"label": "A", "description": "first", "preview": preview},
        {"label": "B", "description": "second"},
    ]}]}


# The 2026-10-20 incident shape: hand-drawn fragments painted with app variables.
FAKE = '<div style="background: var(--color-surface); border: 1px solid #333; padding: 8px">Wrap up</div>'
FAKE_SINGLE_QUOTES = "<div style='background:#111;border-radius:6px'>x</div>"
REAL = '<div class="chat-row"><span class="chat-row__title">Wrap up</span></div>'
LAYOUT_ONLY = '<div class="chat-row" style="width: 240px; margin-top: 4px">x</div>'
PLAIN = "Option A keeps the toggle in the header."

# (tool_input, expect_block, label)
SCAN_CASES = [
    (card(FAKE), True, "painted inline style blocks"),
    (card(FAKE_SINGLE_QUOTES), True, "single-quoted painted style blocks"),
    (card(REAL), False, "real class markup passes"),
    (card(LAYOUT_ONLY), False, "layout-only inline style passes"),
    (card(PLAIN), False, "plain-text preview passes"),
    ({"questions": [{"question": "Q?", "header": "Q", "options": [{"label": "a", "description": "b"}]}]}, False, "no preview at all passes"),
    (card('<div STYLE="COLOR:red">x</div>'), True, "case-insensitive attribute and property"),
    ({"questions": "not-a-list"}, False, "malformed input does not crash or block"),
    # pc-review item 13: border-collapse and border-spacing lay a table out, they paint nothing.
    (card('<table style="border-collapse:collapse;width:100%"><tr><td>x</td></tr></table>'), False, "border-collapse is layout"),
    (card('<table style="width: 100%; border-collapse: collapse">x</table>'), False, "border-collapse after another property"),
    (card('<table style="BORDER-COLLAPSE:COLLAPSE;border-spacing:0">x</table>'), False, "border-collapse and border-spacing, any case"),
    (card('<table style="border-collapse:collapse;border:1px solid #333">x</table>'), True, "border-collapse beside a painting border still blocks"),
    (card('<td style="border-collapse:collapse;border-top:1px solid red">x</td>'), True, "border-collapse beside border-top still blocks"),
    (card('<td style="border-radius:4px">x</td>'), True, "border-radius still blocks"),
    (card('<td style="border-color:red">x</td>'), True, "border-color still blocks"),
    (card('<td style="border-spacing:0;background:red">x</td>'), True, "border-spacing beside a background still blocks"),
    # SVG paint properties are painting too.
    (card('<svg style="fill:#fff"><path d="M0 0"/></svg>'), True, "fill paints"),
    (card('<svg style="width:12px;stroke:red"><path d="M0 0"/></svg>'), True, "stroke paints"),
    (card('<div style="flex:1 1 auto;width:50%">x</div>'), False, "flex shorthand is layout"),
]


def check_scan(case) -> bool:
    tool_input, expect_block, label = case
    got = bool(guard.scan(tool_input))
    ok = got == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] scan: {label} -> {'BLOCK' if got else 'PASS'}")
    return ok


# (tool_name, tool_input, expect_deny, label) - full-process, exit 2 = deny.
PRE_TOOL_USE_CASES = [
    ("mcp__cc_conductor__ask_user_question", card(FAKE), True, "MCP tool with fake preview denied"),
    ("AskUserQuestion", card(FAKE), True, "built-in tool with fake preview denied"),
    ("mcp__cc_conductor__ask_user_question", card(REAL), False, "real-markup preview not denied"),
    ("mcp__cc_conductor__send_message", {"text": FAKE}, False, "other tools never scanned"),
    ("mcp__cc_conductor__ask_user_question", card(FAKE + guard.ESCAPE_MARKER), False, "escape marker bypasses"),
]


def check_pre_tool_use(case) -> bool:
    tool_name, tool_input, expect_deny, label = case
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run([sys.executable, str(_GUARD_PATH)], input=json.dumps(payload), capture_output=True, text=True)
    ok = (proc.returncode == 2) == expect_deny
    print(f"[{'PASS' if ok else 'FAIL'}] pretooluse: {label} -> exit={proc.returncode}")
    return ok


def check_garbage_stdin(_case) -> bool:
    proc = subprocess.run([sys.executable, str(_GUARD_PATH)], input="not json", capture_output=True, text=True)
    ok = proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] fails open on garbage stdin -> exit={proc.returncode}")
    return ok


def run() -> int:
    fails = (
        _testlib.run_cases(SCAN_CASES, check_scan)
        + _testlib.run_cases(PRE_TOOL_USE_CASES, check_pre_tool_use)
        + _testlib.run_cases([("garbage",)], check_garbage_stdin)
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
