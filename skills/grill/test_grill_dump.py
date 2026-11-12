"""Self-test for grill_dump.py. Builds every input in a temp dir (transcripts, decisions logs,
digests, archives, git repos), so it never reads real data and runs on CI's bare Windows runner.

Run: python skills/grill/test_grill_dump.py   (exit 0 = all pass). pytest also collects it.
"""

import contextlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grill_dump  # noqa: E402

FIXTURES = HERE / "fixtures"
NOW = "2026-11-12T12:00:00+00:00"

MAIN = "11111111-0000-0000-0000-000000000001"
SUBCARD = "11111111-0000-0000-0000-000000000002"
SUBFIN = "11111111-0000-0000-0000-000000000003"
UNLOGGED = "11111111-0000-0000-0000-000000000004"
OUTSIDE = "11111111-0000-0000-0000-000000000005"
WORKTREE = "11111111-0000-0000-0000-000000000006"
PREFIX_TRAP = "11111111-0000-0000-0000-000000000007"
OLD = "11111111-0000-0000-0000-000000000008"
MISSING_SUB = "11111111-0000-0000-0000-000000000009"
GONE = "11111111-0000-0000-0000-000000000010"


def epoch(iso):
    return datetime.fromisoformat(iso).timestamp()


IN_WINDOW_MTIME = epoch("2026-10-20T12:00:00+00:00")
OLD_MTIME = epoch("2026-09-01T12:00:00+00:00")


# ---------------------------------------------------------------- helpers

