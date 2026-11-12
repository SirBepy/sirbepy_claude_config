"""Fails when a git-tracked skills/**/*.md still names a removed command.

`/commit pushbump` and `/commit pushnbump` no longer exist (a version bump is
`/release`), and neither does the `/close` skill (a finished chat ends with the
save step in refs/save-step.md, then `close_session`). A stale mention in a skill
sends a future session down a path that silently fails or falls back, so any new
mention is a CI failure. A `> Removed: ...` tombstone line is the one place the
names legitimately appear. Only skills/**/*.md is scanned: CLAUDE.md, refs/ and
hooks/ keep a few dated history sentences that name `/close`.
"""

import argparse
import re
import sys
from pathlib import Path

from _cilib import tracked_files

REMOVED_NAME = re.compile(
    r"\bpushn?bump\b"
    # A standalone `/close` token: a path such as skills/close/ and `/close_session` do not match.
    r"|(?<![\w/.])/close(?![\w-])"
)
TOMBSTONE_PREFIX = "> Removed: "
FRONTMATTER_EXEMPT_FILE = "skills/commit/SKILL.md"
FRONTMATTER_EXEMPT_KEYS = ("description:", "argument-hint:")


def candidate_paths(root: Path) -> list:
    """Repo-relative posix paths of the skills/**/*.md files to scan: git-tracked
    only (an untracked peer file is not yet part of the committed contract),
    every .md under skills/ when git cannot be queried.
    """
    tracked = tracked_files(root, "skills")
    if tracked is None:
        found = (p.relative_to(root).as_posix() for p in (root / "skills").rglob("*.md"))
        return sorted(found)
    return sorted(p for p in tracked if p.endswith(".md"))


def is_exempt(rel: str, line: str) -> bool:
    if line.startswith(TOMBSTONE_PREFIX):
        return True
    return rel == FRONTMATTER_EXEMPT_FILE and line.startswith(FRONTMATTER_EXEMPT_KEYS)


def find_hits(root: Path, paths: list) -> list:
    """Returns `file:line: text` for every non-exempt mention in `paths`."""
    hits = []
    for rel in paths:
        if ".claude/todos" in rel:
            continue
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if REMOVED_NAME.search(line) and not is_exempt(rel, line):
                hits.append(f"{rel}:{lineno}: {line.strip()[:120]}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    root = args.root.resolve()

    paths = candidate_paths(root)
    hits = find_hits(root, paths)
    for hit in hits:
        print(hit)
    if hits:
        print(
            f"FAIL: {len(hits)} mention(s) of a removed command: pushbump/pushnbump (use /release), "
            "/close (use the save step in refs/save-step.md, then close_session)"
        )
        return 1
    print(f"OK: {len(paths)} skill markdown files checked, no removed command names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
