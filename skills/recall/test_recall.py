"""Self-test for recall.py. Builds a throwaway projects/ + memory-archive/ pair in a temp
dir, so it never reads the real transcripts and runs on CI's bare Windows runner.

Run: python skills/recall/test_recall.py   (exit 0 = all pass)
"""

import io
import json
import os
import shutil
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


DIGEST_OLD = """## Done
- Compared the vault design with the MCP server
## Decided
- Use the vault design for cross-project memory
## Rejected
- MCP server for memory: needs a daemon and a second store
## Open
- Whether the zorbquux export is worth keeping
"""
DIGEST_NEW = """## Done
- Wrote the vault loader
## Decided
- Keep transcripts forever
## Rejected
- Nightly summarising model call: vault digests cost no extra call
## Open
- none
"""


def test_digests():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        projects, archive = root / "projects", root / "memory-archive"
        write_session(projects, SID, transcript_lines(), sidecar=False)
        write_session(projects, SID_NEW, [rec(type="user", timestamp="2026-03-02T10:00:00Z", cwd="C:/work/demo",
                                              message={"content": "recent march chat about vault"})], sidecar=False)
        index = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        index.update()
        ddir = archive / "digests"

        code, msg = recall.cmd_digest_save(index, SID, DIGEST_OLD, False)
        check(code == 0 and (ddir / f"{SID}.md").exists(), f"digest-save writes digests/<id>.md ({msg})")
        check([p.name for p in ddir.iterdir()] == [f"{SID}.md"], "the atomic write leaves no temp file behind")
        text = (ddir / f"{SID}.md").read_text(encoding="utf-8")
        check(SID in text and "repo" in text.lower() and "personal" in text and "2026-01-10" in text,
              "the digest header cites date, repo, scope and session id")
        before = text

        code, msg = recall.cmd_digest_save(index, SID, DIGEST_NEW, False)
        check(code != 0 and (ddir / f"{SID}.md").read_text(encoding="utf-8") == before and "--replace" in msg,
              "digest-save refuses to overwrite without --replace and keeps the file")
        code, _ = recall.cmd_digest_save(index, SID, DIGEST_NEW, True)
        check(code == 0 and "Keep transcripts forever" in (ddir / f"{SID}.md").read_text(encoding="utf-8"),
              "--replace overwrites")
        recall.cmd_digest_save(index, SID, DIGEST_OLD, True)

        code, _ = recall.cmd_digest_save(index, SID_NEW, "## Done\n- only one section\n", False)
        check(code != 0 and not (ddir / f"{SID_NEW}.md").exists(), "a digest missing a required section is rejected")
        code, _ = recall.cmd_digest_save(index, "not-a-session", DIGEST_NEW, False)
        check(code != 0, "an unknown session id is rejected")
        code, _ = recall.cmd_digest_save(index, "66666666", DIGEST_NEW, False)
        check(code == 0 and (ddir / f"{SID_NEW}.md").exists(), "a unique prefix resolves to the full session id")
        leaky = DIGEST_NEW.replace("Keep transcripts forever", "Stored key " + AKIA)
        recall.cmd_digest_save(index, SID_NEW, leaky, True)
        check(AKIA not in (ddir / f"{SID_NEW}.md").read_text(encoding="utf-8"), "secrets in a digest are redacted")
        recall.cmd_digest_save(index, SID_NEW, DIGEST_NEW, True)

        shown = recall.cmd_show(index, SID[:8], None, 40000)
        check("Use the vault design for cross-project memory" in shown
              and shown.index("Use the vault design") < shown.index("joe:"),
              "show prints a cached digest above the conversation")
        check(shown.startswith(recall.FENCE_OPEN) and shown.rstrip().endswith(recall.FENCE_CLOSE),
              "show with a digest stays inside the data fence")
        ddir.joinpath(f"{SID}.md").rename(ddir / "parked.tmp")
        bare = recall.cmd_show(index, SID[:8], None, 40000)
        check("digest-save" in bare and "No digest" in bare, "show nudges to write a digest when none exists")
        (ddir / "parked.tmp").rename(ddir / f"{SID}.md")

        out = recall.cmd_decisions(index, ["mcp"], None, 10)
        check(out.startswith(recall.FENCE_OPEN) and out.rstrip().endswith(recall.FENCE_CLOSE),
              "decisions output is fenced as data")
        check("MCP server for memory" in out and SID in out, "decisions matches a Rejected item and cites the session")
        check("repo=demo" in out and "(personal)" in out, "decisions cites repo and scope")
        check("0 decision" in recall.cmd_decisions(index, ["zorbquux"], None, 10),
              "decisions ignores the Open section")
        check("0 decision" in recall.cmd_decisions(index, ["compared"], None, 10)
              and "0 decision" in recall.cmd_decisions(index, ["loader"], None, 10),
              "decisions ignores the Done section")
        both = recall.cmd_decisions(index, ["vault"], None, 10)
        check(both.index(SID_NEW) < both.index(SID), "decisions lists the newest session first")
        check("Use the vault design" in both, "decisions matches a Decided item")
        check(SID not in recall.cmd_decisions(index, ["vault"], "nomatch", 10), "decisions honours --repo")

        snap = {p.name: p.read_bytes() for p in ddir.iterdir()}
        shutil.rmtree(archive / "index")
        rebuilt = recall.Index(projects, archive, scope_of=lambda cwd: "personal")
        check(rebuilt.update() == 2, "the index rebuilds from scratch after deletion")
        check({p.name: p.read_bytes() for p in ddir.iterdir()} == snap, "rebuilding the index leaves every digest intact")

        sys.stdin = io.StringIO(DIGEST_NEW)
        try:
            rc = recall.main(["--projects", str(projects), "--archive", str(archive), "digest-save", SID, "--replace"])
        finally:
            sys.stdin = sys.__stdin__
        check(rc == 0 and "Keep transcripts forever" in (ddir / f"{SID}.md").read_text(encoding="utf-8"),
              "the CLI reads the digest from stdin")


