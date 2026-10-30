"""Self-test for count_invocations.py and days_since.py.

Run: python skills/global-claude-folder-audit/test_audit_scripts.py   (exit 0 = all pass)

Builds a synthetic projects tree in a temp dir, so it reads no real transcript and needs no git
history beyond what local_skills() tolerates (an untracked skill reports an empty created date).
"""

import datetime as dt
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
failures = []


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(cond, label, detail=""):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)
        if detail:
            print(f"  {detail}")


ci = load("count_invocations")
ds = load("days_since")


def rec(kind, content, ts):
    return json.dumps({"type": kind, "timestamp": ts, "message": {"content": content}})


with tempfile.TemporaryDirectory() as tmp:
    projects = Path(tmp) / "projects"
    session = projects / "C--repo" / "s1.jsonl"
    sub = projects / "C--repo" / "s1" / "subagents" / "agent-a.jsonl"
    other = projects / "C--other" / "s2.jsonl"
    for p in (session, sub, other):
        p.parent.mkdir(parents=True, exist_ok=True)
    session.write_text("\n".join([
        rec("user", "<command-name>/commit</command-name> <command-name>/commit</command-name>", "2026-10-01T10:00:00Z"),
        rec("assistant", [{"type": "tool_use", "name": "Skill", "input": {"skill": "brainstorm"}}], "2026-10-02T10:00:00Z"),
        rec("assistant", [{"type": "tool_use", "name": "Read", "input": {"skill": "not-a-skill"}}], "2026-10-02T11:00:00Z"),
        "not json at all <command-name>/broken</command-name>",
    ]) + "\n", encoding="utf-8")
    sub.write_text(rec("assistant", [{"type": "tool_use", "name": "Skill", "input": {"skill": "commit"}}], "2026-10-03T10:00:00Z") + "\n", encoding="utf-8")
    other.write_text(rec("user", [{"type": "text", "text": "<command-name>commit</command-name>"}], "2026-10-05T10:00:00Z") + "\n", encoding="utf-8")

    stats, window = ci.scan(projects)
    commit = stats.get("commit", {})
    check(commit.get("invocations") == 3, "repeated tag in one line counts once, subagent and list content count",
          f"got {commit.get('invocations')}")
    check(len(commit.get("sessions", ())) == 2, "subagent transcript folds into its parent session",
          f"got {commit.get('sessions')}")
    check(commit.get("last_used", "").startswith("2026-10-05"), "last_used is the newest timestamp")
    check("brainstorm" in stats, "Skill tool_use is counted")
    check("not-a-skill" not in stats, "a non-Skill tool with a skill key is ignored")
    check("broken" not in stats, "an unparseable line is skipped, not crashed on")
    check(window == ["2026-10-01T10:00:00Z", "2026-10-05T10:00:00Z"], "window spans first to last invocation",
          f"got {window}")

    report = ci.build_report(stats, window, {"commit": "2026-08-01", "never-used": "2026-10-20"})
    local = {r["skill"]: r for r in report["local"]}
    check(local["never-used"]["sessions"] == 0, "an unused local skill reports zero")
    check(report["local"][0]["skill"] == "never-used", "least-used skills sort first")
    check([r["skill"] for r in report["external"]] == ["brainstorm"], "invoked names without a local dir are external")

ledger = """# Ledger

## Runs

- 2026-07-01 first run
- 2026-10-30 second run

## Declined

- 2026-12-31 not a run date, wrong section
"""
dates = ds.run_dates(ledger)
check(dates == [dt.date(2026, 7, 1), dt.date(2026, 10, 30)], "only the Runs section is read", f"got {dates}")
out = ds.card(dates, dt.date(2026, 11, 9))
check(out["days_since"] == 10 and out["_card"]["headline_tone"] == "good", "recent run is good", f"got {out}")
check(ds.card(dates, dt.date(2027, 4, 1))["_card"]["headline_tone"] == "warn", "a stale run turns warn")
check(ds.card([], dt.date(2026, 11, 9))["_card"]["headline"] == "never run", "an empty ledger says never run")

if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
