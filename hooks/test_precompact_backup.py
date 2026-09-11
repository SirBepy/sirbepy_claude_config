"""Self-test for precompact-backup.py (todo 426, PreCompact-only scope).

Run directly: python hooks/test_precompact_backup.py

Mixes two conventions already used across this suite (both read this
session, see the sibling test files):
  - in-process + monkeypatched SESSION_MARKER_DIR / read_payload for unit
    coverage, the send-message-stop-guard.py convention - a subprocess would
    re-import the module fresh and write its marker to the REAL
    hooks/.session-markers/ instead of a temp dir.
  - subprocess integration for the real entrypoint's fail-open wrapper (the
    `if __name__ == "__main__":` try/except only runs when the file is
    executed directly, not when exec_module()'d in-process), the
    em-dash-guard.py convention - needed here specifically to prove a
    malformed payload still exits 0 through the REAL entrypoint, not just
    through main() called directly.
"""

import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "precompact-backup.py"
guard = _testlib.load_module("precompact_backup", _GUARD_PATH)

fails = []


def write_transcript(tmpdir: Path, name: str, tool_calls: list) -> Path:
    """tool_calls is [(tool_name, input_dict), ...], each wrapped as one
    assistant tool_use entry - matches write_transcript_with_inputs's shape
    in test_send_message_stop_guard.py."""
    entries = [{"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}}]
    for i, (tool_name, tool_input) in enumerate(tool_calls):
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": f"toolu_{i}", "name": tool_name, "input": tool_input}]},
        })
    path = tmpdir / name
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


# --- unit: recently_touched_files ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)

    transcript = write_transcript(tmpdir, "t1.jsonl", [
        ("Read", {"file_path": "/repo/a.py"}),
        ("Edit", {"file_path": "/repo/b.py"}),
        ("Edit", {"file_path": "/repo/a.py"}),  # re-touched: moves to the end
        ("Bash", {"command": "ls"}),  # not a file-path tool, ignored
    ])

    got = guard.recently_touched_files(str(transcript))
    label = "dedup keeps the most recent occurrence's position"
    fails += [] if _testlib.report(got == ["/repo/b.py", "/repo/a.py"], f"{label} (got {got})") else [label]

    label = "a non-file-path tool (Bash) contributes no path"
    fails += [] if _testlib.report("ls" not in got, label) else [label]

    label = "a missing transcript path returns an empty list, no crash"
    fails += [] if _testlib.report(guard.recently_touched_files("") == [], label) else [label]

    label = "a nonexistent transcript file returns an empty list, no crash"
    fails += [] if _testlib.report(guard.recently_touched_files(str(tmpdir / "missing.jsonl")) == [], label) else [label]

    many_calls = [("Write", {"file_path": f"/repo/f{i}.py"}) for i in range(80)]
    big_transcript = write_transcript(tmpdir, "big.jsonl", many_calls)
    got_capped = guard.recently_touched_files(str(big_transcript))
    label = f"list is capped to MAX_TOUCHED_FILES ({guard.MAX_TOUCHED_FILES})"
    fails += [] if _testlib.report(len(got_capped) == guard.MAX_TOUCHED_FILES, f"{label} (got {len(got_capped)})") else [label]
    label = "capping keeps the most-recently-touched files, not the earliest"
    fails += [] if _testlib.report(got_capped[-1] == "/repo/f79.py", label) else [label]

# --- unit: session id safety ---

label = "a UUID-shaped session id is safe"
fails += [] if _testlib.report(guard._safe_session_id("25f6b576-c3c9-4ee1-bfc1-c7ae6fe22612"), label) else [label]

label = "a path-traversal-shaped session id is rejected"
fails += [] if _testlib.report(not guard._safe_session_id("../../etc/passwd"), label) else [label]

label = "an empty session id is rejected"
fails += [] if _testlib.report(not guard._safe_session_id(""), label) else [label]

