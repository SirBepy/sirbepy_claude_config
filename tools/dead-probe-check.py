"""Warns when a diff removes a UI selector literal that a browser probe still references.

Filed against todo 968: a component deletion left `verify/take-sharing-probe.cjs` pointed at
`button[title^="Projects:"]`, a title that no longer existed anywhere. Five commits shipped
"verified" before the dev ran `/e2e` by hand and it surfaced. `/test` cannot catch this - a
Playwright selector string is not a symbol reference, so `tsc` has nothing to flag - and `/e2e`
is deliberately opt-in per CLAUDE.md's testing floor, so nothing in the normal flow re-checks a
probe after the surface it drives changes. This script is the cheap, browser-less, mechanical
substitute: advisory only, never blocking (a probe legitimately naming a deleted file in a
comment or migration note must not stop anything).

Rule, measured against countoff's real history (143 commits, 3 UI-file deletions, the one actual
incident) before being written this way - see todo 968's resolution notes for the full method:

- Scan a diff's REMOVED lines (not just deleted files - the incident's own dead literal lived in
  a trigger button in a DIFFERENT file than the deleted component) across common UI source
  extensions, skipping files already under a test/probe directory.
- `title=`/`aria-label=` literals only count if they contain a colon, matched by the text UP TO
  AND INCLUDING that colon (this codebase's own convention: `title="Projects: switch, ..."`
  paired with a Playwright `title^="Projects:"` prefix selector). A bare first-word or
  no-colon-required version of this rule was measured on the same corpus first and produced 9
  false positives to 1 true positive (Zoom/Share/Song/Edit/One/Add/Delete/Bring - ordinary
  English words that happen to recur in unrelated probe code); requiring the colon dropped that
  to 0 false positives on the same 143 commits, catching the one real incident exactly.
- `id=`/`data-testid=`/`name=` literals count on an exact full match, no colon needed - these
  attributes are conventionally unique tokens, not prefix-truncated in selectors. Zero full-text
  matches occurred anywhere in the corpus (noise or signal), so this arm ships on "provably
  silent so far", not a proven catch - documented as such, not oversold.
- A literal that still appears verbatim in the diff's ADDED lines was not actually removed
  (renamed in place, reordered) and is skipped.

Usage:
    python dead-probe-check.py --root <repo_root> [--against <git-diff-arg>]

`--against` is passed straight to `git diff <arg>` (e.g. `HEAD`, `@{u}..HEAD`, `abc123..HEAD`).
Defaults to `HEAD` (working tree: staged + unstaged). Exit code is always 0 - this never blocks;
findings go to stdout for a human or a skill step to read and act on.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

UI_EXTENSIONS = {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".html"}

PROBE_DIR_NAMES = {
    "verify", "e2e", "tests", "test", "__tests__", "cypress", "playwright", "spec", "specs",
}

# Colon-required arm: free-text attributes, matched by prefix up to the colon.
PREFIX_ATTR_RE = re.compile(r'(?:title|aria-label)=["\']([^"\']{3,80}):([^"\']*)["\']')
# Exact-match arm: identifier-shaped attributes, matched whole.
EXACT_ATTR_RE = re.compile(r'(?:id|data-testid|name)=["\']([^"\']{2,80})["\']')

MIN_PREFIX_LEN = 3  # guards against a colon at position 0-2 producing a near-empty search key


def sh(args, root: Path) -> str:
    try:
        result = subprocess.run(
            args, cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout


def is_probe_path(posix_path: str) -> bool:
    parts = posix_path.split("/")
    return any(p in PROBE_DIR_NAMES for p in parts[:-1])


def parse_diff_files(diff_text: str):
    """Yields (file_path, removed_lines, added_lines) per file in a unified diff."""
    file_path = None
    removed, added = [], []
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if file_path is not None:
                yield file_path, removed, added
            file_path = None
            removed, added = [], []
        elif line.startswith("+++ b/"):
            file_path = line[6:]
        elif line.startswith("+++ /dev/null") or line.startswith("--- "):
            pass
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    if file_path is not None:
        yield file_path, removed, added


def extract_candidates(removed_lines, added_text):
    """Returns a list of (raw_literal, search_key) pairs worth checking."""
    out = []
    for line in removed_lines:
        for m in PREFIX_ATTR_RE.finditer(line):
            before, _after = m.group(1), m.group(2)
            raw = f"{before}:{_after}"
            if raw in added_text:
                continue
            key = before.strip() + ":"
            if len(key) < MIN_PREFIX_LEN:
                continue
            out.append((raw, key))
        for m in EXACT_ATTR_RE.finditer(line):
            raw = m.group(1)
            if raw in added_text:
                continue
            out.append((raw, raw))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--against", default="HEAD")
    args = parser.parse_args()
    root = Path(args.root).resolve()

    diff_text = sh(["git", "diff", args.against, "--", "."], root)
    if not diff_text.strip():
        print("dead-probe-check: no diff to scan, nothing to report")
        return 0

    findings = []
    for file_path, removed, added in parse_diff_files(diff_text):
        if not file_path or is_probe_path(file_path):
            continue
        if Path(file_path).suffix not in UI_EXTENSIONS:
            continue
        added_text = "\n".join(added)
        for raw, key in extract_candidates(removed, added_text):
            hit = sh(["git", "grep", "-l", "-F", key, "--", ":(exclude)*.md"], root)
            hit_lines = [
                p for p in hit.strip().splitlines()
                if is_probe_path(p.replace("\\", "/"))
            ]
            if hit_lines:
                findings.append((file_path, raw, key, hit_lines))

    if not findings:
        print("dead-probe-check: no orphaned selector literals found")
        return 0

    print(f"dead-probe-check: {len(findings)} removed selector(s) still referenced by a probe")
    print("(advisory, not blocking - verify by hand, a probe legitimately naming a deleted")
    print("thing in a comment is a false positive)")
    for file_path, raw, key, hit_lines in findings:
        print(f"  - removed from {file_path}: \"{raw}\" (matched on \"{key}\")")
        for h in hit_lines:
            print(f"      still referenced in: {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
