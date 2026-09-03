"""Self-test for list-peers-pre-edit-guard.py.

Run directly: python hooks/test_list_peers_pre_edit_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real guard.main() against a throwaway `git init` repo and a fake
local HTTP server standing in for the daemon's `/channel/list-peers` route
(guard.DAEMON_PORT is monkeypatched to the fake server's port) - no real
daemon, no real network beyond loopback, no live git repo other than the
temp one this suite creates and destroys.
"""

import http.server
import io
import json
import subprocess
import sys
import tempfile
import threading
from contextlib import redirect_stdout
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "list-peers-pre-edit-guard.py"
)

fails = []


def run_main(session_id: str = "s1", cwd: str = "", file_path: str = "foo.py", tool_input=None):
    payload_input = {"file_path": file_path} if tool_input is None else tool_input
    guard.read_payload = lambda: {
        "session_id": session_id,
        "cwd": cwd,
        "tool_input": payload_input,
    }
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            guard.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, buf.getvalue()


def make_handler(response_body: bytes):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response_body)

        def log_message(self, *args):
            pass

    return Handler


def start_fake_daemon(response_body: bytes):
    server = http.server.HTTPServer(("127.0.0.1", 0), make_handler(response_body))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def free_port() -> int:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --- peer_label formatting ---

LABEL_CASES = [
    ({"name": "Bob", "branch": "main"}, "Bob (main)", "name and branch"),
    ({"name": "Bob"}, "Bob", "name only, no branch"),
    ({"session_id": "abc123"}, "abc123", "falls back to session_id"),
    ({}, "unknown", "falls back to unknown when nothing identifies the peer"),
]


def check_label(case) -> bool:
    peer, expected, label = case
    got = guard.peer_label(peer)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected!r}, got {got!r})")
    return ok


fails += _testlib.run_cases(LABEL_CASES, check_label)

# --- main() end to end ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"

    code, out = run_main(session_id="", cwd=str(tmpdir))
    fails += [] if (code == 0 and out == "") else ["missing session_id skips silently"]

    code, out = run_main(session_id="s1", cwd="")
    fails += [] if (code == 0 and out == "") else ["missing cwd skips silently"]

    non_repo = tmpdir / "non-repo"
    non_repo.mkdir()
    code, out = run_main(session_id="s1", cwd=str(non_repo))
    fails += [] if (code == 0 and out == "") else ["non-git cwd produces no output"]

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    guard.DAEMON_PORT = free_port()  # nothing listens here

    code, out = run_main(session_id="s1", cwd=str(repo))
    ok = code == 0 and out == "" and guard.marker_path("s1", guard.repo_root(str(repo))).exists()
    fails += [] if ok else ["unreachable daemon fails open and marks the session+repo"]

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    server, thread = start_fake_daemon(json.dumps({"ok": False, "error": "unknown session"}).encode())
    guard.DAEMON_PORT = server.server_address[1]
    try:
        code, out = run_main(session_id="s1", cwd=str(repo))
        ok = code == 0 and out == "" and guard.marker_path("s1", guard.repo_root(str(repo))).exists()
        fails += [] if ok else ["unregistered session (ok:false) fails open and marks"]
    finally:
        server.shutdown()
        thread.join(timeout=5)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    server, thread = start_fake_daemon(json.dumps({"peers": []}).encode())
    guard.DAEMON_PORT = server.server_address[1]
    try:
        code, out = run_main(session_id="s1", cwd=str(repo))
        ok = code == 0 and out == "" and guard.marker_path("s1", guard.repo_root(str(repo))).exists()
        fails += [] if ok else ["zero peers produces no output at all"]
    finally:
        server.shutdown()
        thread.join(timeout=5)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    peers = [{"session_id": "s2", "name": "Bob", "branch": "main"}]
    server, thread = start_fake_daemon(json.dumps({"peers": peers}).encode())
    guard.DAEMON_PORT = server.server_address[1]
    try:
        code, out = run_main(session_id="s1", cwd=str(repo), file_path="src/x.py")
        lines = [ln for ln in out.splitlines() if ln.strip()]
        ok = code == 0 and len(lines) == 1
        if ok:
            payload = json.loads(lines[0])
            reason = payload.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            ok = (
                payload["hookSpecificOutput"]["permissionDecision"] == "allow"
                and "Bob" in reason
                and "src/x.py" in reason
            )
        fails += [] if ok else ["a peer produces exactly one warning naming the peer and the file"]

        # A second edit in the same session+repo must not re-warn (marker short-circuits).
        code2, out2 = run_main(session_id="s1", cwd=str(repo), file_path="src/y.py")
        fails += [] if (code2 == 0 and out2 == "") else ["warning fires once per session, not per edit"]

        # settings.json matches this guard on MultiEdit and NotebookEdit too, and those two carry a
        # different tool_input shape: MultiEdit adds `edits`, NotebookEdit has no `file_path` at all.
        code3, out3 = run_main(
            session_id="s3",
            cwd=str(repo),
            tool_input={"file_path": "src/z.py", "edits": [{"old_string": "a", "new_string": "b"}]},
        )
        ok3 = code3 == 0 and "src/z.py" in out3 and "Bob" in out3
        fails += [] if ok3 else ["a MultiEdit payload warns and names the file"]

        code4, out4 = run_main(
            session_id="s4",
            cwd=str(repo),
            tool_input={"notebook_path": "src/nb.ipynb", "new_source": "x"},
        )
        ok4 = code4 == 0 and "Bob" in out4 and "src/nb.ipynb" in out4
        fails += [] if ok4 else ["a NotebookEdit payload warns and names the notebook"]
    finally:
        server.shutdown()
        thread.join(timeout=5)

# --- git backstop (todo 895): HEAD moving stands in for a lied-about peer ---


def commit(repo: Path, name: str) -> None:
    (repo / name).write_text("x")
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t.com", "-c", "user.name=T", "commit", "-q", "-m", name],
        cwd=repo,
        check=True,
    )


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    server, thread = start_fake_daemon(json.dumps({"peers": []}).encode())
    guard.DAEMON_PORT = server.server_address[1]
    try:
        code, out = run_main(session_id="s5", cwd=str(repo), file_path="a.py")
        fails += [] if (code == 0 and out == "") else ["first check with zero peers stays silent"]

        commit(repo, "a.py")

        code2, out2 = run_main(session_id="s5", cwd=str(repo), file_path="b.py")
        ok2 = code2 == 0 and "HEAD moved" in out2 and "b.py" in out2
        fails += [] if ok2 else ["HEAD moving since last check warns even when list_peers stays empty"]

        # Marker now holds the moved-to sha, so a further check with no new move is silent again.
        code3, out3 = run_main(session_id="s5", cwd=str(repo), file_path="c.py")
        fails += [] if (code3 == 0 and out3 == "") else ["git backstop warns once per HEAD move, not repeatedly"]
    finally:
        server.shutdown()
        thread.join(timeout=5)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)
    commit(repo, "seed.py")
    server, thread = start_fake_daemon(json.dumps({"peers": []}).encode())
    guard.DAEMON_PORT = server.server_address[1]
    try:
        code, _ = run_main(session_id="s6", cwd=str(repo), file_path="a.py")
        code2, out2 = run_main(session_id="s6", cwd=str(repo), file_path="b.py")
        fails += [] if (code2 == 0 and out2 == "") else ["equal shas across checks stays silent"]
    finally:
        server.shutdown()
        thread.join(timeout=5)

sys.exit(_testlib.summarize(fails))
