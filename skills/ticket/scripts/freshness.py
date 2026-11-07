#!/usr/bin/env python3
"""Fetch the moving state a draft talks about and print it ready to paste as the spec's
`## Freshness` section (see verify_prompt.py) and into the verifier prompt's Pointers.

Run it right before dispatching the verifiers of `refs/outbound-verify.md`: a PR that merged
or a ticket that moved since the draft was written makes the text stale, and three verifiers
that all fetch first will all FAIL it (zng-app, 2026-11-03: PRs 970/971 had merged into
zng-api develop; one round of 3 verifiers, about 280k tokens, for a fact one fetch catches).

    python freshness.py --repo C:/path/to/repo@develop --story 56598 --story 56595
    python freshness.py --repo C:/path/to/repo@develop --find biller_landing

--repo PATH@BRANCH   `git fetch`, then the sha and subject of origin/BRANCH (repeatable)
--story ID           the story's current state, via shortcut_triage.py's read-only GET (repeatable)
--find TEXT          tracked paths at each --repo's origin/BRANCH containing TEXT, so the
                     Pointers carry real paths instead of ones the verifiers rediscover

Writes nothing. Exit 1 when any fetch or story read failed, with that line saying so.
"""

import argparse
import subprocess
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shortcut_triage as st

GIT_TIMEOUT_SECONDS = 120


def git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=GIT_TIMEOUT_SECONDS,
    )


def split_repo_arg(value: str) -> tuple:
    """`C:/path@develop` -> (`C:/path`, `develop`), split on the LAST `@`."""
    path, sep, branch = value.rpartition("@")
    if not sep or not path or not branch:
        raise ValueError(f"--repo wants PATH@BRANCH, got {value!r}")
    return path, branch


def repo_lines(path: str, branch: str, finds: list) -> tuple:
    """(lines, ok) for one repo after a fetch."""
    fetched = git(path, "fetch", "--quiet")
    if fetched.returncode != 0:
        return [f"- {path}: FETCH FAILED ({fetched.stderr.strip() or 'git fetch exited non-zero'})"], False
    ref = f"origin/{branch}"
    head = git(path, "log", "-1", "--format=%H %cI %s", ref)
    if head.returncode != 0:
        return [f"- {path}: {ref} NOT FOUND"], False
    lines = [f"- {path} {ref} = {head.stdout.strip()}"]
    if finds:
        tree = git(path, "ls-tree", "-r", "--name-only", ref)
        names = tree.stdout.splitlines()
        for needle in finds:
            hits = [n for n in names if needle.lower() in n.lower()]
            lines.append(f"  paths containing {needle!r} at {ref}: " + (", ".join(hits[:10]) or "none")
                         + (f" (+{len(hits) - 10} more)" if len(hits) > 10 else ""))
    return lines, True


def story_lines(ids: list, token: str) -> tuple:
    states = {
        s["id"]: s["name"]
        for wf in st.api_call("GET", "/api/v3/workflows", token)
        for s in wf["states"]
    }
    lines, ok = [], True
    for raw in ids:
        sid = st.parse_story_id(raw)
        try:
            story = st.api_call("GET", f"/api/v3/stories/{sid}", token)
        except urllib.error.HTTPError as e:
            lines.append(f"- sc-{sid}: HTTP {e.code}")
            ok = False
            continue
        state = states.get(story.get("workflow_state_id"), story.get("workflow_state_id"))
        lines.append(f"- sc-{sid}: {state}, blocked={bool(story.get('blocked'))}, updated {story.get('updated_at')}")
    return lines, ok


def build_report(repos: list, stories: list, finds: list, token: str | None = None) -> tuple:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out, ok = [f"Freshness (fetched {stamp}):"], True
    for value in repos:
        lines, good = repo_lines(*split_repo_arg(value), finds)
        out += lines
        ok = ok and good
    if stories:
        lines, good = story_lines(stories, token or st.read_token())
        out += lines
        ok = ok and good
    return "\n".join(out), ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="freshness.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", action="append", default=[], metavar="PATH@BRANCH")
    parser.add_argument("--story", action="append", default=[], metavar="ID")
    parser.add_argument("--find", action="append", default=[], metavar="TEXT")
    args = parser.parse_args(argv)
    if not (args.repo or args.story):
        parser.error("give at least one --repo or --story")
    try:
        report, ok = build_report(args.repo, args.story, args.find)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((report + "\n").encode("utf-8"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
