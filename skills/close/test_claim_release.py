"""Self-test for claim-todo.ps1 -Release (todo 1323).

A /loop-todos run claims the whole backlog up front and only complete-todo.ps1 removed claims,
so every todo the loop left open kept a claim that blocked peers. -Release deletes only claims
whose recorded session id is the current session's; a peer's claim must survive.

Run directly: python skills/close/test_claim_release.py (exit 0 on all-pass). Drives the real
script via powershell.exe against scratch backlogs under tempfile, with a throwaway device-label
file, so it never touches the real .claude/todos/ or ~/.claude/device-label.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(os.environ.get("CLOSE_CLAIM_SCRIPT", str(Path(__file__).resolve().parent / "claim-todo.ps1")))

_LABEL_DIR = tempfile.TemporaryDirectory()
LABEL_FILE = Path(_LABEL_DIR.name) / "device-label"
LABEL_FILE.write_text("pc\n", encoding="utf-8")
BASE_ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_SESSION_ID"}
BASE_ENV["CLAUDE_DEVICE_LABEL_FILE"] = str(LABEL_FILE)

SESS_A = "sess-aaaa"
SESS_B = "sess-bbbb"
ENV_A = dict(BASE_ENV, CLAUDE_CODE_SESSION_ID=SESS_A)
ENV_B = dict(BASE_ENV, CLAUDE_CODE_SESSION_ID=SESS_B)

fails = []


def run(*args, env):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), *args],
        capture_output=True, text=True, timeout=60, env=env,
    )


def make_backlog(tmp, *names):
    todos = Path(tmp) / ".claude" / "todos"
    todos.mkdir(parents=True)
    for n in names:
        (todos / n).write_text(f"# {n}\n", encoding="utf-8")
    return Path(tmp), todos / ".claims"


def session_of(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("session:"):
            return line.split(":", 1)[1].strip()
    return ""


def check(label, ok):
    print(f"{'PASS' if ok else 'FAIL'}: {label}")
    if not ok:
        fails.append(label)


with tempfile.TemporaryDirectory() as tmp:
    repo, c = make_backlog(tmp, "pc-0001-a.md", "pc-0002-b.md", "pc-0003-c.md")
    run("-Id", "pc-0001,pc-0002", "-RepoRoot", str(repo), env=ENV_A)
    run("-Id", "pc-0003", "-RepoRoot", str(repo), env=ENV_B)
    check("setup: claim files record the session id",
          session_of(c / "pc-0001.claim") == SESS_A and session_of(c / "pc-0003.claim") == SESS_B)

    p = run("-Release", "-Id", "pc-0001,pc-0003", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release removes this session's pc-0001.claim and leaves a peer's pc-0003.claim (out={p.stdout!r})",
          not (c / "pc-0001.claim").exists() and (c / "pc-0003.claim").exists() and (c / "pc-0002.claim").exists()
          and "Released claim pc-0001.claim" in p.stdout)
    check(f"-Release exits 1 when an id's claim belongs to another session (rc={p.returncode})", p.returncode == 1)

    p = run("-Release", "-Id", "pc-0001", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release of an already-released id is a clean no-op (rc={p.returncode}, out={p.stdout!r})", p.returncode == 0)

    p = run("-Release", "-AllMine", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release -AllMine removes this session's claims and no peer's (rc={p.returncode}, out={p.stdout!r})",
          p.returncode == 0 and not (c / "pc-0002.claim").exists() and (c / "pc-0003.claim").exists())

    p = run("-Release", "-Id", "pc-0003", "-RepoRoot", str(repo), env=BASE_ENV)
    check(f"-Release without a session id refuses and deletes nothing (rc={p.returncode}, out={p.stdout!r})",
          p.returncode == 2 and (c / "pc-0003.claim").exists())

with tempfile.TemporaryDirectory() as tmp:
    repo, c = make_backlog(tmp, "pc-0007-alpha.md", "pc-0007-beta.md")
    run("-Id", "pc-0007", "-Slug", "alpha", "-RepoRoot", str(repo), env=ENV_A)
    run("-Id", "pc-0007", "-Slug", "beta", "-RepoRoot", str(repo), env=ENV_B)
    p = run("-Release", "-Id", "pc-0007-alpha", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release with a full stem releases only that sibling's claim (rc={p.returncode}, out={p.stdout!r})",
          p.returncode == 0 and not (c / "pc-0007-alpha.claim").exists() and (c / "pc-0007-beta.claim").exists())

with tempfile.TemporaryDirectory() as tmp:
    repo, c = make_backlog(tmp, "pc-0001-a.md")
    p = run("-RepoRoot", str(repo), env=ENV_A)
    check(f"claiming with no -Id still fails loudly (rc={p.returncode})", p.returncode == 2)
    p = run("-Release", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release with neither -Id nor -AllMine fails loudly (rc={p.returncode}, out={p.stdout!r})", p.returncode == 2)
    run("-Id", "pc-0001", "-RepoRoot", str(repo), env=ENV_A)
    p = run("-Id", "pc-0001", "-AllMine", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-AllMine without -Release is rejected and claims nothing new (rc={p.returncode})", p.returncode == 2)

with tempfile.TemporaryDirectory() as tmp:
    # Two spellings of one id resolve to the same claim file; the second must not find it
    # already gone and call it a peer's claim.
    repo, c = make_backlog(tmp, "pc-0001-a.md")
    run("-Id", "pc-0001", "-RepoRoot", str(repo), env=ENV_A)
    p = run("-Release", "-Id", "pc-0001,1", "-RepoRoot", str(repo), env=ENV_A)
    check(f"-Release of one claim named twice (pc-0001,1) releases it once and exits 0 (rc={p.returncode}, out={p.stdout!r})",
          p.returncode == 0 and not (c / "pc-0001.claim").exists()
          and "another session" not in p.stdout and p.stdout.count("Released claim") == 1)

_LABEL_DIR.cleanup()
if fails:
    print(f"\n{len(fails)} FAILURE(S)")
    sys.exit(1)
print("\nall passed")
