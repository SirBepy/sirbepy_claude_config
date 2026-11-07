"""Self-test for _hookboot.py and its wiring into every _hooklib importer.

Run directly: python hooks/test_hookboot.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

The point: a `_hooklib.py` that another session is mid-way through writing must
not lock every session out. The retry is exercised end to end against a real
fail-closed guard (secret-write-guard.py) in a scratch copy of hooks/, with the
shared module broken at start and repaired while the guard sleeps in its retry.
A module that stays broken must still fail closed (exit 2), never go quiet.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import _testlib

HOOKS = Path(__file__).resolve().parent
PYTHON = sys.executable
fails = []

HOOKLIB_IMPORT_RE = re.compile(r"^\s*(?:from _hooklib import|import _hooklib\b)", re.MULTILINE)
BOOT_IMPORT_RE = re.compile(r"^\s*import _hookboot\b", re.MULTILINE)

# --- every hook that imports _hooklib at module level boots through _hookboot first ---

missing = []
for path in sorted(HOOKS.glob("*.py")):
    if path.stem.startswith(("test_", "_")):
        continue
    text = path.read_text(encoding="utf-8")
    first_lib = HOOKLIB_IMPORT_RE.search(text)
    if not first_lib:
        continue
    boot = BOOT_IMPORT_RE.search(text)
    if not boot or boot.start() > first_lib.start():
        missing.append(path.name)
fails += [] if _testlib.report(not missing, f"every _hooklib importer imports _hookboot first (missing: {missing})") else ["wiring"]

# --- scratch copy of hooks/ for the behavior cases ---

GOOD_PAYLOAD = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "notes.txt", "content": "hello"}})
BROKEN_LIB = "def read_payload(:\n    this is a half-written module\n"


def scratch_hooks() -> Path:
    root = Path(tempfile.mkdtemp(prefix="hookboot-test-"))
    dest = root / "hooks"
    dest.mkdir()
    for name in ("_hooklib.py", "_hookboot.py", "secret-write-guard.py", "secret-patterns.txt"):
        shutil.copy(HOOKS / name, dest / name)
    return dest


def run_guard(dest: Path, repair_after_s: float | None, delay_s: float, broken_lib: str = BROKEN_LIB) -> subprocess.CompletedProcess:
    good_lib = (HOOKS / "_hooklib.py").read_text(encoding="utf-8")
    (dest / "_hooklib.py").write_text(broken_lib, encoding="utf-8")
    env = {"CLAUDE_HOOK_IMPORT_RETRY_DELAY_S": str(delay_s), "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    proc = subprocess.Popen(
        [PYTHON, str(dest / "secret-write-guard.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env,
    )
    timer = None
    if repair_after_s is not None:
        timer = threading.Timer(repair_after_s, lambda: (dest / "_hooklib.py").write_text(good_lib, encoding="utf-8"))
        timer.start()
    out, err = proc.communicate(GOOD_PAYLOAD, timeout=60)
    if timer:
        timer.cancel()
        timer.join()
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)


dest = scratch_hooks()
try:
    # Repaired 0.8s in, retry sleeps 2.0s: without the retry the guard exits 2 at ~0.3s.
    repaired = run_guard(dest, repair_after_s=0.8, delay_s=2.0)
    fails += [] if _testlib.report(
        repaired.returncode == 0,
        f"a _hooklib repaired during the retry sleep lets the guard run (exit {repaired.returncode}: {repaired.stderr.strip()[:120]})",
    ) else ["repaired during retry"]

    still_broken = run_guard(dest, repair_after_s=None, delay_s=0.1)
    fails += [] if _testlib.report(
        still_broken.returncode == 2 and "FATAL" in still_broken.stderr,
        f"a _hooklib that stays broken after the retry still fails closed (exit {still_broken.returncode})",
    ) else ["stays broken"]

    # Opening for write truncates first, so an EMPTY file (and one cut at a statement
    # boundary) imports cleanly; only the hook's own `from _hooklib import ...` fails.
    # Review finding 2026-11-07: that used to exit 2 at once with no retry.
    good_text = (HOOKS / "_hooklib.py").read_text(encoding="utf-8")
    truncated = good_text[: good_text.index("\ndef ask(")]
    for shape, text in (("empty", ""), ("cut at a statement boundary", truncated)):
        repaired = run_guard(dest, repair_after_s=0.8, delay_s=2.0, broken_lib=text)
        fails += [] if _testlib.report(
            repaired.returncode == 0,
            f"a {shape} _hooklib repaired during the retry sleep lets the guard run (exit {repaired.returncode}: {repaired.stderr.strip()[:120]})",
        ) else [f"{shape} repaired during retry"]

        stuck = run_guard(dest, repair_after_s=None, delay_s=0.1, broken_lib=text)
        fails += [] if _testlib.report(
            stuck.returncode == 2,
            f"a {shape} _hooklib that stays that way still fails closed (exit {stuck.returncode})",
        ) else [f"{shape} stays broken"]
finally:
    shutil.rmtree(dest.parent, ignore_errors=True)

# --- preload() contract: names still broken come back, healthy ones do not ---

boot = _testlib.load_module("hookboot_under_test", HOOKS / "_hookboot.py")
fails += [] if _testlib.report(
    boot.preload("json", retries=0) == [] and boot.preload("definitely_not_a_module_1278", retries=0) == ["definitely_not_a_module_1278"],
    "preload reports only the modules that stay unimportable",
) else ["preload contract"]

# A module that imports cleanly but lacks its sentinel counts as broken, and the sentinel
# is the last statement of the real _hooklib (a cut file cannot carry it).
with tempfile.TemporaryDirectory() as tmp:
    sys.path.insert(0, tmp)
    try:
        (Path(tmp) / "boot_sentinel_fixture.py").write_text("X = 1\n", encoding="utf-8")
        got = boot.preload("boot_sentinel_fixture", retries=0, sentinels={"boot_sentinel_fixture": "_DONE"})
        fails += [] if _testlib.report(got == ["boot_sentinel_fixture"], "a module without its sentinel is reported broken") else ["sentinel missing"]
        (Path(tmp) / "boot_sentinel_fixture.py").write_text("X = 1\n_DONE = True\n", encoding="utf-8")
        got = boot.preload("boot_sentinel_fixture", retries=0, sentinels={"boot_sentinel_fixture": "_DONE"})
        fails += [] if _testlib.report(got == [], "a module with its sentinel is healthy") else ["sentinel present"]
    finally:
        sys.path.remove(tmp)
        sys.modules.pop("boot_sentinel_fixture", None)

import ast

last = ast.parse((HOOKS / "_hooklib.py").read_text(encoding="utf-8")).body[-1]
fails += [] if _testlib.report(
    isinstance(last, ast.Assign) and getattr(last.targets[0], "id", "") == boot.SENTINELS["_hooklib"],
    "_hooklib's last statement is its completion sentinel",
) else ["sentinel last"]

# --- one is_agent_call, in _hooklib: no guard execs another guard's whole file for a predicate ---

hooklib = _testlib.load_module("hooklib_under_test", HOOKS / "_hooklib.py")
for stem, filename in (
    ("commit_guard_under_test", "commit-guard.py"),
    ("agent_todo_guard_under_test", "agent-todo-write-guard.py"),
    ("testing_floor_lib_under_test", "_testing_floor_lib.py"),
):
    module = _testlib.load_module(stem, HOOKS / filename)
    label = f"{filename} uses _hooklib.is_agent_call"
    # Same code object, not identity: each load_module call re-executes _hooklib.
    same = module.is_agent_call.__code__.co_filename == hooklib.is_agent_call.__code__.co_filename
    if not _testlib.report(same, label):
        fails.append(label)
label = "is_agent_call keys on agent_id"
if not _testlib.report(hooklib.is_agent_call({"agent_id": "a1"}) and not hooklib.is_agent_call({"session_id": "s"}), label):
    fails.append(label)

sys.exit(_testlib.summarize(fails))
