"""Self-test for migrate-todo-ids.py: dry run, apply, idempotency, collision refusal,
git mv for tracked files, PLAN.md rewriting. Every case runs the real CLI against temp
fixture repos; nothing outside tempfile.TemporaryDirectory() is read or written.

Run directly: python tools/test_migrate_todo_ids.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

SCRIPT = ROOT / "tools" / "migrate-todo-ids.py"
fails = []


def check(label: str, ok: bool) -> None:
    if not _testlib.report(ok, label):
        fails.append(label)


def run(*args: str, claude_home: Path) -> subprocess.CompletedProcess:
    # --claude-home keeps discovery away from the real ~/.claude backlog.
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--claude-home", str(claude_home), *args],
        capture_output=True, text=True, timeout=120,
    )


def snapshot(repo: Path) -> dict:
    return {
        p.relative_to(repo).as_posix(): p.read_bytes()
        for p in sorted(repo.rglob("*")) if p.is_file() and ".git" not in p.relative_to(repo).parts
    }


def names(directory: Path) -> list:
    return sorted(p.name for p in directory.iterdir() if p.is_file()) if directory.is_dir() else []


PLAN = "\n".join([
    "# Plan",
    "",
    "## 0.9",
    "- [ ] 1407 - label for the first",
    "- [ ] 7 [P] - parallel one",
    "- [ ] **0008** - bold",
    "- [ ] __9__ - underscore",
    "- [ ] `10` - backtick",
    "- [ ] pc-0011 - already migrated",
    "- [ ] mac-0012 - another device",
    "- [ ] 13",
    "  wrapped continuation mentioning todo 1407 in prose",
    "",
    "Free text line with 1407 inside stays.",
    "",
])


def make_repo(base: Path, name: str = "repo", crlf: bool = False) -> Path:
    repo = base / name
    todos = repo / ".claude" / "todos"
    (todos / "done").mkdir(parents=True)
    (todos / ".claims").mkdir()
    (todos / "1407-live-one.md").write_text("# one\n\nsee todo 1407 and todo 7\n", encoding="utf-8")
    (todos / "07-second.md").write_text("# two\n", encoding="utf-8")
    (todos / "pc-0011-already.md").write_text("# already\n", encoding="utf-8")
    (todos / "mac-0012-theirs.md").write_text("# theirs\n", encoding="utf-8")
    (todos / "notes-without-id.md").write_text("# loose note\n", encoding="utf-8")
    (todos / "done" / "0008-archived.md").write_text("# done\n", encoding="utf-8")
    (todos / "done" / "pc-0020-archived-new.md").write_text("# done new\n", encoding="utf-8")
    (todos / ".claims" / "1407.claim").write_text("session: s\npid: 1\n", encoding="utf-8")
    (todos / ".claims" / "7-second.claim").write_text("session: s\npid: 1\n", encoding="utf-8")
    (todos / ".claims" / "pc-0011.claim").write_text("session: s\npid: 1\n", encoding="utf-8")
    (todos / "9-.reserved").write_text("session: s\npid: 1\n", encoding="utf-8")
    plan = PLAN.replace("\n", "\r\n") if crlf else PLAN
    with open(todos / "PLAN.md", "w", encoding="utf-8", newline="") as fh:
        fh.write(plan)
    return repo


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    empty_home = base / "empty-claude-home"
    empty_home.mkdir()
    repo = make_repo(base)
    todos = repo / ".claude" / "todos"

    # --- dry run is the default and touches nothing ---
    before = snapshot(repo)
    proc = run("--repo", str(repo), claude_home=empty_home)
    check(f"dry run exits 0 and says DRY RUN (rc={proc.returncode}, out={proc.stdout!r})",
          proc.returncode == 0 and "DRY RUN" in proc.stdout)
    check("dry run changes no file", snapshot(repo) == before)
    check(f"dry run reports 2 backlog + 1 done, 2 claims, 1 reserved, 6 PLAN lines (out={proc.stdout!r})",
          "would rename 2 backlog + 1 done" in proc.stdout and "2 claims" in proc.stdout
          and "1 reserved markers" in proc.stdout and "6 PLAN line(s)" in proc.stdout)

    # --- apply ---
    log_path = base / "log" / "rename.json"
    proc = run("--repo", str(repo), "--apply", "--log", str(log_path), claude_home=empty_home)
    check(f"apply exits 0 (rc={proc.returncode}, out={proc.stdout!r}, err={proc.stderr!r})", proc.returncode == 0)
    check(f"backlog files renamed to pc-NNNN, others untouched (got {names(todos)})",
          names(todos) == sorted([
              "pc-1407-live-one.md", "pc-0007-second.md", "pc-0011-already.md", "mac-0012-theirs.md",
              "notes-without-id.md", "pc-0009-.reserved", "PLAN.md",
          ]))
    check(f"done/ renamed, already-prefixed left (got {names(todos / 'done')})",
          names(todos / "done") == sorted(["pc-0008-archived.md", "pc-0020-archived-new.md"]))
    check(f"claims renamed incl. the slug-suffixed form (got {names(todos / '.claims')})",
          names(todos / ".claims") == sorted(["pc-1407.claim", "pc-0007-second.claim", "pc-0011.claim"]))
    check("todo body prose is not rewritten",
          (todos / "pc-1407-live-one.md").read_text(encoding="utf-8") == "# one\n\nsee todo 1407 and todo 7\n")

    plan_after = (todos / "PLAN.md").read_text(encoding="utf-8")
    expected_plan = "\n".join([
        "# Plan",
        "",
        "## 0.9",
        "- [ ] pc-1407 - label for the first",
        "- [ ] pc-0007 [P] - parallel one",
        "- [ ] **pc-0008** - bold",
        "- [ ] __pc-0009__ - underscore",
        "- [ ] `pc-0010` - backtick",
        "- [ ] pc-0011 - already migrated",
        "- [ ] mac-0012 - another device",
        "- [ ] pc-0013",
        "  wrapped continuation mentioning todo 1407 in prose",
        "",
        "Free text line with 1407 inside stays.",
        "",
    ])
    check(f"PLAN lines rewritten with wrappers, [P], label and prose kept (got {plan_after!r})",
          plan_after == expected_plan)
    check("PLAN.md is BOM-less", not (todos / "PLAN.md").read_bytes().startswith(b"\xef\xbb\xbf"))

    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    log_renames = [r for e in log.get("repos", []) for r in e["renames"]]
    check(f"JSON log lists every rename (6 = 2 backlog + 1 done + 2 claims + 1 marker; got {len(log_renames)}) and the PLAN changes",
          len(log_renames) == 6 and log.get("applied") is True
          and len(log["repos"][0]["plan"]["changes"]) == 6)

    # --- idempotent: a second apply is a no-op ---
    after_first = snapshot(repo)
    second_log = base / "log" / "second.json"
    proc = run("--repo", str(repo), "--apply", "--log", str(second_log), claude_home=empty_home)
    check(f"second apply exits 0 and reports nothing to migrate (out={proc.stdout!r})",
          proc.returncode == 0 and "nothing to migrate" in proc.stdout)
    check("second apply changes no file and writes no log", snapshot(repo) == after_first and not second_log.exists())

# --- CRLF PLAN.md keeps its line endings ---
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    empty_home = base / "h"
    empty_home.mkdir()
    repo = make_repo(base, crlf=True)
    run("--repo", str(repo), "--apply", "--log", str(base / "l.json"), claude_home=empty_home)
    raw = (repo / ".claude" / "todos" / "PLAN.md").read_bytes()
    check("a CRLF PLAN.md stays CRLF, line for line", raw.count(b"\r\n") == PLAN.count("\n") and b"\n" not in raw.replace(b"\r\n", b""))

# --- collision guard: refuse the whole repo, touch nothing ---
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    empty_home = base / "h"
    empty_home.mkdir()
    repo = make_repo(base, "clash")
    todos = repo / ".claude" / "todos"
    (todos / "pc-1407-live-one.md").write_text("# already holds the target name\n", encoding="utf-8")
    before = snapshot(repo)
    proc = run("--repo", str(repo), "--apply", "--log", str(base / "l.json"), claude_home=empty_home)
    check(f"an existing target name refuses the repo with exit 1 (rc={proc.returncode}, out={proc.stdout!r})",
          proc.returncode == 1 and "REFUSED" in proc.stdout and "pc-1407-live-one.md" in proc.stdout)
    check("a refused repo is left byte-identical (no partial renames, no PLAN rewrite)", snapshot(repo) == before)

with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    empty_home = base / "h"
    empty_home.mkdir()
    repo = base / "twins"
    todos = repo / ".claude" / "todos"
    todos.mkdir(parents=True)
    (todos / "07-same.md").write_text("a\n", encoding="utf-8")
    (todos / "007-same.md").write_text("b\n", encoding="utf-8")
    before = snapshot(repo)
    proc = run("--repo", str(repo), "--apply", "--log", str(base / "l.json"), claude_home=empty_home)
    check(f"two sources mapping to one target name refuse the repo (rc={proc.returncode}, out={proc.stdout!r})",
          proc.returncode == 1 and "both map to" in proc.stdout and snapshot(repo) == before)

# --- git: tracked files move with git mv, untracked ones with a plain rename ---
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    empty_home = base / "h"
    empty_home.mkdir()
    repo = base / "gitrepo"
    todos = repo / ".claude" / "todos"
    todos.mkdir(parents=True)

    def git(*a):
        return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *a],
                              capture_output=True, text=True)

    git("init", "-q")
    (todos / "0101-tracked.md").write_text("tracked\n", encoding="utf-8")
    git("add", "--", ".claude/todos/0101-tracked.md")
    git("commit", "-q", "-m", "seed")
    (todos / "0102-untracked.md").write_text("untracked\n", encoding="utf-8")

    proc = run("--repo", str(repo), "--apply", "--log", str(base / "l.json"), claude_home=empty_home)
    tracked_now = git("ls-files", "--", ".claude/todos").stdout.split()
    status = git("status", "--porcelain").stdout
    check(f"tracked file moved with git mv: index holds the new name, rename staged (ls-files={tracked_now}, status={status!r})",
          ".claude/todos/pc-0101-tracked.md" in tracked_now and "R  .claude/todos/0101-tracked.md -> .claude/todos/pc-0101-tracked.md" in status)
    check("untracked file got a plain rename and stays untracked",
          (todos / "pc-0102-untracked.md").exists() and ".claude/todos/pc-0102-untracked.md" not in tracked_now)
    log = json.loads((base / "l.json").read_text(encoding="utf-8"))
    flags = {Path(r["to"]).name: r["git"] for e in log["repos"] for r in e["renames"]}
    check(f"log records which renames went through git (got {flags})",
          flags == {"pc-0101-tracked.md": True, "pc-0102-untracked.md": False})

# --- discovery: --projects-root finds every repo with a backlog, --repo limits to one ---
with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    projects = base / "Projects"
    a = make_repo(projects, "alpha")
    b = make_repo(projects, "beta")
    (projects / "no-backlog").mkdir()
    own = base / "claude-home"
    (own / ".claude" / "todos").mkdir(parents=True)
    (own / ".claude" / "todos" / "0001-global.md").write_text("g\n", encoding="utf-8")

    proc = run("--projects-root", str(projects), claude_home=own)
    out = proc.stdout
    check(f"default scan covers both projects plus the claude home, skips dirs without a backlog (out={out!r})",
          "3 repo(s)" in out and "alpha" in out and "beta" in out and "claude-home" in out and "no-backlog" not in out)
    check("totals line sums the repos", "TOTAL: 3 repo(s), 0 refused; would rename 7 todo files" in out)

    proc = run("--projects-root", str(projects), "--repo", str(a), claude_home=own)
    check(f"--repo limits the run to that one repo (out={proc.stdout!r})",
          "1 repo(s)" in proc.stdout and "beta" not in proc.stdout)

    proc = run("--repo", str(base / "nope"), claude_home=own)
    check("--repo on a path without .claude/todos exits 2", proc.returncode == 2)

sys.exit(_testlib.summarize(fails, style="count"))
