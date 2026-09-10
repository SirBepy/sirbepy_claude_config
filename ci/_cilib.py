"""Shared helpers for ci/*.py scripts. Two callers justify this; keep it tiny (todo 912)."""

import subprocess
from pathlib import Path


def tracked_files(root: Path, subdir: str):
    """Returns the set of `<subdir>/*` paths git has in its index (posix, repo-relative),
    or None if git could not be queried (non-repo checkout, git missing, timeout).

    Discovery callers use this to skip untracked candidates (todo 805): a peer session's
    half-written untracked file must not be able to fail a gate it was never committed to.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", subdir],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}
