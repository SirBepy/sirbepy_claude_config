"""PreToolUse hook (todo 886): block a Croatian-language AskUserQuestion
card before Joe sees it. "Reply to Joe in English only" was already stated
in CLAUDE.md and in zng-app auto-memory; both failed to stop the same
mistake twice, so this replaces the third restatement with a mechanical
gate on the question tools themselves.

Covers the built-in `AskUserQuestion` tool and any `ask_user_question` MCP
tool (matched by suffix after the last "__", same convention as
em-dash-guard.py's CHAT_TOOL_TEXT_FIELDS, kept independent here rather than
importing that module since the two guards scan for unrelated patterns).

Detection is diacritics-or-stopwords, not a language model: Croatian-only
diacritics anywhere trip it on one hit, since those characters have no
legitimate use in an English question card. Diacritic-free Croatian (how
Joe himself usually types) needs 2+ stopword hits across the payload, since
a single short token like "bi" is not enough signal on its own.

Escape: ESCAPE_MARKER anywhere in the payload skips the whole check, for
quoting Joe's own Croatian back to him or reviewing a Croatian string that
is the subject of the question - same shape as todo-duplicate-guard.py's
OVERRIDE_MARKER.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[croatian-question-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

ESCAPE_MARKER = "<!-- hr-quote -->"

DIACRITIC_RE = re.compile("[čćžšđČĆŽŠĐ]")

STOPWORDS = ["jel", "nije", "samo", "ovo", "treba", "kad", "sto", "ako", "bi"]
STOPWORD_RE = re.compile(r"\b(?:" + "|".join(STOPWORDS) + r")\b", re.IGNORECASE)
MIN_STOPWORD_HITS = 2

FIELD_PATHS = [
    "questions[].question",
    "questions[].header",
    "questions[].options[].label",
    "questions[].options[].description",
]

_PATH_TOKEN_RE = re.compile(r"\[\]|[^.\[\]]+")


def extract_field(tool_input: dict, path: str):
    """Walk one field-path spec against a tool's input dict, returning every
    string leaf value it resolves to (0, 1, or many for a "[]" segment)."""
    values = [tool_input]
    for tok in _PATH_TOKEN_RE.findall(path):
        next_values = []
        if tok == "[]":
            for v in values:
                if isinstance(v, list):
                    next_values.extend(v)
        else:
            for v in values:
                if isinstance(v, dict) and tok in v:
                    next_values.append(v[tok])
        values = next_values
    return [v for v in values if isinstance(v, str)]


def matches_tool(name: str) -> bool:
    suffix = name.rsplit("__", 1)[-1] if "__" in name else name
    return suffix in ("AskUserQuestion", "ask_user_question")


def collect_texts(tool_input: dict):
    """Yield (field_path, text) for every question/header/option string."""
    for field_path in FIELD_PATHS:
        for value in extract_field(tool_input, field_path):
            yield field_path, value


def scan(tool_input: dict):
    """Returns a list of (field_path, text, matched_tokens) for fields that
    look Croatian: any diacritic hit blocks alone, stopwords need
    MIN_STOPWORD_HITS total across the whole payload."""
    fields = list(collect_texts(tool_input))
    total_stopword_hits = sum(len(STOPWORD_RE.findall(text)) for _, text in fields)
    stopwords_trip = total_stopword_hits >= MIN_STOPWORD_HITS

    offenders = []
    for field_path, text in fields:
        diacritics = DIACRITIC_RE.findall(text)
        stopwords = STOPWORD_RE.findall(text) if stopwords_trip else []
        if diacritics or stopwords:
            offenders.append((field_path, text, diacritics + stopwords))
    return offenders


def build_reason(offenders) -> str:
    lines = []
    for field_path, text, tokens in offenders:
        snippet = text if len(text) <= 80 else text[:77] + "..."
        lines.append(f'{field_path}: "{snippet}" (matched: {", ".join(tokens)})')
    return (
        "Croatian text found in this question card, blocked before Joe sees it:\n"
        + "\n".join(lines)
        + "\nGlobal rule: reply to Joe in English only, question cards included. "
        f"Quoting his own Croatian back to him or reviewing a Croatian string is fine, "
        f"add {ESCAPE_MARKER} anywhere in the payload to bypass."
    )


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if not matches_tool(tool_name):
        sys.exit(0)
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
        sys.stderr.write(f"[croatian-question-guard] hook error, failing open: {e}\n")
        sys.exit(0)
