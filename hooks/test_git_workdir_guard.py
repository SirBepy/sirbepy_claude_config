"""Self-test for git-workdir-guard.py.

Run directly: python hooks/test_git_workdir_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real guard.main() against two throwaway `git init` repos standing
in for the harness project ($CLAUDE_PROJECT_DIR) and a drifted shell cwd
(payload["cwd"]) - no live repo other than the temp ones this suite creates
and destroys.
"""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "git-workdir-guard.py"
)

fails = []


def make_repo(tmp: Path, name: str) -> Path:
    repo = tmp / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def run_main(command: str, cwd: str = "", project_dir=None, override=None):
    guard.read_payload = lambda: {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": cwd,
    }
    old_pd = os.environ.get("CLAUDE_PROJECT_DIR")
    old_bp = os.environ.get(guard.OVERRIDE_ENV)
    if project_dir is None:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
    else:
        os.environ["CLAUDE_PROJECT_DIR"] = project_dir
    if override is None:
        os.environ.pop(guard.OVERRIDE_ENV, None)
    else:
        os.environ[guard.OVERRIDE_ENV] = override
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            try:
                guard.main()
                code = 0
            except SystemExit as e:
                code = e.code
    finally:
        if old_pd is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = old_pd
        if old_bp is None:
            os.environ.pop(guard.OVERRIDE_ENV, None)
        else:
            os.environ[guard.OVERRIDE_ENV] = old_bp
    return code, buf.getvalue()


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    repo_a = make_repo(tmpdir, "repo_a")  # stands in for the harness project
    repo_b = make_repo(tmpdir, "repo_b")  # stands in for the drifted shell cwd
    root_a = guard.repo_root(str(repo_a))
    root_b = guard.repo_root(str(repo_b))

    code, err = run_main("git push", cwd=str(repo_b), project_dir=str(repo_a))
    ok = code == 2 and root_a in err and root_b in err
    fails += [] if ok else ["wrong-root push is blocked and names both roots"]

    code, err = run_main("git status", cwd=str(repo_b), project_dir=str(repo_a))
    fails += [] if (code == 0 and err == "") else ["wrong-root read-only git is allowed"]

    code, err = run_main(f'git -C "{repo_b}" push', cwd=str(repo_a), project_dir=str(repo_a))
    fails += [] if (code == 0 and err == "") else ["explicit git -C push passes through untouched"]

    code, err = run_main("git push", cwd=str(repo_a), project_dir=str(repo_a))
    fails += [] if (code == 0 and err == "") else ["same-root push is allowed"]

    code, err = run_main(f'cd "{repo_a}" && git push', cwd=str(repo_b), project_dir=str(repo_a))
    fails += [] if (code == 0 and err == "") else ["a same-command cd pin is honoured"]

    code, err = run_main("git commit -C HEAD -m x", cwd=str(repo_b), project_dir=str(repo_a))
    ok = code == 2 and root_a in err and root_b in err
    fails += [] if ok else ["subcommand-level -C (git commit -C <ref>) is not mistaken for a repo pin"]

    code, err = run_main("git push", cwd=str(repo_b), project_dir=None)
    fails += [] if (code == 0 and err == "") else ["missing CLAUDE_PROJECT_DIR fails open"]

    non_repo = tmpdir / "non-repo"
    non_repo.mkdir()
    code, err = run_main("git push", cwd=str(non_repo), project_dir=str(repo_a))
    fails += [] if (code == 0 and err == "") else ["non-git shell cwd fails open"]

    code, err = run_main("git push", cwd=str(repo_b), project_dir=str(repo_a), override="1")
    fails += [] if (code == 0 and err == "") else ["bypass env var allows a wrong-root push"]

sys.exit(_testlib.summarize(fails))
