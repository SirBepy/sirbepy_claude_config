"""Shared temp-repo helpers for the /release script tests. Not a test itself (leading underscore)."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELEASE_PY = HERE / "release.py"
SHIP_CONFIG_PY = HERE / "ship-config.py"


def base_env(**extra):
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    # A local-path submodule needs the file transport; scoped to the child processes so no
    # real git config on the machine is touched.
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "protocol.file.allow"
    env["GIT_CONFIG_VALUE_0"] = "always"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.update(extra)
    return env


def git(cwd, *args, check=True):
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=base_env(),
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {cwd}: {proc.stderr}")
    return proc.stdout.strip()


def configure(path):
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "core.autocrlf", "false")
    git(path, "config", "commit.gpgsign", "false")


def write(path, rel, content):
    target = Path(path) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))


def read(path, rel):
    return (Path(path) / rel).read_bytes()


def make_repo(path, files, origin=None, track=True):
    """Fresh repo on branch main with `files` committed (when `track`), optional origin URL."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    configure(path)
    for rel, content in files.items():
        write(path, rel, content)
    if track:
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", "init")
    if origin:
        git(path, "remote", "add", "origin", origin)
    return path


def commit_all(path, message):
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", message)


def run_script(script, *args, env=None):
    """(exit code, parsed JSON stdout). `-I` mirrors how skills are meant to call these."""
    proc = subprocess.run(
        [sys.executable, "-I", str(script), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", env=env or base_env(),
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"not JSON (exit {proc.returncode}): {proc.stdout!r} / {proc.stderr!r}")
    return proc.returncode, payload


def tempdir():
    # git marks object files read-only, which makes plain cleanup fail on Windows.
    return tempfile.TemporaryDirectory(prefix="release-test-", ignore_cleanup_errors=True)
