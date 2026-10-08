"""Self-test for recall.py. Builds a throwaway projects/ + memory-archive/ pair in a temp
dir, so it never reads the real transcripts and runs on CI's bare Windows runner.

Run: python skills/recall/test_recall.py   (exit 0 = all pass)
"""

import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recall  # noqa: E402

SID = "11111111-2222-3333-4444-555555555555"
SID_NEW = "66666666-7777-8888-9999-000000000000"
SLUG = "C--work-demo"
# Built by concatenation so this file itself never holds a literal key for the write guard.
AKIA = "AKIA" + "IOSFODNN7EXAMPLE"
ZWSP = "\u200b"

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def rec(**kw):
    return json.dumps(kw)


def transcript_lines():
    return [
        rec(type="user", timestamp="2026-01-10T09:00:00Z", cwd="C:/work/demo",
            message={"role": "user", "content": "Lets pick the vault design, not the MCP server"}),
        rec(type="user", timestamp="2026-01-10T09:00:01Z", isMeta=True,
            message={"role": "user", "content": "skill expansion text that Joe never typed"}),
        rec(type="user", timestamp="2026-01-10T09:01:00Z",
            message={"role": "user", "content": f"{ZWSP}[daemon-meta]{ZWSP} peer relay noise"}),
        rec(type="user", timestamp="2026-01-10T09:02:00Z",
            message={"role": "user", "content": "<system-reminder>injected hook text</system-reminder>my key is " + AKIA}),
        rec(type="assistant", timestamp="2026-01-10T09:03:00Z",
            message={"role": "assistant", "content": [
                {"type": "text", "text": "Plain assistant reply about vault"},
                {"type": "tool_use", "name": "mcp__cc_conductor__send_message", "input": {"text": "Bubble: chose the vault"}},
                {"type": "tool_use", "name": "mcp__cc_conductor__ask_user_question",
                 "input": {"questions": [{"question": "Keep transcripts forever?"}]}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}},
            ]}),
        rec(type="user", timestamp="2026-01-10T09:04:00Z",
            message={"role": "user", "content": [{"type": "tool_result", "content": "[master 5a4b270] CHORE: file todo 1150\n 1 file changed"}]}),
        rec(type="ai-title", aiTitle="Vault versus MCP"),
        "{truncated mid-li",
    ]