# --- in-process: main() writes the expected backup on a normal payload ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"

    transcript = write_transcript(tmpdir, "session.jsonl", [
        ("Edit", {"file_path": "/repo/x.py"}),
    ])
    session_id = "unit-test-session-1"
    payload = {
        "hook_event_name": "PreCompact",
        "session_id": session_id,
        "cwd": "/repo",
        "trigger": "manual",
        "transcript_path": str(transcript),
    }
    guard.read_payload = lambda: payload

    try:
        guard.main()
        code = 0
    except SystemExit as e:
        code = e.code

    label = "main() exits 0 on a normal payload"
    fails += [] if _testlib.report(code == 0, f"{label} (got {code})") else [label]

    marker_path = guard.SESSION_MARKER_DIR / f"{guard.MARKER_PREFIX}{session_id}.json"
    label = "the per-session backup file was written"
    fails += [] if _testlib.report(marker_path.exists(), label) else [label]

    if marker_path.exists():
        written = json.loads(marker_path.read_text(encoding="utf-8"))
        label = "backup carries the session_id"
        fails += [] if _testlib.report(written.get("session_id") == session_id, label) else [label]
        label = "backup carries the trigger"
        fails += [] if _testlib.report(written.get("trigger") == "manual", label) else [label]
        label = "backup carries the touched file path"
        fails += [] if _testlib.report(written.get("recently_touched_files") == ["/repo/x.py"], label) else [label]
        label = "backup never carries a transcript_path or raw content field"
        fails += [] if _testlib.report(
            "transcript_path" not in written and "transcript" not in written and "last_user_prompt" not in written,
            label,
        ) else [label]

    # A second compaction in the SAME session overwrites, never appends.
    transcript2 = write_transcript(tmpdir, "session2.jsonl", [
        ("Write", {"file_path": "/repo/y.py"}),
    ])
    payload2 = dict(payload, transcript_path=str(transcript2))
    guard.read_payload = lambda: payload2
    try:
        guard.main()
    except SystemExit:
        pass
    written2 = json.loads(marker_path.read_text(encoding="utf-8"))
    label = "a second compaction in the same session overwrites the one file, not append"
    fails += [] if _testlib.report(written2.get("recently_touched_files") == ["/repo/y.py"], label) else [label]

# --- in-process: missing session_id writes nothing, still exits 0 ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.read_payload = lambda: {"hook_event_name": "PreCompact", "trigger": "auto"}

    try:
        guard.main()
        code = 0
    except SystemExit as e:
        code = e.code

    label = "main() exits 0 when session_id is missing"
    fails += [] if _testlib.report(code == 0, f"{label} (got {code})") else [label]
    label = "no marker directory is created when session_id is missing/unsafe"
    fails += [] if _testlib.report(not guard.SESSION_MARKER_DIR.exists() or not any(guard.SESSION_MARKER_DIR.iterdir()), label) else [label]

# --- integration: the REAL entrypoint fails open on a malformed payload ---

proc = subprocess.run(
    [sys.executable, str(_GUARD_PATH)],
    input="not valid json {{{",
    capture_output=True,
    text=True,
)
label = "the real entrypoint exits 0 on malformed (non-JSON) stdin"
fails += [] if _testlib.report(proc.returncode == 0, f"{label} (got exit={proc.returncode}, stderr={proc.stderr.strip()!r})") else [label]

# --- integration: never writes into the repo (git-ignored, and git status stays clean) ---

label = "hooks/.session-markers/ is git-ignored"
check = subprocess.run(
    ["git", "check-ignore", "-q", str(_HOOKS_DIR / ".session-markers" / "precompact-probe.json")],
    cwd=_HOOKS_DIR.parent,
)
fails += [] if _testlib.report(check.returncode == 0, label) else [label]

probe_session_id = f"test-precompact-{uuid.uuid4().hex}"
probe_marker = _HOOKS_DIR / ".session-markers" / f"precompact-{probe_session_id}.json"
try:
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=_HOOKS_DIR.parent, capture_output=True, text=True, check=True
    ).stdout

    proc = subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps({"hook_event_name": "PreCompact", "session_id": probe_session_id, "trigger": "auto"}),
        capture_output=True,
        text=True,
    )
    label = "the real entrypoint exits 0 on a normal payload"
    fails += [] if _testlib.report(proc.returncode == 0, f"{label} (got {proc.returncode})") else [label]

    label = "the real entrypoint actually wrote the per-session backup file"
    fails += [] if _testlib.report(probe_marker.exists(), label) else [label]

    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=_HOOKS_DIR.parent, capture_output=True, text=True, check=True
    ).stdout
    label = "writing the backup does not change `git status` (git-ignored, no repo pollution)"
    fails += [] if _testlib.report(before == after, f"{label} (before={before!r} after={after!r})") else [label]
finally:
    try:
        probe_marker.unlink()
    except OSError:
        pass

sys.exit(_testlib.summarize(fails, style="count"))