def memory_file(path, name, body, verified=None, superseded_by=None, modified=None, mtype="reference"):
    fm = ["---", f"name: {name}", f"description: about {name}"]
    if verified:
        fm.append(f"verified: {verified}")
    if superseded_by:
        fm.append(f"superseded_by: {superseded_by}")
    fm += ["metadata: ", "  node_type: memory", f"  type: {mtype}"]
    if modified:
        fm.append(f"  modified: {modified}T10:00:00.000Z")
    fm += ["---", "", body, ""]
    path.write_text("\n".join(fm), encoding="utf-8")


def test_memory():
    with tempfile.TemporaryDirectory() as tmp:
        mem = Path(tmp) / "memory"
        (mem / "archive").mkdir(parents=True)
        (mem / "MEMORY.md").write_text("- [zorb old](zorb_old.md) zorbquux\n", encoding="utf-8")
        memory_file(mem / "zorb_old.md", "zorb-old", "zorbquux flag is --fast", verified="2026-01-02",
                    superseded_by="zorb-new")
        memory_file(mem / "zorb_new.md", "zorb-new", "zorbquux flag is --quick", verified="2026-10-01")
        memory_file(mem / "plain.md", "plain", "unrelated fact", modified="2026-02-01")
        memory_file(mem / "archive" / "gone.md", "gone", "zorbquux archived")

        out = recall.cmd_memory(mem, ["zorbquux"], False, 10)
        check("zorb-new" in out and "zorb-old" not in out, "memory search excludes a superseded memory by default")
        check("gone" not in out and "MEMORY.md" not in out, "memory search skips archive/ and the index")
        out_all = recall.cmd_memory(mem, ["zorbquux"], True, 10)
        check("zorb-old" in out_all and "superseded by zorb-new" in out_all and "zorb-new" in out_all,
              "--all includes the superseded memory and shows its link")
        check((mem / "zorb_old.md").exists(), "a superseded memory stays on disk")
        out_both = recall.cmd_memory(mem, ["zorbquux", "quick"], False, 10)
        check("zorb-new" in out_both, "every term must match")
        check("verified 2026-10-01" in out, "a hit shows its verified date")

        today = datetime(2026, 10, 23)
        stale = recall.cmd_memory_stale(mem, 90, today)
        check("zorb-old" not in stale, "a superseded memory is not a stale candidate")
        check("zorb-new" not in stale, "a recently verified memory is not a stale candidate")
        check("plain" in stale and "no verified" in stale,
              "an unverified memory is aged by its modified date and labelled")
        check("1 verified, 1 unverified" in stale and "1 superseded" in stale, "stale listing reports counts")
        memory_file(mem / "aged.md", "aged", "old repro", verified="2026-03-01")
        check("aged" in recall.cmd_memory_stale(mem, 90, today), "an old verified memory is a stale candidate")
        check("aged" not in recall.cmd_memory_stale(mem, 365, today), "the age threshold is respected")

        # A frontmatter-less file must not crash the scan.
        (mem / "bare.md").write_text("no frontmatter at all\n", encoding="utf-8")
        recall.cmd_memory(mem, ["bare"], False, 10)
        recall.cmd_memory_stale(mem, 90, today)
        check(True, "a file without frontmatter is tolerated")


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

        # A new redaction format must re-extract sessions already in the index, or old
        # leaks stay searchable forever. The bumped version is left in place: the rest
        # of this run never compares it again.
        setattr(recall, "REDACTION_VERSION", getattr(recall, "REDACTION_VERSION", 0) + 1)
        check(index.update() == 2, "a bumped redaction version re-extracts every indexed session")
        check(index.update() == 0, "and the run after that is a no-op again")

        fake = "fakeword" + "1234"
        shaped = recall.redact(f"**2.** Log in. Password:\n\n> {fake}\n\nthen continue")
        check(fake not in shaped and "[REDACTED:labelled_password]" in shaped and "then continue" in shaped,
              "a value in a blockquote under a blank line after a Password: label is redacted")
        check(fake not in recall.redact(f"- **Lozinka:**\n`{fake}`"),
              "a bold list-item label with a backticked value is redacted")
        check(fake not in recall.redact(f"PIN:\n```\n{fake}\n```"),
              "a value inside a code fence under the label is redacted")
        prose = recall.redact("Password:\nthis next line is ordinary prose")
        check(prose == "Password:\nthis next line is ordinary prose", "prose with spaces after a label stays intact")
        unlabelled = recall.redact(f"Log in here\n\n> {fake}")
        check(unlabelled == f"Log in here\n\n> {fake}", "a short line after a line with no label stays intact")
        check(recall.redact("Password:\n\n" + "x" * 65) == "Password:\n\n" + "x" * 65,
              "a line over 64 chars after a label stays intact")
        check(recall.redact(f"Password:\n{fake}\nsecond line") == "Password:\n[REDACTED:labelled_password]\nsecond line",
              "only the first value line after a label is redacted")

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

    test_digests()
    test_memory()

    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall recall tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
