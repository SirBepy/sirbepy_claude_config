"""PreToolUse hook (todo 1207): block an ask_user_question card whose option
`preview` is a hand-styled imitation of the app instead of the app's real
render markup.

The rule ("a preview is built from the app's own classes, never a
`<div style="background:var(--color-surface)...">` look-alike") lived in a
project memory and was read but not applied three times (2026-10-18, and
twice on 2026-10-20): under time pressure with 3-4 previews to write, prose
memory lost every time. This gate runs on the tool call itself.

What counts as a hand-styled imitation: an inline `style` attribute that
paints (background, border, color, font, shadow, radius, gradient). Layout-
only inline styles (width, margin, display) pass, and so does any preview
built from `class=` markup, so a real-markup preview is never slowed down.
A preview that is plain text or has no style attribute is untouched.

Escape: ESCAPE_MARKER anywhere in the payload skips the check, for the rare
case where the question is about a styled thing itself. Omitting `preview`
and using plain option text is always allowed and is what the deny message
recommends when there is no time to use the real markup.

Fails open on any internal error: this runs on every question card in every
session.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[question-preview-style-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

ESCAPE_MARKER = "<!-- hand-styled-ok -->"

STYLE_ATTR_RE = re.compile(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
# `border-collapse` and `border-spacing` lay a table out and paint nothing, so the `border*`
# family skips them; `fill`/`stroke` paint inline SVG.
PAINT_PROP_RE = re.compile(
    r"(?:^|[;\s])(?:background|border(?!-collapse\b|-spacing\b)|box-shadow|color|font|text-shadow|outline|"
    r"filter|opacity|fill|stroke)[a-z-]*\s*:|radius|gradient|var\(\s*--color",
    re.IGNORECASE,
)


def matches_tool(name: str) -> bool:
    suffix = name.rsplit("__", 1)[-1] if "__" in name else name
    return suffix in ("AskUserQuestion", "ask_user_question")


def iter_previews(node):
    """Yield every string stored under a key named `preview`, at any depth."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "preview" and isinstance(value, str):
                yield value
            else:
                yield from iter_previews(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_previews(item)


def painted_styles(preview: str) -> list[str]:
    """The inline style attribute values in one preview that paint."""
    hits = []
    for double, single in STYLE_ATTR_RE.findall(preview):
        value = double or single
        if PAINT_PROP_RE.search(value):
            hits.append(value)
    return hits


def scan(tool_input: dict) -> list[str]:
    offenders = []
    for preview in iter_previews(tool_input):
        offenders.extend(painted_styles(preview))
    return offenders


def build_reason(offenders: list[str]) -> str:
    shown = []
    for value in offenders[:3]:
        snippet = value if len(value) <= 70 else value[:67] + "..."
        shown.append(f'style="{snippet}"')
    return (
        "This question card has a preview drawn with hand-styled inline CSS "
        "(an imitation of the app, not its real markup), blocked before Joe sees it:\n"
        + "\n".join(shown)
        + "\nBuild each preview from the app's real classes (read the component's "
        "markup and reuse its class names, no painting style attributes). "
        "If there is no time for that, omit `preview` and use plain option text "
        f"instead of posting another fake one. Escape for a genuine exception: {ESCAPE_MARKER}"
    )


def main() -> None:
    payload = read_payload()
    if not matches_tool(payload.get("tool_name") or ""):
        sys.exit(0)
    tool_input = payload.get("tool_input") or {}
    if ESCAPE_MARKER in json.dumps(tool_input):
        sys.exit(0)
    offenders = scan(tool_input)
    if offenders:
        deny(build_reason(offenders))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[question-preview-style-guard] hook error, failing open: {e}\n")
        sys.exit(0)
