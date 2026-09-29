"""Client-repo detection plus the pushable marker client-push-gate.py checks.

A repo is a client repo when its origin's `owner/repo` slug is listed in
refs/client-repos.txt. Markers live in hooks/.client-push-ok/<HEAD sha>, one
file per pushable commit, holding the stated reason, so every override Joe
approved stays on disk as a record.

CLI, for skills and scripts that cannot import this:
  python _client_repo.py is-client [path]            prints client|personal
  python _client_repo.py mark [path] --reason "..."  records HEAD as pushable
"""

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
CLIENT_LIST_PATH = _HOOKS_DIR.parent / "refs" / "client-repos.txt"
MARKER_DIR = _HOOKS_DIR / ".client-push-ok"
GIT_TIMEOUT_SECONDS = 10


def _git(path, *args) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def origin_slug(url: str) -> str | None:
    """`owner/repo`, lowercased, from any https/ssh/scp-style remote URL.
    Covers host aliases like `git@github-work:zirtue-corp/zng-api.git`."""
    parts = [p for p in re.split(r"[/:]", (url or "").strip()) if p]
    if len(parts) < 2:
        return None
    repo = parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return f"{parts[-2]}/{repo}".lower() if repo else None


def load_client_slugs(path: Path | None = None) -> set[str]:
    path = path or CLIENT_LIST_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    return {ln.strip().lower() for ln in lines if ln.strip() and not ln.strip().startswith("#")}


def client_slug(path) -> str | None:
    """The listed slug if `path` is inside a client repo, else None."""
    slug = origin_slug(_git(path, "remote", "get-url", "origin") or "")
    return slug if slug and slug in load_client_slugs() else None


def head_sha(path) -> str | None:
    return _git(path, "rev-parse", "HEAD")


def is_pushable(sha: str) -> bool:
    return bool(sha) and (MARKER_DIR / sha).exists()


def mark_pushable(path, reason: str) -> str:
    sha = head_sha(path)
    if not sha:
        raise SystemExit(f"ERROR: {path} has no HEAD commit to mark")
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    (MARKER_DIR / sha).write_text(f"{stamp} {reason}\n", encoding="utf-8")
    return sha


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="_client_repo.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_is = sub.add_parser("is-client")
    p_is.add_argument("path", nargs="?", default=".")
    p_mark = sub.add_parser("mark")
    p_mark.add_argument("path", nargs="?", default=".")
    p_mark.add_argument("--reason", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "is-client":
        print("client" if client_slug(args.path) else "personal")
        return 0
    if not client_slug(args.path):
        print(f"ERROR: {args.path} is not a listed client repo, nothing to mark")
        return 2
    sha = mark_pushable(args.path, args.reason)
    print(f"marked {sha[:7]} pushable: {args.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