def write_session(projects, sid, lines, mtime=None, sidecar=True):
    d = projects / SLUG
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{sid}.jsonl"
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    files = [f]
    if sidecar:
        side = d / sid / "subagents"
        side.mkdir(parents=True, exist_ok=True)
        s = side / "agent-a1.jsonl"
        s.write_text(rec(type="user", message={"content": "subagent work"}) + "\n", encoding="utf-8")
        files.append(s)
    if mtime is not None:
        for p in files:
            os.utime(p, (mtime, mtime))
    return f


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        projects, archive = root / "projects", root / "memory-archive"
        old = datetime(2026, 1, 10, 12).timestamp()
        write_session(projects, SID, transcript_lines(), mtime=old)
        write_session(projects, SID_NEW, [rec(type="user", timestamp="2026-03-02T10:00:00Z", cwd="C:/work/demo",
                                              message={"content": "recent march chat about vault"})], sidecar=False)
        memory = projects / SLUG / "memory"
        memory.mkdir()
        (memory / "MEMORY.md").write_text("# index\n", encoding="utf-8")
        os.utime(memory / "MEMORY.md", (old, old))

        index = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        check(index.update() == 2, "update extracts both sessions")
        check(index.update() == 0, "second update re-extracts nothing")

        header, rows = next((h, r) for h, r in index.sessions() if h["session"] == SID)
        texts = [r["text"] for r in rows]
        joe = [r["text"] for r in rows if r.get("role") == "joe"]
        check(joe[0].startswith("Lets pick the vault design"), "Joe's typed turn is kept")
        check(not any("skill expansion" in t for t in texts), "isMeta turn is dropped")
        check(not any("peer relay" in t for t in texts), "daemon-meta relay behind zero-width chars is dropped")
        check(not any("injected hook text" in t for t in texts), "system-reminder block is stripped")
        check(any("[REDACTED:aws_akia]" in t for t in texts) and not any(AKIA in t for t in texts),
              "secret is redacted in the index")
        check("Bubble: chose the vault" in texts and "Plain assistant reply about vault" in texts,
              "send_message bubble and assistant text are kept")
        check(any(t == "[asked] Keep transcripts forever?" for t in texts), "question card text is kept")
        check(any(r["kind"] == "commit" and r["sha"] == "5a4b270" for r in rows), "commit line is captured")
        check(header["title"] == "Vault versus MCP" and header["repo"] == "demo", "title and repo in header")
        check(len(header["human_turns"]) == 2, "human_turns counts only Joe's two genuine turns")

        out = recall.cmd_search(index, ["vault", "mcp"], None, None, None, 10)
        check(out.startswith(recall.FENCE_OPEN) and out.rstrip().endswith(recall.FENCE_CLOSE),
              "search output is fenced as data")
        check(SID in out and SID_NEW not in out, "search requires every term in the session")
        check("(personal)" in out and "repo=demo" in out, "search hit cites repo and scope")

        act = json.loads(recall.cmd_activity(index, "2026-01-01", "2026-01-31", None, True))
        check(len(act) == 1 and act[0]["session"] == SID and len(act[0]["human_turns"]) == 2,
              "activity lists raw human-turn times in range")

        check(recall.compress_cutoff(datetime(2026, 3, 10)) == datetime(2026, 2, 1),
              "in March the cutoff is 1 February (January compressed, February raw)")
        check(recall.compress_cutoff(datetime(2026, 1, 1)) == datetime(2025, 12, 1),
              "cutoff wraps across a year boundary")

        dry = recall.cmd_compress(projects, archive, True, today=datetime(2026, 3, 10))
        check("2026-01" in dry and (projects / SLUG / f"{SID}.jsonl").exists(), "dry run reports and moves nothing")

        msg = recall.cmd_compress(projects, archive, False, today=datetime(2026, 3, 10))
        zpath = archive / "transcripts" / "2026-01.zip"
        check(zpath.exists(), f"January zip created ({msg})")
        with zipfile.ZipFile(zpath) as zf:
            names = set(zf.namelist())
        check(f"{SLUG}/{SID}.jsonl" in names and f"{SLUG}/{SID}/subagents/agent-a1.jsonl" in names,
              "transcript and its sidecar are both archived")
        check(not (projects / SLUG / f"{SID}.jsonl").exists() and not (projects / SLUG / SID).exists(),
              "archived originals and the emptied sidecar dir are removed")
        check((projects / SLUG / f"{SID_NEW}.jsonl").exists(), "a recent transcript stays raw")
        check((memory / "MEMORY.md").exists() and not any("memory" in n for n in names),
              "memory/ is never touched")
        check(not (archive / "compress.lock").exists(), "lock is released")

        index2 = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        index2.update()
        out2 = recall.cmd_search(index2, ["vault", "mcp"], None, None, None, 10)
        check(SID in out2, "an archived session is still searchable from the zip")

        again = recall.cmd_compress(projects, archive, False, today=datetime(2026, 3, 10))
        check(again.startswith("OK 0 file(s) due"), "a second compress run is a no-op")
        log_lines = (archive / recall.COMPRESS_LOG).read_text(encoding="utf-8").splitlines()
        check(len(log_lines) == 2 and all(" OK " in ln for ln in log_lines), "every real compress run is logged")
        check("Verified 2026-01.zip: ok" in msg, "a compress run re-verifies an archived zip")

        check(recall.health_warnings(archive) == [], "a fresh, healthy archive raises no warning")
        stale = recall.health_warnings(archive, now=datetime.now() + timedelta(days=10))
        check(any("last ran" in w for w in stale), "a compressor that stopped running is flagged")
        with (archive / recall.COMPRESS_LOG).open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat(timespec='seconds')} FAILED OSError: boom\n")
        check(any("failed" in w for w in recall.health_warnings(archive)), "a failed compressor run is flagged")

        # Corrupt the archived zip's data region, then let the rolling re-verify find it.
        zbytes = bytearray(zpath.read_bytes())
        for i in range(40, 80):
            zbytes[i] ^= 0xFF
        zpath.write_bytes(bytes(zbytes))
        check("CORRUPT" in recall._verify_one_zip(archive), "re-verification detects a corrupted zip")
        check(any("re-verification" in w for w in recall.health_warnings(archive)), "a corrupt zip is flagged")

        # A transcript deleted by something other than the compressor is logged as a loss.
        (projects / SLUG / f"{SID_NEW}.jsonl").unlink()
        index3 = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        index3.update()
        check(any("vanished" in w for w in recall.health_warnings(archive)), "an unarchived deletion is flagged")
        check((archive / "index" / "sessions" / f"{SID_NEW}.jsonl").exists(), "its index file survives the loss")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        projects, archive = root / "projects", root / "memory-archive"
        old = datetime(2026, 1, 10, 12).timestamp()
        write_session(projects, SID, transcript_lines(), mtime=old)
        full = recall.cmd_compress(projects, archive, False, today=datetime(2026, 3, 10), free_bytes=lambda: 0)
        check("Not enough free disk for: 2026-01" in full and (projects / SLUG / f"{SID}.jsonl").exists(),
              "a disk too full for the month skips it and keeps the originals")

        # A long transcript in a format the parser no longer understands extracts to nothing.
        write_session(projects, SID_NEW, [rec(type="turn_v2", body={"text": f"hello {i}"}) for i in range(60)],
                      sidecar=False)
        index4 = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        index4.update()
        check(any("format may have changed" in w for w in index4.warnings), "a format change is flagged")

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall recall tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
