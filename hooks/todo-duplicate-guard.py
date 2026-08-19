"""PreToolUse hook (todo 363): advisory duplicate check when Claude Writes a
new file directly under `.claude/todos/` (backlog root, never `done/` or
`.claims/`).

`ai-todos-format.md`'s Content-duplicate guard has always been prose - every
writer (`/create-todo`, `/handoff`, `/close`, `/code-check`, autopilot) is
supposed to grep the destination backlog first, but nothing enforced it.
2026-08-17: a `/code-check` run in zng-app filed a todo covering the same
finding as an already-live one, caught only by luck.

Deliberately advisory, not a hard block like shortcut-create-guard.py: two
todos can legitimately share a word or two (see the GOTCHA this repo has hit
before with guess-based hooks), so a plausible hit blocks with the candidate
listed and an explicit override marker, never a silent or unresolvable stop.
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
    sys.stderr.write(f"[todo-duplicate-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_MARKER = "<!-- duplicate-checked -->"

PATH_SEP_RE = re.compile(r"[\\/]+")
FILENAME_RE = re.compile(r"^\d+-.*\.md$", re.IGNORECASE)
TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# Common enough in todo prose to carry no signal on their own; kept short on
# purpose, the 4+ char length filter below already does most of the work.
STOPWORDS = {
    "that", "this", "from", "have", "must", "never", "always", "also",
    "only", "when", "then", "than", "into", "onto", "over", "under",
    "about", "after", "before", "while", "where", "which", "their",
    "there", "these", "those", "being", "been", "were", "will", "would",
    "could", "should", "does", "did", "each", "every", "some", "such",
    "more", "most", "less", "least", "very", "just", "todo", "todos",
}


def todos_target_dir(file_path: str) -> Path | None:
    """The `.claude/todos` directory if `file_path` is a new backlog file
    written directly inside it (name matches `\\d+-*.md`), else None. A
    `done/` or `.claims/` child never matches, since it has an extra path
    segment between `todos` and the filename.
    """
    if not file_path:
        return None
    p = Path(file_path)
    if not FILENAME_RE.match(p.name):
        return None
    segments = [s.lower() for s in PATH_SEP_RE.split(str(p.parent)) if s]
    if len(segments) < 2 or segments[-2] != ".claude" or segments[-1] != "todos":
        return None
    return p.parent


def extract_title(content: str) -> str:
    m = TITLE_RE.search(content or "")
    return m.group(1).strip() if m else ""


def salient_tokens(title: str) -> list[str]:
    seen = set()
    out = []
    for raw in TOKEN_RE.findall(title or ""):
        low = raw.lower()
        if len(low) < 4 or low in STOPWORDS or low in seen:
            continue
        seen.add(low)
        out.append(low)
    return out


def matched_tokens(tokens: list[str], text: str) -> list[str]:
    return [t for t in tokens if re.search(r"\b" + re.escape(t) + r"\b", text, re.IGNORECASE)]


def is_plausible_hit(tokens: list[str], matched: list[str]) -> bool:
    """Requires real overlap, not a shared word or two: at least 3 salient
    tokens in common, or (for short titles) at least 2 covering >=60% of the
    new title's tokens.
    """
    if len(tokens) < 2 or len(matched) < 2:
        return False
    if len(matched) >= 3:
        return True
    return len(matched) / len(tokens) >= 0.6


def find_hits(todos_dir: Path, target_name: str, tokens: list[str]) -> list[tuple[Path, list[str]]]:
    candidates = [f for f in sorted(todos_dir.glob("*.md")) if f.name.lower() != target_name]
    done_dir = todos_dir / "done"
    if done_dir.is_dir():
        candidates += sorted(done_dir.glob("*.md"))

    hits = []
    for f in candidates:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        matched = matched_tokens(tokens, text)
        if is_plausible_hit(tokens, matched):
            hits.append((f, matched))
    return hits


def main() -> None:
    payload = read_payload()
    if (payload.get("tool_name") or "") != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    todos_dir = todos_target_dir(file_path)
    if todos_dir is None:
        sys.exit(0)

    content = tool_input.get("content") or ""
    if OVERRIDE_MARKER in content:
        sys.exit(0)

    tokens = salient_tokens(extract_title(content))
    if len(tokens) < 2:
        sys.exit(0)

    hits = find_hits(todos_dir, Path(file_path).name.lower(), tokens)
    if not hits:
        sys.exit(0)

    hit_lines = "; ".join(f"{f.name} (shares: {', '.join(m)})" for f, m in hits[:5])
    deny(
        f"[todo-duplicate-guard] Possible duplicate of existing todo(s): {hit_lines}. "
        "Per ai-todos-format.md's Content-duplicate guard, read the hit(s) in full and "
        "resolve to fold-in / drop-as-stale / drop-as-declined instead of filing this. "
        f"If it is genuinely distinct and only shares vocabulary, add {OVERRIDE_MARKER} "
        "anywhere in the new file's content to proceed."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[todo-duplicate-guard] hook error, failing open: {e}\n")
        sys.exit(0)
