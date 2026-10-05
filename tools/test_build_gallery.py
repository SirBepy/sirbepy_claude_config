"""Self-test for skills/preview/build_gallery.py.

Run directly: python tools/test_build_gallery.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Todo 995: the image branch of /preview had no script, only a hand-typed
node-builder-plus-curl ritual re-authored on every push. These cases drive
the real script as a subprocess (same way a session would invoke it) and
assert the budget-drop/follow-up/html-passthrough behavior the SKILL.md
Approach promises - never POST to the live Conductor endpoint
(127.0.0.1:27182): the --post wiring is proven instead by importing
post_preview() directly against a scratch local HTTP server on an ephemeral
port, so this suite never depends on, or touches, the real daemon.
"""

import http.server
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "preview" / "build_gallery.py"
TIMEOUT_SECONDS = 30

fails = []


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        fails.append(label)
        if detail:
            print(f"  {detail}")


def load_module():
    spec = importlib.util.spec_from_file_location("build_gallery", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_exists():
    check("script exists", SCRIPT.is_file(), f"missing: {SCRIPT}")


def test_basic_gallery(tmp):
    img_dir = tmp / "imgs"
    img_dir.mkdir()
    (img_dir / "a.png").write_bytes(b"\x89PNG" + b"0" * 100)
    (img_dir / "b.jpg").write_bytes(b"\xff\xd8\xff" + b"1" * 100)

    proc = run(str(img_dir), "--slug", "x", "--title", "y")
    check(
        "basic gallery exits 0",
        proc.returncode == 0,
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
    )
    check("basic gallery reports included: 2", "included: 2 dropped: []" in proc.stdout, proc.stdout)

    out_path = img_dir / "x-gallery.html"
    check("basic gallery writes output file", out_path.is_file())
    if out_path.is_file():
        html_text = out_path.read_text(encoding="utf-8")
        check("gallery embeds both figcaptions", "a.png" in html_text and "b.jpg" in html_text)
        check("gallery title present", "<title>y</title>" in html_text)


def test_budget_drop(tmp):
    img_dir = tmp / "big"
    img_dir.mkdir()
    # Names pick the sort order deliberately: collect_images sorts
    # alphabetically like render_markdown.py's collect_md_files, so
    # a-small must sort before b-huge for the included/dropped split below.
    (img_dir / "a-small.png").write_bytes(b"0" * 1000)
    (img_dir / "b-huge.png").write_bytes(b"1" * 2000)

    proc = run(str(img_dir), "--budget-mb", "0.0015", "--slug", "budget")
    check("budget-drop exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("budget-drop reports one included", "included: 1" in proc.stdout, proc.stdout)
    check("budget-drop names b-huge.png as dropped", "b-huge.png" in proc.stdout, proc.stdout)
    check("budget-drop prints a follow-up command", "follow-up: python" in proc.stdout, proc.stdout)

    out_path = img_dir / "budget-gallery.html"
    if out_path.is_file():
        html_text = out_path.read_text(encoding="utf-8")
        check("dropped file never makes it into the html", "b-huge.png" not in html_text, html_text[:200])


def test_html_passthrough(tmp):
    html_file = tmp / "mockup-thing.html"
    html_file.write_text("<!doctype html><html><body>hi</body></html>", encoding="utf-8")

    proc = run(str(html_file))
    check("html passthrough exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("html passthrough prints the given path back", str(html_file.resolve()) in proc.stdout, proc.stdout)
    check("html passthrough does not report included/dropped", "included:" not in proc.stdout, proc.stdout)


def test_missing_path_errors():
    proc = run(str(ROOT / "tools" / "does-not-exist.png"))
    check("missing path exits non-zero", proc.returncode != 0)


def test_post_against_scratch_server(tmp):
    """Proves the --post body shape and response handling without ever
    reaching 127.0.0.1:27182 - a throwaway HTTPServer on an ephemeral port
    stands in for Conductor's hook endpoint."""
    received = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            received["body"] = json.loads(self.rfile.read(length))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": "scratch-1"}).encode("utf-8"))

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    mod = load_module()
    status, body = mod.post_preview(
        "<html>scratch</html>", "Scratch Title", "scratch-slug",
        endpoint=f"http://127.0.0.1:{port}/hooks/preview",
    )
    thread.join(timeout=5)
    server.server_close()

    check("post_preview reaches the scratch server with HTTP 200", status == 200, f"status={status} body={body}")
    check(
        "post_preview sends the documented body shape",
        received.get("body", {}).get("title") == "Scratch Title"
        and received.get("body", {}).get("slug") == "scratch-slug"
        and received.get("body", {}).get("source") == "terminal"
        and received.get("body", {}).get("html") == "<html>scratch</html>",
        f"received={received.get('body')}",
    )


def main() -> int:
    test_script_exists()
    with tempfile.TemporaryDirectory(prefix="build_gallery_test_") as tmp_str:
        tmp = Path(tmp_str)
        test_basic_gallery(tmp)
        test_budget_drop(tmp)
        test_html_passthrough(tmp)
        test_post_against_scratch_server(tmp)
    test_missing_path_errors()

    if fails:
        print(f"FAIL: {len(fails)} case(s) failed: {fails}")
        return 1
    print("OK: all build_gallery.py cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
