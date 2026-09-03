"""UserPromptSubmit hook: reinforce the active CUSTOM output style every turn.

Built-in styles (default, Proactive, Concise, Explanatory, Learning) already
get a per-turn `turnReminder` from the harness itself. A custom style is only
ever injected once, at session start, and fades over a long session (todo
209's caveman-mode incident, todo 452). This hook restores that reinforcement
for a custom style by re-reading output-styles/<name>.md and re-emitting a
short line derived from it. Silent for default and every built-in. Fails
open: any read/parse error emits nothing rather than blocking the turn.
"""

import glob
import json
import os
import re
import sys

BUILTIN_STYLES = {"default", "proactive", "concise", "explanatory", "learning"}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NAME_RE = re.compile(r"^name:\s*\"?([^\"\n]+?)\"?\s*$", re.MULTILINE)
_DESC_RE = re.compile(r"^description:\s*\"?([^\"\n]+?)\"?\s*$", re.MULTILINE)
_COMMENT_RE = re.compile(r"<!--\s*reminder:\s*(.+?)\s*-->", re.DOTALL)
_RULE_ONE_RE = re.compile(r"^1\.\s+\*\*(.+?)\*\*", re.MULTILINE)


def read_output_style(repo_root: str):
    for name in ("settings.local.json", "settings.json"):
        path = os.path.join(repo_root, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        style = data.get("outputStyle")
        if style:
            return style
    return None


def find_style_file(repo_root: str, style_name: str):
    for path in glob.glob(os.path.join(repo_root, "output-styles", "*.md")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        m = _NAME_RE.search(content)
        if m and m.group(1).strip().lower() == style_name.strip().lower():
            return content
    return None


def extract_reminder(content: str, style_name: str) -> str:
    m = _COMMENT_RE.search(content)
    if m:
        return m.group(1).strip()
    m = _RULE_ONE_RE.search(content)
    if m:
        return m.group(1).strip()
    m = _DESC_RE.search(content)
    if m:
        return m.group(1).strip()
    return "%s output style is active." % style_name


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
    try:
        style = read_output_style(repo_root)
        if not style or style.strip().lower() in BUILTIN_STYLES:
            return 0
        content = find_style_file(repo_root, style)
        if content is None:
            return 0
        reminder = extract_reminder(content, style)
    except Exception:
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "[%s style reminder] %s" % (style, reminder),
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
