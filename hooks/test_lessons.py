"""Self-test for the cross-project lessons mechanism (todo 1154):
skills/cleanup-memory/lessons_sweep.py (scan, promote, index),
hooks/lessons-index.py (SessionStart injection) and the trigger hook's scan of
the lessons folder.

Run directly: python hooks/test_lessons.py
Exits 0 on all-pass, 1 on any failure. Everything runs in scratch dirs.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_REPO = _HOOKS_DIR.parent
sweep = _testlib.load_module("lessons_sweep", _REPO / "skills" / "cleanup-memory" / "lessons_sweep.py")
mt = sweep.mt
_INDEX_HOOK = _HOOKS_DIR / "lessons-index.py"

results = []


def case(label, ok):
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    results.append((label, ok))


def memory_text(name, description, kind="feedback", extra="", body="Body text."):
    return f"---\nname: {name}\ndescription: {description}\n{extra}metadata:\n  type: {kind}\n---\n{body}\n"


def add_memory(root, project, filename, text):
    d = Path(root) / project / "memory"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(text, encoding="utf-8")
    return str(d / filename)


def run_sweep_cases(tmp):
    roots = Path(tmp) / "projects"
    os.environ[mt.LESSONS_ENV] = str(Path(tmp) / "lessons")
    bases = ["zng-app", "revaire-server"]

    a = add_memory(roots, "C--Users-tecno-proj-alpha", "feedback_gentle_runs.md",
                   memory_text("gentle-local-runs", "Joe wants long local GPU runs gentle on CPU and RAM even if slower"))
    b = add_memory(roots, "C--Users-tecno-proj-beta", "feedback_gentle.md",
                   memory_text("gentle-gpu-runs", "Long local GPU runs must stay gentle on CPU and RAM, slower is fine"))
    add_memory(roots, "C--Users-tecno-proj-alpha", "reference_thing.md",
               memory_text("gentle-thing", "Long local GPU runs reference note", kind="reference"))
    add_memory(roots, "C--Users-tecno-proj-gamma", "feedback_old.md",
               memory_text("old-gentle", "Long local GPU runs gentle on CPU and RAM", extra="superseded_by: gentle-local-runs\n"))
    add_memory(roots, "C--Users-tecno-proj-alpha--claude-worktrees-sub-1", "feedback_wt.md",
               memory_text("worktree-copy", "Zebra migrations always need a rollback script before running"))
    add_memory(roots, "C--Users-tecno-proj-alpha", "feedback_zebra.md",
               memory_text("zebra-rollback", "Zebra migrations always need a rollback script before running"))
    add_memory(roots, "C--Users-tecno-Desktop-Projects-zng-app", "feedback_client.md",
               memory_text("client-rule", "Quokka deploys need the staging flag set before pushing"))
    add_memory(roots, "C--Users-tecno-proj-delta", "feedback_quokka.md",
               memory_text("quokka-flag", "Quokka deploys need the staging flag set before pushing"))

    items = sweep.gather_feedback([str(roots)])
    names = sorted(i["name"] for i in items)
    case("gather: feedback only, superseded skipped", "gentle-thing" not in names and "old-gentle" not in names and len(items) == 6)
    case("project_key folds a worktree dir into its project",
         sweep.project_key("C--Users-tecno-proj-alpha--claude-worktrees-sub-1") == "C--Users-tecno-proj-alpha")

    cands, held = sweep.candidates(items, bases)
    flat = [sorted(m["name"] for m in g) for g in cands]
    case("cluster: the same lesson in two projects is a candidate", ["gentle-gpu-runs", "gentle-local-runs"] in flat)
    case("cluster: a worktree copy is not independent confirmation", not any("worktree-copy" in g for g in flat))
    case("cluster: a client-project member holds the cluster back, unlisted",
         held == 1 and not any("quokka-flag" in g or "client-rule" in g for g in flat))
    case("is_client_project matches a hyphen-delimited repo name only",
         sweep.is_client_project("C--Users-tecno-Desktop-Projects-zng-app", bases)
         and not sweep.is_client_project("C--Users-tecno-Desktop-Projects-zng-appendix", bases))

    # --- promote
    code, msg = sweep.promote("gentle-runs", "Long local runs stay gentle on CPU, GPU and RAM", "Cap the clocks.\n",
                              [a, b], ["**/ollama/**"], [], supersede=True, bases=bases)
    lesson = Path(sweep.lessons_dir()) / "gentle-runs.md"
    text = lesson.read_text(encoding="utf-8") if lesson.is_file() else ""
    case("promote: ADD writes the lesson with sources and triggers", code == 0 and "sources:" in text and a in text and "**/ollama/**" in text)
    case("promote: --supersede stamps the sources", "superseded_by: gentle-runs" in Path(a).read_text(encoding="utf-8"))
    index = (Path(sweep.lessons_dir()) / "INDEX.md").read_text(encoding="utf-8")
    case("promote: INDEX.md lists the lesson", "[gentle-runs](gentle-runs.md)" in index)

    c = add_memory(roots, "C--Users-tecno-proj-epsilon", "feedback_more.md", memory_text("gentle-more", "Gentle runs again"))
    code, _ = sweep.promote("gentle-runs", "Long local runs stay gentle", "Cap the clocks, updated.\n", [c], [], [], False, bases)
    text2 = lesson.read_text(encoding="utf-8")
    case("promote: UPDATE keeps the file and merges sources",
         code == 0 and a in text2 and c in text2 and text2.count(c) == 1 and "updated" in text2)

    client_src = str(Path(roots) / "C--Users-tecno-Desktop-Projects-zng-app" / "memory" / "feedback_client.md")
    code, msg = sweep.promote("client-lesson", "x", "y", [client_src], [], [], False, bases)
    case("promote: refuses a client-project source and writes nothing",
         code == 2 and "client" in msg and not (Path(sweep.lessons_dir()) / "client-lesson.md").exists())
    code, msg = sweep.promote("Bad Name!", "x", "y", [a], [], [], False, bases)
    case("promote: refuses a non-slug name", code == 2)

    # --- the trigger hook sees the lessons folder
    os.environ[mt.STATE_ENV] = str(Path(tmp) / "state")
    os.environ[mt.RECHECK_ENV] = "0"
    table = mt.load_table([str(roots)], force=True)
    ids = [e["name"] for e in table["entries"]]
    case("triggers: a lesson declaring triggers is in the table, INDEX.md is not",
         "gentle-runs" in ids and not any(e["path"].endswith("INDEX.md") for e in table["entries"]))
    code, out, err = mt.run_hook({"tool_name": "Read", "tool_input": {"file_path": "C:/x/ollama/run.py"},
                                  "session_id": "L1", "cwd": tmp}, roots=[str(roots)])
    case("triggers: the promoted lesson loads in a project that never had it",
         code == 0 and "Cap the clocks" in json.loads(out)["hookSpecificOutput"]["additionalContext"])


def run_index_cases(tmp):
    ldir = Path(tmp) / "lessons-cap"
    os.environ[mt.LESSONS_ENV] = str(ldir)
    ldir.mkdir()
    for i in range(300):
        (ldir / f"lesson-{i:03d}.md").write_text(memory_text(f"lesson-{i:03d}", "A reasonably long description of the lesson " + "x" * 60), encoding="utf-8")
    sweep.build_index()
    size = (ldir / "INDEX.md").stat().st_size
    text = (ldir / "INDEX.md").read_text(encoding="utf-8")
    case("index: byte-capped with a 'more' line when lessons overflow", size <= sweep.INDEX_BYTE_CAP and "more in ~/.claude/lessons/" in text)

    env = dict(os.environ)
    env[mt.LESSONS_ENV] = str(ldir)
    proc = subprocess.run([sys.executable, str(_INDEX_HOOK)], input="{}", capture_output=True, text=True, env=env)
    out = json.loads(proc.stdout)["hookSpecificOutput"]
    case("hook: SessionStart additionalContext carries the index, exit 0",
         proc.returncode == 0 and out["hookEventName"] == "SessionStart" and "lesson-000" in out["additionalContext"])

    (ldir / "INDEX.md").write_text("- row\n" * 5000, encoding="utf-8")
    proc = subprocess.run([sys.executable, str(_INDEX_HOOK)], input="{}", capture_output=True, text=True, env=env)
    injected = json.loads(proc.stdout)["hookSpecificOutput"]["additionalContext"]
    case("hook: re-applies the byte cap at read time", len(injected.encode("utf-8")) <= 4096 + 64 and "truncated" in injected)

    env[mt.LESSONS_ENV] = str(Path(tmp) / "no-such-lessons")
    proc = subprocess.run([sys.executable, str(_INDEX_HOOK)], input="{}", capture_output=True, text=True, env=env)
    case("hook: no lessons folder prints nothing and exits 0", proc.returncode == 0 and proc.stdout == "")
    proc = subprocess.run([sys.executable, str(_INDEX_HOOK)], input="not json", capture_output=True, text=True, env=env)
    case("hook: garbage stdin fails open", proc.returncode == 0)


def run() -> int:
    saved = {k: os.environ.get(k) for k in (mt.LESSONS_ENV, mt.STATE_ENV, mt.RECHECK_ENV)}
    with tempfile.TemporaryDirectory() as tmp:
        run_sweep_cases(tmp)
        run_index_cases(tmp)
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return _testlib.summarize([label for label, ok in results if not ok])


if __name__ == "__main__":
    sys.exit(run())
