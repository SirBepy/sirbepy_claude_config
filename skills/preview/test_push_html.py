"""Self-test for push_html.py.

Run: python skills/preview/test_push_html.py   (exit 0 = all pass)

The script POSTs to Conductor's preview hook; here a throwaway local HTTP server stands in for
the daemon, so the test proves what actually reaches the wire: session_id is always present, and
an unset CLAUDE_CODE_SESSION_ID exits non-zero without any request being made.
"""

import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "push_html.py"
failures = []
received = []


def check(cond, label, detail=""):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)
        if detail:
            print(f"  {detail}")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        received.append(json.loads(self.rfile.read(length)))
        payload = b'{"id": "entry-42"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def run(args, env_extra, drop=()):
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60, env=env
    )


def main():
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f"http://127.0.0.1:{server.server_port}/hooks/preview"
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "m.html"
        page.write_text('<!doctype html><title>t</title><p class="a">é "quoted"</p>', encoding="utf-8")
        base = [str(page), "--slug", "s1", "--title", "T1", "--endpoint", endpoint]

        proc = run(base, {}, drop=("CLAUDE_CODE_SESSION_ID",))
        check(proc.returncode != 0, "an unset CLAUDE_CODE_SESSION_ID exits non-zero", f"rc={proc.returncode}")
        check("CLAUDE_CODE_SESSION_ID" in proc.stderr, "the error names the missing variable", proc.stderr)
        check(received == [], "nothing is posted without a session id", str(received))

        proc = run(base, {"CLAUDE_CODE_SESSION_ID": ""})
        check(proc.returncode != 0 and received == [], "an empty session id is refused too", proc.stderr)

        proc = run(base, {"CLAUDE_CODE_SESSION_ID": "sess-123"})
        check(proc.returncode == 0, "a set session id posts and exits 0", proc.stderr)
        check(proc.stdout.strip().endswith("entry-42"), "the returned id is printed", proc.stdout)
        body = received[0] if received else {}
        check(body.get("session_id") == "sess-123", "the body carries session_id", str(body.keys()))
        check(
            body.get("slug") == "s1" and body.get("title") == "T1" and body.get("source") == "terminal",
            "slug, title and the default source terminal are sent",
            str(body),
        )
        check(body.get("html") == page.read_text(encoding="utf-8"), "the html is sent unchanged")

        proc = run(base + ["--source", "chat"], {"CLAUDE_CODE_SESSION_ID": "sess-123"})
        check(len(received) == 2 and received[1].get("source") == "chat", "--source chat is passed through")

        proc = run([str(Path(tmp) / "missing.html"), "--slug", "s", "--title", "t", "--endpoint", endpoint],
                   {"CLAUDE_CODE_SESSION_ID": "sess-123"})
        check(proc.returncode != 0 and len(received) == 2, "a missing html file exits non-zero without posting")

        latin = Path(tmp) / "latin.html"
        latin.write_bytes("<p>café</p>".encode("latin-1"))
        proc = run([str(latin), "--slug", "s", "--title", "t", "--endpoint", endpoint],
                   {"CLAUDE_CODE_SESSION_ID": "sess-123"})
        check(proc.returncode == 2 and "cannot read" in proc.stderr and "Traceback" not in proc.stderr and len(received) == 2,
              "a non-UTF-8 html file exits 2 with one line and no traceback, without posting", proc.stderr)

    server.shutdown()
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall push_html tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
