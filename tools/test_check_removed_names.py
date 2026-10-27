"""Self-test for ci/check_removed_names.py.

Run directly: python tools/test_check_removed_names.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Calls find_hits() on a throwaway tree instead of the real repo, so it passes
before the check's own files are committed and never depends on git state.
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ci"))

import check_removed_names as crn  # noqa: E402

# Built by concatenation so this file never carries the removed names as a bare word.
OLD = "push" + "bump"
OLDER = "push" + "nbump"

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    write(root, "skills/a/SKILL.md", f"intro\nrun /commit {OLD} now\nand {OLDER} too\n")
    hits = crn.find_hits(root, ["skills/a/SKILL.md"])
    check(len(hits) == 2, "both removed names are reported")
    check(hits and hits[0].startswith("skills/a/SKILL.md:2:"), "hit carries file:line")

    write(root, "skills/b/SKILL.md", f"> Removed: `/commit {OLD}` and `/commit {OLDER}`.\n")
    check(crn.find_hits(root, ["skills/b/SKILL.md"]) == [], "a '> Removed: ' tombstone line is exempt")

    write(root, "skills/commit/SKILL.md", f"---\ndescription: x {OLD}\nargument-hint: \"[{OLDER}]\"\n---\nbody {OLD}\n")
    hits = crn.find_hits(root, ["skills/commit/SKILL.md"])
    check(len(hits) == 1 and ":5:" in hits[0], "commit frontmatter description/argument-hint lines are exempt, body is not")

    write(root, "skills/c/SKILL.md", f"description: x {OLD}\n")
    check(len(crn.find_hits(root, ["skills/c/SKILL.md"])) == 1, "the frontmatter exemption is limited to skills/commit/SKILL.md")

    write(root, "skills/d/SKILL.md", "mentions pushbumpers and bumppush only\n")
    check(crn.find_hits(root, ["skills/d/SKILL.md"]) == [], "word boundary: longer words do not match")

    write(root, "skills/x/.claude/todos/1-old.md", f"{OLD}\n")
    check(crn.find_hits(root, ["skills/x/.claude/todos/1-old.md"]) == [], "todo history is skipped")
    check(crn.find_hits(root, ["skills/missing.md"]) == [], "a missing path is skipped")

if failures:
    print(f"FAIL: {len(failures)} case(s) failed")
    sys.exit(1)
print("OK: all cases passed")
