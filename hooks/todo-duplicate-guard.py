"""PreToolUse hook (todo 363, 492): advisory duplicate check when Claude
Writes a new file directly under `.claude/todos/` (backlog root, never
`done/` or `.claims/`).

`ai-todos-format.md`'s Content-duplicate guard has always been prose - every
writer (`/create-todo`, `/handoff`, `/close`, `/code-check`, autopilot) is
supposed to grep the destination backlog first, but nothing enforced it.
2026-08-17: a `/code-check` run in zng-app filed a todo covering the same
finding as an already-live one, caught only by luck.

Deliberately advisory, not a hard block like shortcut-create-guard.py: two
todos can legitimately share a word or two (see the GOTCHA this repo has hit
before with guess-based hooks), so a plausible hit blocks with the candidate
listed and an explicit override marker, never a silent or unresolvable stop.

Id uniqueness (todo 492) is a separate, unconditional check: two files ever
sharing a numeric prefix breaks every `-Id`-addressed tool downstream, so it
is a hard block with no override marker, unlike the content heuristic above.

Todo 851: the check does not delete a matched `*-.reserved` marker on a
passing write. A PreToolUse hook deleting files is a surprising side effect;
step 3 of the reserve-then-write contract stays the caller's job.
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

# A token in more than this share of the backlog's titles+goals carries no signal.
COMMON_TOKEN_RATIO = 0.25
COMMON_TOKEN_MIN_DOCS = 3
COMMON_TOKEN_MIN_CORPUS = 8

PATH_SEP_RE = re.compile(r"[\\/]+")
FILENAME_RE = re.compile(r"^\d+-.*\.md$", re.IGNORECASE)
ID_RE = re.compile(r"^0*(\d+)-")
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


def comparable_text(content: str) -> str:
    """Title plus Goal, never the whole body: matching full text made every long
    todo a hit on shared vocabulary (5 false positives on 2 real writes, 2026-08-19).
    """
    title = extract_title(content)
    goal = ""
    m = re.search(r"(?ms)^##[ \t]+Goal[ \t]*\r?\n(.*?)(?=^##[ \t]|\Z)", content or "")
    if not m:
        m = re.search(r"(?mi)^[ \t]*Goal[ \t]*:[ \t]*(.+)$", content or "")
    if m:
        goal = m.group(1)
    return f"{title}\n{goal}"


def find_hits(todos_dir: Path, target_name: str, tokens: list[str]) -> list[tuple[Path, list[str]]]:
    # Only real backlog files compare: PLAN.md is the ordered lane, not a todo,
    # and it names nearly every id in the backlog, so it matched everything.
    candidates = [
        f for f in sorted(todos_dir.glob("*.md"))
        if f.name.lower() != target_name and FILENAME_RE.match(f.name)
    ]
    done_dir = todos_dir / "done"
    if done_dir.is_dir():
        candidates += [f for f in sorted(done_dir.glob("*.md")) if FILENAME_RE.match(f.name)]

    texts = []
    for f in candidates:
        try:
            texts.append((f, comparable_text(f.read_text(encoding="utf-8", errors="ignore"))))
        except OSError:
            continue

    # Domain terms ("skill", "dispatch", "marker") killed signal here and no English
    # stopword list catches those; document frequency finds them per-repo. Needs a
    # real corpus: under ~8 candidates the ratio drops below a single document.
    if len(texts) >= COMMON_TOKEN_MIN_CORPUS:
        floor = max(COMMON_TOKEN_MIN_DOCS, len(texts) * COMMON_TOKEN_RATIO)
        common = {
            t for t in tokens
            if sum(1 for _, txt in texts if matched_tokens([t], txt)) > floor
        }
        tokens = [t for t in tokens if t not in common] or tokens

    hits = []
    for f, txt in texts:
        matched = matched_tokens(tokens, txt)
        if is_plausible_hit(tokens, matched):
            hits.append((f, matched))
    return hits


def extract_id(name: str) -> int | None:
    """Numeric prefix of a backlog filename or `<id>-.reserved` marker, with
    leading zeros normalized (so "007-x.md" and "7-y.md" are the same id).
    """
    m = ID_RE.match(name)
    return int(m.group(1)) if m else None


def find_id_collision(todos_dir: Path, target_name: str, target_id: int) -> Path | None:
    """Path of a differently-named file or reservation marker that already
    claims `target_id`, else None. A same-name match in `todos_dir` itself is
    an in-place rewrite, not a collision - same precedent as `find_hits`. A
    `<target_id>-.reserved` marker in `todos_dir` is the caller's own
    reservation, not a collision either: `reserve-todo-id.ps1`'s atomic
    no-overwrite rename guarantees at most one marker per id ever exists, so
    a marker sharing `target_id` can only be the write this same id was
    reserved for.
    """
    candidates = [f for f in sorted(todos_dir.glob("*.md")) if FILENAME_RE.match(f.name)]
    done_dir = todos_dir / "done"
    if done_dir.is_dir():
        candidates += [f for f in sorted(done_dir.glob("*.md")) if FILENAME_RE.match(f.name)]
    candidates += sorted(todos_dir.glob("*-.reserved"))

    for f in candidates:
        if f.parent == todos_dir and f.name.lower() == target_name:
            continue
        if f.parent == todos_dir and f.name.lower().endswith("-.reserved") and extract_id(f.name) == target_id:
            continue
        if extract_id(f.name) == target_id:
            return f
    return None


def main() -> None:
    payload = read_payload()
    if (payload.get("tool_name") or "") != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    todos_dir = todos_target_dir(file_path)
    if todos_dir is None:
        sys.exit(0)

    target_name = Path(file_path).name
    target_id = extract_id(target_name)
    if target_id is not None:
        collision = find_id_collision(todos_dir, target_name.lower(), target_id)
        if collision is not None:
            repo_root = todos_dir.parent.parent
            deny(
                f"[todo-duplicate-guard] Id {target_id} is already claimed by "
                f"{collision.name}. Ids must be unique across .claude/todos/, done/, "
                f"and *-.reserved markers - run `skills/close/reserve-todo-id.ps1 "
                f"-RepoRoot {repo_root}` to reserve a free one instead of picking by hand."
            )

    content = tool_input.get("content") or ""
    if OVERRIDE_MARKER in content:
        sys.exit(0)

    tokens = salient_tokens(extract_title(content))
    if len(tokens) < 2:
        sys.exit(0)

    hits = find_hits(todos_dir, target_name.lower(), tokens)
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
