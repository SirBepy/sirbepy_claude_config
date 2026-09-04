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

Todo 481: a third, non-blocking signal - a repo-allocation warning when the
todo's own body points mostly at paths outside the repo being written to.
`allow`-decision JSON, never `deny`: allocation needs judgment a text
heuristic cannot have, so a false positive here must never refuse the write.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, allow_with_warning
except Exception as e:
    sys.stderr.write(f"[todo-duplicate-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_MARKER = "<!-- duplicate-checked -->"
# Todo 834: matches the bare marker AND `<!-- duplicate-checked: reason -->`,
# since inlining the reason next to the marker is the natural move and the
# strict equality match gave no signal that FORM, not content, was rejected.
OVERRIDE_MARKER_RE = re.compile(r"<!--\s*duplicate-checked\b[^\n>]*-->")

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


RELATIVE_PARENT_RE = re.compile(r"\.\.[\\/]([A-Za-z0-9_.-]+)[\\/]")


def _whole_name_re(name: str) -> re.Pattern:
    """Word-boundary match that also treats `-` as part of the identifier, so
    a repo named "hubbub" does not match inside "hubbub-game-music-guesser".
    """
    return re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])")


def outside_repo_names(content: str, repo_root: Path) -> set[str]:
    """Other-repo names this todo's body points at: an explicit `../name/`
    path, or a bare mention of a sibling directory that is itself a git repo.
    """
    names = set(RELATIVE_PARENT_RE.findall(content or ""))
    try:
        for child in repo_root.parent.iterdir():
            if child.name == repo_root.name or not child.is_dir():
                continue
            if (child / ".git").exists() and _whole_name_re(child.name).search(content or ""):
                names.add(child.name)
    except OSError:
        pass
    return names


def allocation_warning(content: str, repo_root: Path) -> str | None:
    """Advisory text (todo 481) when `content`'s own paths point mostly
    outside `repo_root`: the incident this guards against is a mis-filed
    todo getting EXECUTED from the wrong session. Per ai-todos-format.md's
    allocation rule, not a reason to block on its own.
    """
    if not content or not repo_root.name:
        return None
    outside = outside_repo_names(content, repo_root)
    if not outside:
        return None
    here = len(_whole_name_re(repo_root.name).findall(content))
    if len(outside) <= here:
        return None
    return (
        f"[todo-duplicate-guard] This todo's own paths point mostly outside "
        f"{repo_root.name} ({', '.join(sorted(outside))}). Per ai-todos-format.md's "
        "allocation rule, a todo belongs in the backlog of the repo it changes - "
        "consider filing it there instead."
    )


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


def allow(warning: str | None) -> None:
    """Exit 0, optionally surfacing `warning` as a non-blocking `allow`
    decision via _hooklib's shared helper (todo 910).
    """
    if warning:
        allow_with_warning(warning)
    sys.exit(0)


def main() -> None:
    payload = read_payload()
    if (payload.get("tool_name") or "") != "Write":
        sys.exit(0)

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    todos_dir = todos_target_dir(file_path)
    if todos_dir is None:
        sys.exit(0)

    repo_root = todos_dir.parent.parent
    content = tool_input.get("content") or ""
    warning = allocation_warning(content, repo_root)

    target_name = Path(file_path).name
    target_id = extract_id(target_name)
    if target_id is not None:
        collision = find_id_collision(todos_dir, target_name.lower(), target_id)
        if collision is not None:
            deny(
                f"[todo-duplicate-guard] Id {target_id} is already claimed by "
                f"{collision.name}. Ids must be unique across .claude/todos/, done/, "
                f"and *-.reserved markers - run `skills/close/reserve-todo-id.ps1 "
                f"-RepoRoot {repo_root}` to reserve a free one instead of picking by hand."
            )

    if OVERRIDE_MARKER_RE.search(content):
        allow(warning)

    tokens = salient_tokens(extract_title(content))
    if len(tokens) < 2:
        allow(warning)

    hits = find_hits(todos_dir, target_name.lower(), tokens)
    if not hits:
        allow(warning)

    hit_lines = "; ".join(f"{f.name} (shares: {', '.join(m)})" for f, m in hits[:5])
    deny(
        f"[todo-duplicate-guard] Possible duplicate of existing todo(s): {hit_lines}. "
        "Per ai-todos-format.md's Content-duplicate guard, read the hit(s) in full and "
        "resolve to fold-in / drop-as-stale / drop-as-declined instead of filing this. "
        f"If it is genuinely distinct and only shares vocabulary, add {OVERRIDE_MARKER} "
        "anywhere in the new file's content to proceed - a reason can go inside the same "
        "comment, e.g. `<!-- duplicate-checked: the two hits are different surfaces -->`."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[todo-duplicate-guard] hook error, failing open: {e}\n")
        sys.exit(0)
