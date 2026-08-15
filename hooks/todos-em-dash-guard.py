"""PreToolUse hook (todo 318): block an em dash (U+2014) from entering a
file under .claude/todos/ at Write/Edit/MultiEdit time, so a todo authored
in another session never reaches /commit still carrying the character.

Same exact-codepoint property as em-dash-guard.py: no heuristic, no
false-positive surface. Path scope is a segment check (".claude" directly
followed by "todos"), never a substring match, so a sibling folder like
"myclaude/todos-backup" can't collide.

Exemption: a todo whose SUBJECT is the em dash (307-em-dash-stop-hook.md
quotes the character as an example, already shipped) is real and must
stay writable. Per this repo's hook doctrine, invert the problem instead
of guessing intent: allow only if EXEMPT_MARKER is present in the new
content or already on disk.

BLOCKS (not auto-fix): the writing session is the one that can act on the
message immediately, same shape as em-dash-guard.py's Stop block. Silently
rewriting the character would also risk mangling the one legitimate case
this file quotes.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[todos-em-dash-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

EM_DASH = chr(0x2014)
EXEMPT_MARKER = "<!-- em-dash-exempt -->"

PATH_SEP_RE = re.compile(r"[\\/]+")


def is_todos_path(file_path: str) -> bool:
    segments = [s.lower() for s in PATH_SEP_RE.split(file_path or "") if s]
    return any(
        segments[i] == ".claude" and segments[i + 1] == "todos"
        for i in range(len(segments) - 1)
    )


def new_content_strings(tool_name: str, tool_input: dict) -> list:
    if tool_name == "Write":
        return [tool_input.get("content") or ""]
    if tool_name == "Edit":
        return [tool_input.get("new_string") or ""]
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return [(e.get("new_string") or "") for e in edits if isinstance(e, dict)]
    return []


def find_em_dash(text: str) -> int:
    return text.find(EM_DASH) if text else -1


def build_reason(file_path: str, text: str, idx: int) -> str:
    start = max(0, idx - 20)
    end = min(len(text), idx + 21)
    snippet = text[start:end].replace("\n", " ")
    return (
        f"Em dash (U+2014) found writing {file_path} near: \"...{snippet}...\". "
        "Global rule bans it outright, rewrite using a comma, colon, or hyphen. "
        "If the em dash is genuinely the subject (e.g. a todo about this hook "
        f"quoting the character), add {EXEMPT_MARKER} anywhere in the file."
    )


def existing_file_text(file_path: str) -> str:
    try:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    if not file_path or not is_todos_path(file_path):
        sys.exit(0)

    contents = new_content_strings(tool_name, tool_input)
    combined = "\n".join(contents)
    idx = find_em_dash(combined)
    if idx == -1:
        sys.exit(0)

    if EXEMPT_MARKER in combined or EXEMPT_MARKER in existing_file_text(file_path):
        sys.exit(0)

    deny("[todos-em-dash-guard] " + build_reason(file_path, combined, idx))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[todos-em-dash-guard] hook error, failing open: {e}\n")
        sys.exit(0)
