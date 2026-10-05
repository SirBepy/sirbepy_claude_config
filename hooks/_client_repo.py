"""Client-repo detection, for the client-only rules in snippets/client-repo.md.

A repo is a client repo when its origin's `owner/repo` slug is listed in
refs/client-repos.txt. The testing floor and push gate apply to every repo;
only the rules that snippet lists still key off this.

CLI, for skills and scripts that cannot import this:
  python _client_repo.py is-client [path]            prints client|personal
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
CLIENT_LIST_PATH = _HOOKS_DIR.parent / "refs" / "client-repos.txt"
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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="_client_repo.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_is = sub.add_parser("is-client")
    p_is.add_argument("path", nargs="?", default=".")
    args = parser.parse_args(argv)

    print("client" if client_slug(args.path) else "personal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