def run_cli(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = grill_dump.main(args)
    return code, out.getvalue()


def joe(text, ts, cwd=None, origin="sdk", **extra):
    r = {"type": "user", "message": {"role": "user", "content": text}, "timestamp": ts}
    if origin is not None:
        r["promptSource"] = origin
        r["turnOrigin"] = origin
    if cwd is not None:
        r["cwd"] = cwd
    r.update(extra)
    return json.dumps(r)


def asst(mid, ts, inp=0, cw=0, cr=0, out=0):
    return json.dumps({
        "type": "assistant", "timestamp": ts,
        "message": {"id": mid, "role": "assistant", "content": [],
                    "usage": {"input_tokens": inp, "cache_creation_input_tokens": cw,
                              "cache_read_input_tokens": cr, "output_tokens": out}},
    })


def write_lines(path, lines, mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("".join(line + "\n" for line in lines))
    if mtime is not None:
        os.utime(path, (mtime, mtime))


def copy_fixture(name, dest, root=None):
    text = (FIXTURES / name).read_text(encoding="utf-8")
    if root is not None:
        text = text.replace("__ROOT__", str(root))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def git(repo, *args, date=None):
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    cmd = ["git", "-c", "user.name=grill-test", "-c", "user.email=grill@example.invalid",
           "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={Path(repo) / '.nohooks'}",
           "-c", "core.autocrlf=false", "-C", str(repo), *args]
    return subprocess.run(cmd, check=True, env=env, capture_output=True, text=True).stdout.strip()


def put(repo, rel, text="x\n"):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def commit(repo, msg, date):
    git(repo, "add", "-A", date=date)
    git(repo, "commit", "-q", "-m", msg, date=date)
    return git(repo, "rev-parse", "--short=7", "HEAD")


def read_jsonl(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return [json.loads(line) for line in fh.read().split("\n") if line.strip()]


def build_world(root):
    """The shared fixture world for tests 2, 4 and 5. Returns a dict of paths."""
    root = Path(root)
    scope = root / "demo-repo"
    projects = root / "projects"
    decisions = root / "decisions"
    digests = root / "digests"
    archive = root / "archive"
    proj = projects / "C--demo"
    s = str(scope)

    scope.mkdir(parents=True)
    git(scope, "init", "-q")
    put(scope, "README.md", "demo\n")
    commit(scope, "FEAT: start the demo", "2026-10-20T12:00:00+00:00")

    main_lines = [
        json.dumps({"type": "session-owner", "sessionId": MAIN}),
        json.dumps({"type": "queue-operation", "operation": "enqueue"}),
        joe("this is wrong, fix the layout", "2026-10-20T10:00:00Z", cwd=s),       # 3: cat 1
        joe("the old menu is wrong", "2026-09-01T10:00:00Z", cwd=s),               # 4: out of window
        asst("msg_a", "2026-10-20T10:01:00Z", 100, 1000, 10000, 50),
        asst("msg_a", "2026-10-20T10:01:30Z", 100, 1000, 10000, 60),
        joe("please revert that change", "2026-10-20T10:02:00Z", cwd=s),           # 7: cat 2
        joe("why did you delete the file", "2026-10-20T10:03:00Z", cwd=s),         # 8: cat 3
        joe("it keeps failing on start", "2026-10-20T10:04:00Z", cwd=s),           # 9: cat 4
        joe("the log is too noisy", "2026-10-20T10:05:00Z", cwd=s),                # 10: cat 5
        joe("that's not what I asked for", "2026-10-20T10:06:00Z", cwd=s),         # 11: cat 6
        joe("i don't need this panel", "2026-10-20T10:07:00Z", cwd=s),             # 12: cat 7
        joe("the build is wrong", "2026-10-20T10:08:00Z", cwd=s, origin="peer", isMeta=True),
        json.dumps({"type": "user", "timestamp": "2026-10-20T10:09:00Z", "promptSource": "sdk",
                    "message": {"role": "user",
                                "content": [{"type": "tool_result", "content": "wrong output"}]}}),
        joe("<system-reminder>this is broken</system-reminder>", "2026-10-20T10:10:00Z", cwd=s),
        joe("this is wrong", "2026-10-20T10:11:00Z", cwd=s, isSidechain=True),
        joe("it is still broken", "2026-10-20T10:12:00Z", cwd=s, origin=None),     # 17: cat 1
        asst("msg_z", "2026-10-20T10:13:00Z", 1, 0, 0, 1),
    ]
    write_lines(proj / f"{MAIN}.jsonl", main_lines, IN_WINDOW_MTIME)
    write_lines(proj / MAIN / "subagents" / "agent-x.jsonl",
                [asst("msg_b", "2026-10-20T10:05:00Z", 7, 0, 0, 3)], IN_WINDOW_MTIME)

    write_lines(proj / f"{SUBCARD}.jsonl", [
        joe("Job: the old exporter is wrong, rebuild it", "2026-10-22T09:00:00Z", cwd=s),
        joe("this is still wrong", "2026-10-22T09:05:00Z", cwd=s),
        asst("msg_c", "2026-10-22T09:06:00Z", 5, 0, 0, 5),
    ], IN_WINDOW_MTIME)
    write_lines(proj / f"{SUBFIN}.jsonl", [
        joe("Job: nested change, the menu is broken", "2026-10-24T09:00:00Z", cwd=s),
        asst("msg_d", "2026-10-24T09:01:00Z", 6, 0, 0, 6),
    ], IN_WINDOW_MTIME)
    # Case and slash variant of the scope path: matching must normalise both.
    write_lines(proj / f"{UNLOGGED}.jsonl", [
        joe("Brief: the old parser is wrong", "2026-10-25T09:00:00Z", cwd=s.upper().replace("\\", "/")),
        joe("thanks, looks good", "2026-10-25T09:02:00Z"),
        asst("msg_e", "2026-10-25T09:03:00Z", 4, 0, 0, 4),
    ], IN_WINDOW_MTIME)
    write_lines(proj / f"{OUTSIDE}.jsonl", [
        joe("this is wrong elsewhere", "2026-10-25T09:00:00Z", cwd=str(root / "other")),
        asst("msg_f", "2026-10-25T09:01:00Z", 9, 0, 0, 9),
    ], IN_WINDOW_MTIME)
    write_lines(proj / f"{PREFIX_TRAP}.jsonl", [
        joe("hello", "2026-10-25T09:00:00Z", cwd=str(root / "demo-repo-two")),
    ], IN_WINDOW_MTIME)
    write_lines(proj / f"{WORKTREE}.jsonl", [
        joe("Brief: hello", "2026-10-26T09:00:00Z", cwd=str(scope / ".claude" / "worktrees" / "wt1")),
        joe("this is annoying", "2026-10-26T09:01:00Z"),                           # 2: cat 5
        asst("msg_g", "2026-10-26T09:02:00Z", 3, 0, 0, 3),
    ], IN_WINDOW_MTIME)
    write_lines(proj / f"{OLD}.jsonl", [
        joe("this is wrong", "2026-09-01T09:00:00Z", cwd=s),
    ], OLD_MTIME)

    copy_fixture("main.decisions.md", decisions / f"{MAIN}.decisions.md")
    copy_fixture("subcard.decisions.md", decisions / f"{SUBCARD}.decisions.md")
    # A main chat whose transcript is gone: its card entries are dropped with a warning, not counted.
    (decisions / f"{GONE}.decisions.md").write_text(
        "# Decisions log\n\n## D1 - card - 2026-10-21 - main chat\nQuestion: Ship dark mode?\nAnswer: Yes\n"
        "\n## D2 - card - 2026-10-22 - main chat\nQuestion: Ship light mode?\nAnswer: Yes\n", encoding="utf-8")
    (decisions / f"{MAIN}.digest.md").write_text("not a decisions log\n", encoding="utf-8")
    copy_fixture("digest-weekly.md", digests / f"{MAIN}.md")
    copy_fixture("digest-archive.md", digests / "99999999-0000-0000-0000-000000000001.md")
    copy_fixture("digest-old.md", digests / "88888888-0000-0000-0000-000000000001.md")
    copy_fixture("digest-nowhere.md", digests / "99999999-0000-0000-0000-000000000002.md")

    copy_fixture("archive-demo-new.md", archive / "demo-repo" / "2026-10-15.md", root)
    copy_fixture("archive-demo-old.md", archive / "demo-repo" / "2026-09-15.md", root)
    put(scope, ".claude/todos/pc-0001-sidebar-cost.md", "# todo\n")
    put(root / ".claude", ".claude/todos/done/pc-0002-backup.md", "# todo\n")

    return {"root": root, "scope": scope, "projects": projects, "decisions": decisions,
            "digests": digests, "archive": archive, "proj": proj}


def dump_world(w, out, *extra):
    args = ["dump", "--scope", str(w["scope"]), "--now", NOW, "--out", str(out),
            "--projects-dir", str(w["projects"]), "--decisions-dir", str(w["decisions"]),
            "--digests-dir", str(w["digests"]), "--archive-dir", str(w["archive"]), *extra]
    return run_cli(args)


@contextlib.contextmanager
def tmpdir():
    d = tempfile.mkdtemp(prefix="grill-test-")
    try:
        yield Path(d)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------- 1. parse_decisions

def test_parse_decisions():
    path = FIXTURES / "main.decisions.md"
    entries = grill_dump.parse_decisions(path.read_text(encoding="utf-8"), str(path))
    by_n = {e["n"]: e for e in entries}
    assert sorted(by_n) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    d1 = by_n[1]
    assert d1["kind"] == "card" and d1["date"] == "2026-10-20" and d1["label"] == "main chat"
    assert d1["sub"] is None
    assert d1["question"] == "Should the sidebar dashboard show token cost per chat kind?"
    assert d1["answer"] == "Yes, show cost per chat kind\nin the sidebar dashboard"
    assert d1["ref"] == f"{path}#D1"
    assert by_n[2]["sub"] == SUBCARD and by_n[2]["label"] == "alpha-sub"
    assert by_n[5]["kind"] == "finish" and by_n[5]["decided"] == "Group release notes commits by ticket number"
    assert by_n[6]["superseded"] is True and by_n[7]["superseded"] is False


# ---------------------------------------------------------------- 2. scope and kind (dump)

def test_dump_scope_kind_window():
    with tmpdir() as root:
        w = build_world(root)
        out = root / "run"
        code, _ = dump_world(w, out)
        assert code == 0
        chats = {c["session"]: c for c in read_jsonl(out / "chats.jsonl")}
        # First-cwd rule, case/slash match, worktree match; outside, prefix trap and old file excluded.
        assert set(chats) == {MAIN, SUBCARD, SUBFIN, UNLOGGED, WORKTREE}
        assert chats[MAIN]["kind"] == "main"
        assert chats[SUBCARD]["kind"] == "sub-with-card"       # also a decisions-log stem
        assert chats[SUBFIN]["kind"] == "sub-without-card"
        assert chats[UNLOGGED]["kind"] == "main"
        assert chats[WORKTREE]["kind"] == "main"
        assert all(c["scope"] == str(w["scope"]) for c in chats.values())
        # Subagent usage summed into the parent, message.id deduped (last record wins).
        assert chats[MAIN]["input"] == 108 and chats[MAIN]["output"] == 64
        assert chats[MAIN]["cache_write"] == 1000 and chats[MAIN]["cache_read"] == 10000
        assert chats[MAIN]["input_equiv"] == 2678

        clusters = read_jsonl(out / "clusters.jsonl")
        refs = {e["ref"] for c in clusters for e in c["entries"]}
        dec = str(w["decisions"] / f"{MAIN}.decisions.md")
        weekly = str(w["digests"] / f"{MAIN}.md")
        fallback = str(w["digests"] / "99999999-0000-0000-0000-000000000001.md")
        assert f"{weekly}#0" in refs and f"{weekly}#1" in refs        # Session: line scope
        assert f"{fallback}#0" in refs                                # Repo: fallback
        assert f"{dec}#D9" not in refs                                # entry out of window
        assert not any("88888888" in r for r in refs)                 # digest out of window
        assert f"{dec}#D8" not in refs                                # Sub: transcript missing
        assert all(c["scope"] == str(w["scope"]) for c in clusters)

        complaints = read_jsonl(out / "complaints.jsonl")
        assert not any(c["text"].startswith("the old menu") for c in complaints)   # Joe turn out of window

        summary = (out / "summary.md").read_text(encoding="utf-8")
        assert "Window: 2026-10-13 to 2026-11-12 (30 days)" in summary
        assert "in-window chats outside the scope (or unmatched): 3" in summary
        assert "`Sub:` uuids with no transcript: 1" in summary
        assert "1 decisions log(s) whose main chat transcript is gone" in summary and GONE in summary

        for name in ("chats", "clusters", "complaints", "git", "phase0"):
            raw = (out / f"{name}.jsonl").read_bytes()
            assert raw, f"{name}.jsonl is empty"
            assert all(b < 128 for b in raw), f"{name}.jsonl is not ASCII"
            assert b"\r" not in raw, f"{name}.jsonl has CR"

        # The window start follows --now: a later now drops D1 (2026-10-20).
        out2 = root / "run2"
        dump_world(w, out2, "--now", "2026-11-25T12:00:00+00:00")
        refs2 = {e["ref"] for c in read_jsonl(out2 / "clusters.jsonl") for e in c["entries"]}
        assert f"{dec}#D1" not in refs2 and f"{dec}#D7" in refs2
        assert "Window: 2026-10-26 to 2026-11-25 (30 days)" in (out2 / "summary.md").read_text(encoding="utf-8")


def test_chat_kind():
    card, finish = {SUBCARD}, {SUBFIN, SUBCARD}
    assert grill_dump.chat_kind(SUBCARD, card, finish) == "sub-with-card"
    assert grill_dump.chat_kind(SUBFIN, card, finish) == "sub-without-card"
    assert grill_dump.chat_kind(MAIN, card, finish) == "main"


# ---------------------------------------------------------------- 3. sum_usage

def test_sum_usage():
    parent = [
        asst("m1", "2026-10-20T10:00:00Z", 10, 100, 1000, 5),
        asst("m1", "2026-10-20T10:00:30Z", 10, 100, 1000, 7),
        asst("m2", "2026-10-20T10:01:00Z", 1, 0, 0, 1),
        json.dumps({"type": "system", "timestamp": "2026-10-20T10:12:40Z"}),   # 700 s gap: idle
        json.dumps({"type": "system", "timestamp": "2026-10-20T10:14:20Z"}),
        "not json at all",
    ]
    sub = [[asst("m3", "2026-10-20T10:00:10Z", 2, 0, 0, 2)]]
    r = grill_dump.sum_usage(parent, sub)
    assert (r["input"], r["cache_write"], r["cache_read"], r["output"]) == (13, 100, 1000, 10)
    assert r["input_equiv"] == 13 + 125 + 100 + 50
    assert r["wall_s"] == 160
    assert r["first_ts"].startswith("2026-10-20T10:00:00") and r["last_ts"].startswith("2026-10-20T10:14:20")


# ---------------------------------------------------------------- 4. clustering

def entry(ref, date, q, a="", scope="S", superseded=False, source="card"):
    return {"source": source, "ref": ref, "date": date, "question": q, "answer": a,
            "superseded": superseded, "scope": scope}


def test_cluster_on_dump():
    with tmpdir() as root:
        w = build_world(root)
        out = root / "run"
        dump_world(w, out)
        dec = str(w["decisions"] / f"{MAIN}.decisions.md")
        clusters = {c["id"]: c for c in read_jsonl(out / "clusters.jsonl")}
        assert len(clusters) == 7
        rel = clusters[f"{dec}#D2"]
        assert [e["ref"] for e in rel["entries"]] == [f"{dec}#D2", f"{dec}#D3"]   # labels differ, finish D5 excluded
        assert rel["size"] == 2 and rel["revisits"] == 1 and rel["reversed"] is False
        assert f"{dec}#D4" in clusters and f"{dec}#D1" in clusters               # dissimilar stays apart
        backup = clusters[f"{dec}#D6"]
        assert backup["revisits"] == 2 and backup["reversed"] is True and backup["examined"] is False
        assert backup["rank"] == 1 and rel["rank"] == 2
        assert sum(c["examined"] for c in clusters.values()) == 6
        assert sorted(c["rank"] for c in clusters.values()) == list(range(1, 8))

        summary = (out / "summary.md").read_text(encoding="utf-8")
        reversed_part = summary.split("### Reversed, not examined")[1].split("## ")[0]
        assert "revisits 2: Should the backup job retry uploads overnight?" in reversed_part

        out2 = root / "run2"
        dump_world(w, out2, "--include-refs", f"{MAIN}#D6,{MAIN}#D9")
        c2 = {c["id"]: c for c in read_jsonl(out2 / "clusters.jsonl")}
        assert c2[f"{dec}#D6"]["examined"] is True and c2[f"{dec}#D6"]["reversed"] is True
        summary2 = (out2 / "summary.md").read_text(encoding="utf-8")
        assert f"--include-refs {dec}#D9 matched no in-window, in-scope card entry" in summary2   # D9 is out of window
        assert f"--include-refs {dec}#D6 matched" not in summary2


def test_cluster_jaccard_rules():
    es = [
        entry("r#1", "2026-10-01", "aaa bbb"),
        entry("r#2", "2026-10-02", "aaa bbb ccc ddd"),             # Jaccard exactly 0.5: merges
        entry("r#3", "2026-10-03", "zzz yyy the and should"),      # stop words dropped
        entry("r#4", "2026-10-04", "zzz yyy ab cd"),               # short tokens dropped: equal sets
        entry("r#5", "2026-10-05", "qqq www eee rrr ttt"),
    ]
    cs = {c["id"]: c for c in grill_dump.cluster(es)}
    assert [e["ref"] for e in cs["r#1"]["entries"]] == ["r#1", "r#2"]
    assert [e["ref"] for e in cs["r#3"]["entries"]] == ["r#3", "r#4"]
    assert "r#5" in cs and len(cs) == 3


def test_cluster_first_not_best():
    es = [
        entry("a#1", "2026-10-01", "aaa bbb xxx"),
        entry("b#1", "2026-10-02", "aaa bbb ccc zzz"),     # 2/5 vs a#1: separate cluster
        entry("e#1", "2026-10-03", "aaa bbb ccc"),         # 0.5 vs a#1 (first), 0.75 vs b#1 (best)
    ]
    cs = {c["id"]: c for c in grill_dump.cluster(es)}
    assert [e["ref"] for e in cs["a#1"]["entries"]] == ["a#1", "e#1"]
    assert [e["ref"] for e in cs["b#1"]["entries"]] == ["b#1"]


def test_cluster_cap_and_rank():
    es = []
    for i in range(45):
        es.append(entry(f"x#{i:02d}", f"2026-10-{1 + i % 28:02d}", f"tq{i:02d}a tq{i:02d}b tq{i:02d}c"))
    # One reversed cluster with the most revisits: ranked first, never examined unless included.
    es.append(entry("rev#1", "2026-10-01", "rva rvb rvc", superseded=True))
    es.append(entry("rev#2", "2026-10-20", "rva rvb rvc"))
    cs = grill_dump.cluster(es)
    assert len(cs) == 46
    by_rank = sorted(cs, key=lambda c: c["rank"])
    assert by_rank[0]["id"] == "rev#1" and by_rank[0]["examined"] is False
    examined = [c for c in by_rank if c["examined"]]
    assert len(examined) == 40
    assert examined == [c for c in by_rank if not c["reversed"]][:40]

    cs2 = {c["id"]: c for c in grill_dump.cluster(es, include_refs=("rev#2",))}
    assert cs2["rev#1"]["examined"] is True
    assert sum(c["examined"] for c in cs2.values()) == 40
    lowest = max(cs2.values(), key=lambda c: c["rank"])
    assert lowest["examined"] is False


def test_cluster_cap_is_global():
    es = []
    for scope in ("S1", "S2"):
        for i in range(30):
            es.append(entry(f"{scope}#{i:02d}", "2026-10-05", f"{scope}q{i:02d}a {scope}q{i:02d}b", scope=scope))
    cs = grill_dump.cluster(es)
    assert len(cs) == 60
    assert sum(c["examined"] for c in cs) == 40
    assert sorted(c["rank"] for c in cs) == list(range(1, 61))


# ---------------------------------------------------------------- 5. complaints

def test_complaint_hits():
    with tmpdir() as root:
        w = build_world(root)
        start = datetime(2026, 10, 13, tzinfo=timezone.utc)
        end = datetime.fromisoformat(NOW)
        main_path = w["proj"] / f"{MAIN}.jsonl"
        hits = grill_dump.complaint_hits(str(main_path), "S", start, end, True)
        got = sorted((h["category"], h["line"]) for h in hits)
        assert got == [(1, 3), (1, 17), (2, 7), (3, 8), (4, 9), (5, 10), (6, 11), (7, 12)]
        assert all(h["session"] == MAIN and h["scope"] == "S" and h["file"] == str(main_path) for h in hits)
        # Not a decisions-log stem: the first qualifying turn (a possible sub brief) is dropped.
        brief = grill_dump.complaint_hits(str(w["proj"] / f"{UNLOGGED}.jsonl"), "S", start, end, False)
        assert brief == []
        wt = grill_dump.complaint_hits(str(w["proj"] / f"{WORKTREE}.jsonl"), "S", start, end, False)
        assert [(h["category"], h["line"]) for h in wt] == [(5, 2)]
        # The first turn is consumed as the possible brief even when it falls outside the window.
        late = root / "late.jsonl"
        write_lines(late, [joe("old brief, this is wrong", "2026-09-01T09:00:00Z"),
                           joe("this is useless", "2026-10-20T09:00:00Z"),
                           joe("i do not read that", "2026-10-20T09:01:00Z")])
        got = grill_dump.complaint_hits(str(late), "S", start, end, False)
        assert [(h["category"], h["line"]) for h in got] == [(5, 2), (7, 3)]

        out = root / "run"
        dump_world(w, out)
        sessions = {c["session"] for c in read_jsonl(out / "complaints.jsonl")}
        assert sessions == {MAIN, WORKTREE}     # logged subs and the unlogged brief give nothing


# ---------------------------------------------------------------- 6. git outcome

def test_git_outcome():
    with tmpdir() as root:
        repo = root / "gitrepo"
        repo.mkdir()
        git(repo, "init", "-q")
        put(repo, "src/app/widget.py")
        put(repo, "src/app/lonely.py")
        put(repo, "src/app/old.py")
        put(repo, "README.md")
        c1 = commit(repo, "FEAT: add widget", "2026-10-01T12:00:00+00:00")
        put(repo, "src/app/widget.py", "fix 1\n")
        c2 = commit(repo, "FIX: widget crash", "2026-10-21T12:00:00+00:00")
        put(repo, "src/app/widget.py", "fix 2\n")
        c3 = commit(repo, "FIX: widget again", "2026-10-23T12:00:00+00:00")
        put(repo, "src/app/widget.py", "fix 1\n")
        commit(repo, 'Revert "FIX: widget again"', "2026-10-24T12:00:00+00:00")
        put(repo, "docs/notes/temp.md")
        commit(repo, "DATA: tweak copy", "2026-10-25T12:00:00+00:00")
        os.remove(repo / "docs" / "notes" / "temp.md")
        commit(repo, "tidy up things", "2026-10-26T12:00:00+00:00")
        git(repo, "mv", "src/app/old.py", "src/app/new.py")
        commit(repo, "CHORE: rename old", "2026-10-27T12:00:00+00:00")

        rows = {r["group"]: r for r in grill_dump.git_outcome(str(repo), "2026-09-25T00:00:00")}
        app = rows["src/app"]
        assert app["repo"] == str(repo)
        assert (app["total"], app["feat"], app["fix"], app["revert"], app["ignored"], app["unclassified"]) == (5, 1, 2, 1, 1, 0)
        assert app["later_fix_links"] == [f"{c1}->{c2}"]
        assert f"{c1}->{c3}" not in app["later_fix_links"]
        assert app["never_touched"] == ["src/app/lonely.py"]
        assert app["added_then_deleted"] == ["src/app/old.py"]
        docs = rows["docs/notes"]
        assert (docs["total"], docs["ignored"], docs["unclassified"]) == (2, 1, 1)
        assert docs["added_then_deleted"] == ["docs/notes/temp.md"]
        assert rows["README.md"]["feat"] == 1 and rows["README.md"]["never_touched"] == ["README.md"]


def test_git_top_15_groups():
    with tmpdir() as root:
        repo = root / "many"
        repo.mkdir()
        git(repo, "init", "-q")
        for i in range(1, 18):
            put(repo, f"g{i:02d}/sub/a.txt")
        commit(repo, "FEAT: all groups", "2026-10-01T00:00:00+00:00")
        for i in range(1, 17):
            put(repo, f"g{i:02d}/sub/a.txt", f"v{i}\n")
            commit(repo, f"FIX: g{i:02d}", f"2026-10-02T{i:02d}:00:00+00:00")
        rows = grill_dump.git_outcome(str(repo), "2026-09-25T00:00:00")
        assert [r["group"] for r in rows] == [f"g{i:02d}/sub" for i in range(1, 16)]
        assert all(r["total"] == 2 for r in rows)
        out = root / "run"
        run_cli(["dump", "--scope", str(repo), "--now", NOW, "--days", "60", "--out", str(out),
                 "--projects-dir", str(root / "none"), "--decisions-dir", str(root / "none"),
                 "--digests-dir", str(root / "none"), "--archive-dir", str(root / "none")])
        assert len(read_jsonl(out / "git.jsonl")) == 15
        git_part = (out / "summary.md").read_text(encoding="utf-8").split("## L4")[1].split("## ")[0]
        assert git_part.count("git.jsonl:") == 15 and "2 more not shown (path groups)" in git_part


# ---------------------------------------------------------------- 7. phase 0

def test_phase0():
    with tmpdir() as root:
        archive = root / "archive"
        demo = root / "demo-repo"
        tool2 = root / "tool2"
        dotclaude = root / ".claude"
        copy_fixture("archive-demo-new.md", archive / "demo-repo" / "2026-10-15.md", root)
        copy_fixture("archive-demo-old.md", archive / "demo-repo" / "2026-09-15.md", root)
        copy_fixture("archive-tool2-new.md", archive / "tool2" / "2026-10-01.md", root)
        copy_fixture("archive-tool2-old.md", archive / "tool2" / "2026-08-01.md", root)
        copy_fixture("archive-tool2-new.md", archive / "claude-tooling" / "2026-10-01.md", root)
        put(demo, ".claude/todos/pc-0001-sidebar-cost.md")
        put(dotclaude, ".claude/todos/done/pc-0002-backup.md")
        tool2.mkdir()

        rows = grill_dump.phase0(str(archive), [str(demo), str(tool2)])
        got = {(r["scope"], r["slug"]): r for r in rows}
        d = str(demo)
        assert set(got) == {(d, s) for s in ("a-picked-open", "b-picked-closed", "c-picked-missing",
                                             "d-unknown-repo", "e-declined-once", "f-declined-twice",
                                             "g-not-shown")} | {(str(tool2), "t-new")}
        assert got[(d, "a-picked-open")]["state"] == "open"
        assert got[(d, "a-picked-open")]["surface"] == "sidebar"
        assert got[(d, "a-picked-open")]["todo"] == f"{demo}:pc-0001"
        assert got[(d, "b-picked-closed")]["state"] == "closed"
        assert got[(d, "c-picked-missing")]["state"] == "missing"
        assert got[(d, "d-unknown-repo")]["state"] == "missing"
        assert grill_dump._todo_state(f"{demo}:pc") == "missing"            # an id prefix is not a match
        e, f, g = got[(d, "e-declined-once")], got[(d, "f-declined-twice")], got[(d, "g-not-shown")]
        warned = []
        grill_dump.phase0(str(archive), [str(demo)], warned)
        assert warned == []
        assert (e["state"], e["declined"], e["never_raise"]) == ("not-picked", 1, False)
        assert (f["declined"], f["never_raise"]) == (2, True)
        assert (g["declined"], g["never_raise"]) == (1, False)

        tooling = grill_dump.phase0(str(archive), [str(dotclaude)])
        assert [r["slug"] for r in tooling] == ["t-new"]


def test_parse_archive_table_tolerant():
    text = ("intro\n\n|  slug | surface  | tag | lane | verdict | joe | todo | declined |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| pipe-slug | sidebar \\| footer | PRODUCT | L2 | survives | declined |  | 1 |\n"
            "| short | row |\n")
    skipped = []
    rows = grill_dump.parse_archive_table(text, skipped)
    assert [(r["slug"], r["surface"], r["declined"]) for r in rows] == [("pipe-slug", "sidebar | footer", "1")]
    assert skipped == ["| short | row |"]
    with tmpdir() as root:
        put(root / "archive" / "demo", "2026-10-01.md", "| no | table |\n")
        warnings = []
        assert grill_dump.phase0(str(root / "archive"), [str(root / "demo"), str(root / "x" / "demo")], warnings) == []
        assert any("no archive table rows" in w for w in warnings)
        assert any("share the archive slug 'demo'" in w for w in warnings)
        put(root / "archive" / "odd", "2026-10-01.md",
            "| slug | surface | tag | lane | verdict | joe | todo | declined |\n|---|---|---|---|---|---|---|---|\n"
            "| odd-row | menu | PRODUCT | L2 | survives | declined |  | two |\n")
        warnings = []
        rows = grill_dump.phase0(str(root / "archive"), [str(root / "odd")], warnings)
        assert [(r["slug"], r["declined"]) for r in rows] == [("odd-row", 0)]
        assert any("non-numeric declined" in w for w in warnings)


# ---------------------------------------------------------------- 8. summary.md caps

def test_summary_caps():
    with tmpdir() as root:
        scope = root / "big-repo"
        scope.mkdir()
        projects, decisions = root / "projects", root / "decisions"
        uuids = [f"22222222-0000-0000-0000-{i:012d}" for i in range(25)]
        for i, u in enumerate(uuids):
            # uuids[0] is the decisions-log stem, so its first turn is Joe's and is a complaint too.
            first = "this is wrong from the start" if i == 0 else "hello there"
            write_lines(projects / "C--big" / f"{u}.jsonl", [
                joe(first, "2026-10-20T09:00:00Z", cwd=str(scope)),
                joe("this is wrong", f"2026-10-20T09:{i + 1:02d}:00Z", cwd=str(scope)),
                asst(f"m{i}", "2026-10-20T09:30:00Z", 10 + i, 0, 0, 1),
            ], IN_WINDOW_MTIME)
        lines = ["# Decisions log", ""]
        for i in range(47):
            lines += [f"## D{i + 1} - card - 2026-10-20 - main chat",
                      f"Question: tq{i:02d}a tq{i:02d}b?", f"Answer: tq{i:02d}c", ""]
        decisions.mkdir()
        (decisions / f"{uuids[0]}.decisions.md").write_text("\n".join(lines), encoding="utf-8")
        out = root / "run"
        code, _ = run_cli(["dump", "--scope", str(scope), "--now", NOW, "--out", str(out),
                           "--projects-dir", str(projects), "--decisions-dir", str(decisions),
                           "--digests-dir", str(root / "nodigests"), "--archive-dir", str(root / "noarchive")])
        assert code == 0
        summary = (out / "summary.md").read_text(encoding="utf-8")
        assert len(read_jsonl(out / "chats.jsonl")) == 25
        assert len(read_jsonl(out / "complaints.jsonl")) == 26        # the stem's first turn counts too
        assert f"| {scope} | main | 25 |" in summary                   # totals cover the cut chats
        chat_section = summary.split("## L1")[1].split("## ")[0]
        assert chat_section.count("chats.jsonl:") == 20 and "5 more not shown" in chat_section
        cluster_section = summary.split("## L2")[1].split("## ")[0]
        assert cluster_section.count("clusters.jsonl:") == 40
        assert "7 more not shown (not examined)" in cluster_section
        complaint_section = summary.split("## L5")[1].split("## ")[0]
        assert complaint_section.count("complaints.jsonl:") == 20 and "6 more not shown" in complaint_section
        assert f"git log failed for {scope}" in summary                  # not a repo: said, not silent


# ---------------------------------------------------------------- 9. check-receipts

def test_check_receipts():
    with tmpdir() as root:
        plain = root / "plain.txt"
        plain.write_text("first line of evidence\nsecond line of evidence\n", encoding="utf-8")
        esc = root / "esc.jsonl"
        write_lines(esc, [json.dumps({"path": "C:\\Users\\demo\\x"})])
        crlf = root / "crlf.txt"
        crlf.write_bytes(b"alpha line here\r\nsecond crlf line here\r\n")

        def rc(f, line, quote):
            return {"file": str(f), "line": line, "quote": quote}

        rows = [
            {"slug": "good", "receipt": rc(plain, 2, "second line of")},
            {"slug": "escaped", "receipt": rc(esc, 1, "C:\\\\Users\\\\demo")},
            {"slug": "crlf", "receipt": rc(crlf, 2, "second crlf line")},
            {"slug": "fab", "receipt": rc(plain, 50, "second line of")},
            {"slug": "offline", "receipt": rc(plain, 1, "second line of")},
            {"slug": "short", "receipt": rc(plain, 1, "first l")},
            {"slug": "badalt", "receipt": rc(plain, 1, "first line of"), "alt_receipt": rc(plain, 9, "nothing here")},
            {"slug": "none", "receipt": {"none_searched": "searched the whole repo"}},
            {"slug": "missing"},
        ]
        rows_path = root / "rows.jsonl"
        write_lines(rows_path, [json.dumps(r) for r in rows])
        code, out = run_cli(["check-receipts", str(rows_path)])
        lines = out.splitlines()
        assert code == 1
        for slug in ("good", "escaped", "crlf"):
            assert f"OK {slug}" in lines, slug
        for slug in ("fab", "offline", "short", "badalt", "none", "missing"):
            assert any(line.startswith(f"BAD {slug} ") for line in lines), slug

        ok_path = root / "ok.jsonl"
        write_lines(ok_path, [json.dumps(rows[0]), json.dumps(rows[2])])
        code, out = run_cli(["check-receipts", str(ok_path)])
        assert code == 0 and out.splitlines() == ["OK good", "OK crlf"]


# ---------------------------------------------------------------- 10. gate

class GateWorld:
    def __init__(self, root):
        self.root = root
        self.run = root / "run"
        self.scope = root / "scope"
        self.projects = root / "projects"
        self.dec = root / "decisions" / "x.decisions.md"
        self.run.mkdir()
        self.scope.mkdir()
        self.dec.parent.mkdir()
        self.dec.write_text("# log\n\n## D1 - card - 2026-10-20 - main chat\nQuestion: keep the sidebar wide?\n"
                            "Answer: yes keep it wide\n", encoding="utf-8")
        self.evidence = self.run / "l3_0.jsonl"
        write_lines(self.evidence, [json.dumps({"measurement": "median wait of a question sub", "value": 42})])
        self.transcript = self.projects / "C--x" / "abc.jsonl"
        write_lines(self.transcript, [json.dumps({"type": "user", "message": {"content": "keep the sidebar narrow"}})])
        self.unrelated = root / "unrelated" / "x.txt"
        self.unrelated.parent.mkdir()
        self.unrelated.write_text("an unrelated line of text\n", encoding="utf-8")
        self.write_clusters(3)

    def write_clusters(self, n, examined=True):
        self.ids = [f"{self.dec}#D{i + 1}" for i in range(n)]
        recs = [{"id": cid, "scope": str(self.scope), "rank": i + 1, "examined": examined,
                 "entries": [{"ref": cid}]} for i, cid in enumerate(self.ids)]
        recs.append({"id": f"{self.dec}#D99", "scope": str(self.scope), "rank": n + 1, "examined": False,
                     "entries": [{"ref": f"{self.dec}#D99"}]})
        write_lines(self.run / "clusters.jsonl", [json.dumps(r) for r in recs])

    def ev(self):
        return {"file": str(self.evidence), "line": 1, "quote": "median wait of a question sub"}

    def row(self, i, verdict="KEEP", **kw):
        r = {"slug": f"slug-{i}", "cluster": self.ids[i], "scope": str(self.scope), "surface": "sidebar",
             "decision": f"keep the sidebar wide number {i}", "alternative": f"make the sidebar collapsible {i}",
             "receipt": self.ev(), "verdict": verdict,
             "why_fails": f"collapsing hides the cost column that Joe reads daily, case {i}"}
        if verdict != "KEEP":
            r.pop("why_fails")
        r.update(kw)
        return r

    def valid(self):
        return [
            self.row(0, alt_receipt={"file": str(self.dec), "line": 4, "quote": "keep the sidebar wide"}),
            self.row(1, receipt={"none_searched": "searched git log and todos for revisits"}),
            self.row(2, verdict="CHANGE-CANDIDATE"),
        ]

    def gate(self, rows, *extra):
        p = self.run / "l2_rows.jsonl"
        write_lines(p, [json.dumps(r) for r in rows])
        return run_cli(["gate", str(p), "--clusters", str(self.run / "clusters.jsonl"),
                        "--scope", str(self.scope), "--projects-dir", str(self.projects), *extra])


def rules_hit(out):
    return {int(line.split()[2]) for line in out.splitlines() if line.startswith("FAIL rule ")}


def test_gate_green_and_passing_variants():
    with tmpdir() as root:
        g = GateWorld(root)
        code, out = g.gate(g.valid())
        assert code == 0 and "KEEP=2 CHANGE=1" in out.splitlines(), out
        # CHANGE receipt in its cluster's decisions log, and in a transcript.
        for rec in ({"file": str(g.dec), "line": 4, "quote": "Question: keep the sidebar"},
                    {"file": str(g.transcript), "line": 1, "quote": "keep the sidebar narrow"}):
            rows = g.valid()
            rows[2]["receipt"] = rec
            code, out = g.gate(rows)
            assert code == 0 and "KEEP=2 CHANGE=1" in out.splitlines(), out
        rows = g.valid()
        rows[1]["alt_receipt"] = None                                       # optional, sent as null
        code, out = g.gate(rows)
        assert code == 0 and "KEEP=2 CHANGE=1" in out.splitlines(), out


def red(g, rows, rule, *extra):
    code, out = g.gate(rows, *extra)
    assert code == 1, out
    assert rules_hit(out) == {rule}, out


def test_gate_rule1_row_set():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        red(g, [rows[0], rows[2]], 1)                                      # missing examined cluster
        dup = g.row(0, why_fails="a second distinct reason that is long enough")
        red(g, rows + [dup], 1)                                            # duplicate cluster


def test_gate_rule2_required():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        del rows[0]["receipt"]
        red(g, rows, 2)
        rows = g.valid()
        rows[0]["alternative"] = "Keep the sidebar wide, number 0!"
        red(g, rows, 2)                                                    # alternative == decision
        rows = g.valid()
        rows[0]["decision"] = ""
        red(g, rows, 2)
        rows = g.valid()
        rows[0]["decision"] = None
        rows[0]["alternative"] = None
        red(g, rows, 2)                                                    # null is not text
        rows = g.valid()
        rows[0]["slug"] = None
        red(g, rows, 2)


def test_gate_rule3_verdict():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        rows[0]["verdict"] = "MAYBE"
        rows[0].pop("why_fails")
        red(g, rows, 3)


def test_gate_rule4_shape():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        rows[0]["receipt"] = dict(g.ev(), quote="")
        red(g, rows, 4)
        rows = g.valid()
        rows[2]["receipt"] = {"none_searched": "searched git log and todos"}
        red(g, rows, 4)                                                    # none_searched on a CHANGE row
        rows = g.valid()
        rows[0]["receipt"] = dict(g.ev(), file="run/l3_0.jsonl")
        red(g, rows, 4)                                                    # relative file


def test_gate_rule5_content():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        rows[2]["receipt"] = {"file": str(g.unrelated), "line": 1, "quote": "an unrelated line"}
        red(g, rows, 5)
        rows = g.valid()
        rows[2]["cluster"] = ["not", "a", "string"]
        rows[2]["receipt"] = {"file": str(g.dec), "line": 4, "quote": "Question: keep the sidebar"}
        code, out = g.gate(rows)
        assert code == 1 and rules_hit(out) == {1, 2, 5}, out              # flagged, never a crash
        rows = g.valid()
        rows[2]["receipt"] = {"file": str(g.run / "clusters.jsonl"), "line": 1, "quote": '"examined": true'}
        red(g, rows, 5)
        rows = g.valid()
        rows[2]["receipt"] = {"file": str(g.scope / ".." / "unrelated" / "x.txt"), "line": 1,
                              "quote": "an unrelated line"}
        red(g, rows, 5)                                                    # `..` cannot escape a scope
        rows = g.valid()
        rows[0]["receipt"] = dict(g.ev(), line=7)
        red(g, rows, 5)                                                    # fabricated file:line


def test_gate_rule6_keep_reason():
    with tmpdir() as root:
        g = GateWorld(root)
        rows = g.valid()
        rows[0]["why_fails"] = "no"
        red(g, rows, 6)
        rows = g.valid()
        rows[1]["why_fails"] = rows[0]["why_fails"]
        red(g, rows, 6)


def test_gate_rule7_rubber_stamp():
    with tmpdir() as root:
        g = GateWorld(root)
        g.write_clusters(20)
        rows = [g.row(i, receipt={"none_searched": f"searched everything for case {i}"}) for i in range(19)]
        rows.append(g.row(19, verdict="CHANGE-CANDIDATE"))
        assert math.ceil(0.1 * 20) == 2
        red(g, rows, 7)
        code, out = g.gate(rows, "--allow-all-keep", "every decision held up under the outcome data")
        assert code == 0 and any(line.startswith("KEEP=19 CHANGE=1") for line in out.splitlines()), out
        assert "every decision held up under the outcome data" in out


def test_gate_no_decisions():
    with tmpdir() as root:
        g = GateWorld(root)
        g.write_clusters(0)
        code, out = g.gate([])
        assert code == 0 and "KEEP=0 CHANGE=0 (no decisions in window)" in out.splitlines(), out
        code, out = run_cli(["gate", str(g.run / "absent.jsonl"), "--clusters", str(g.run / "clusters.jsonl"),
                             "--scope", str(g.scope)])
        assert code == 0 and "KEEP=0 CHANGE=0 (no decisions in window)" in out.splitlines(), out
        code, out = run_cli(["gate", str(g.run / "absent.jsonl"), "--clusters", str(g.run / "clusterz.jsonl"),
                             "--scope", str(g.scope)])
        assert code == 1 and rules_hit(out) == {1}, out                    # a typo is not "no decisions"


# ---------------------------------------------------------------- 11. cost

def test_cost():
    with tmpdir() as root:
        projects = root / "projects"
        sid = "33333333-0000-0000-0000-000000000001"
        proj = projects / "C--cost"
        write_lines(proj / f"{sid}.jsonl", [
            asst("k1", "2026-10-20T10:00:00Z", 1000, 400, 10000, 100),
            asst("k1", "2026-10-20T10:01:00Z", 1000, 400, 10000, 200),
            asst("k2", "2026-10-20T10:03:00Z", 500, 0, 0, 0),
            json.dumps({"type": "system", "timestamp": "2026-10-20T11:00:00Z"}),
            json.dumps({"type": "system", "timestamp": "2026-10-20T11:01:30Z"}),
        ])
        write_lines(proj / sid / "subagents" / "agent-a.jsonl", [asst("s1", "2026-10-20T10:02:00Z", 300, 0, 0, 10)])
        write_lines(proj / sid / "subagents" / "agent-b.jsonl", [asst("s2", "2026-10-20T10:02:00Z", 200, 0, 0, 0)])
        before = sorted(p for p in root.rglob("*"))
        code, out = run_cli(["cost", "--session", sid, "--projects-dir", str(projects)])
        # input 2000, cw 400, cr 10000, out 210: 2000 + 500 + 1000 + 1050 = 4550; wall 60+120+90 s = 4.5
        # min, which rounds half up to 5 (round() would give 4).
        assert code == 0 and out.strip() == "Cost: main 4550 input-equiv tokens, 2 agents, 5 min", out
        assert sorted(p for p in root.rglob("*")) == before
        code, out = run_cli(["cost", "--session", "44444444-0000-0000-0000-000000000000",
                             "--projects-dir", str(projects)])
        assert code == 1 and out.strip()


# ---------------------------------------------------------------- runner

def main():
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    failures = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            print(f"FAIL {name}")
            traceback.print_exc()
            failures.append(name)
    if failures:
        print(f"\n{len(failures)} of {len(tests)} failed: {', '.join(failures)}")
        return 1
    print(f"\nall {len(tests)} grill_dump tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
