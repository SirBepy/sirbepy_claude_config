"""PreToolUse hook: block a show_preview call whose `html` param is
HTML-entity-escaped instead of raw markup (todo: 2026-09-28 incident - a
manually escaped `<`/`>` document rendered as literal source text in Joe's
preview panel instead of the design).

A valid `show_preview` `html` value is a complete, self-contained HTML
document, so it must start with a literal `<` (after whitespace/BOM). If it
instead starts with `&lt;`, or is dense with `&lt;`/`&gt;` entities relative
to real tag characters, the caller almost certainly ran the whole document
through an HTML-escaper (or hand-typed entities) before handing it to the
tool. Block and tell the model to pass raw markup and retry, so Joe never
sees the broken card in the first place.

Pure structural check on the string - no HTML parsing, no DOM diffing. Fails
open on any hook error so a bug here can never block a legitimate preview.
"""

import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[preview-html-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

TOOL_SUFFIX = "show_preview"
MIN_ENTITY_COUNT = 5


def looks_double_escaped(html: str) -> str | None:
    """Returns a reason string if `html` looks HTML-entity-escaped instead
    of raw markup, else None."""
    stripped = html.lstrip("﻿ \t\r\n")
    if not stripped:
        return None

    if stripped.lower().startswith("&lt;"):
        return "the document starts with the literal text \"&lt;\" instead of \"<\" - the whole document was HTML-entity-escaped before being passed as `html`"

    lt_entities = stripped.count("&lt;")
    gt_entities = stripped.count("&gt;")
    literal_lt = stripped.count("<")
    literal_gt = stripped.count(">")
    if lt_entities >= MIN_ENTITY_COUNT and lt_entities > literal_lt and gt_entities > literal_gt:
        return (
            f"found {lt_entities} \"&lt;\" and {gt_entities} \"&gt;\" entities but only "
            f"{literal_lt} literal \"<\" and {literal_gt} literal \">\" characters - the "
            "document body looks HTML-entity-escaped rather than raw markup"
        )
    return None


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    if not tool_name.endswith(TOOL_SUFFIX):
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    html = tool_input.get("html", "") or ""
    if not html:
        sys.exit(0)

    reason = looks_double_escaped(html)
    if reason is None:
        sys.exit(0)

    deny(
        "[preview-html-guard] show_preview's `html` looks HTML-entity-escaped, not raw markup: "
        + reason
        + ". Pass the literal, unescaped HTML document (real `<`/`>` characters) as `html` - "
        "never run the document through an HTML escaper first - then retry."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[preview-html-guard] hook error, failing open: {e}\n")
        sys.exit(0)
