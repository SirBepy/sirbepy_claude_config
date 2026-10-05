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
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "preview" / "build_gallery.py"
TIMEOUT_SECONDS = 30

fails = []


def run(*args: str, env: dict = None, timeout: int = TIMEOUT_SECONDS) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=timeout, env=env,
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


def test_lightbox_markup(tmp):
    """Todo 995's 2026-10-05 fold-in: Joe asked to click a gallery image to
    open it full-size, step with arrow keys, close with Esc/backdrop click.
    Asserts the generated page carries that markup/handlers for every
    included image - pure inline CSS+JS, no external deps."""
    img_dir = tmp / "lb"
    img_dir.mkdir()
    (img_dir / "a.png").write_bytes(b"\x89PNG" + b"0" * 100)
    (img_dir / "b.png").write_bytes(b"\x89PNG" + b"1" * 100)
    (img_dir / "c.png").write_bytes(b"\x89PNG" + b"2" * 100)

    proc = run(str(img_dir), "--slug", "lb")
    check("lightbox gallery exits 0", proc.returncode == 0, proc.stdout + proc.stderr)

    html_text = (img_dir / "lb-gallery.html").read_text(encoding="utf-8")
    check("lightbox overlay markup present", 'id="lightbox"' in html_text)
    check("lightbox image slot present", 'id="lightbox-img"' in html_text)
    check(
        "every one of the 3 images is clickable into the lightbox",
        html_text.count('class="gallery-img"') == 3,
        html_text.count('class="gallery-img"'),
    )
    for i in range(3):
        check(f"image {i} wired to openLightbox({i})", f"openLightbox({i})" in html_text)
    check("left/right arrow key stepping wired", "ArrowLeft" in html_text and "ArrowRight" in html_text)
    check("Esc closes the lightbox", "Escape" in html_text and "closeLightbox" in html_text)
    check("on-screen prev/next arrows present", "lightbox-prev" in html_text and "lightbox-next" in html_text)
    check("backdrop click closes the lightbox", "lbBackdropClick" in html_text)


def test_check_flag_cli(tmp):
    """The 2026-10-03 fold-in: --check POSTs the html to /hooks/preview-render, loads
    /hooks/preview-render/<id> headless, and fails on a page error (a doc that rendered fine
    from file:// once threw an inline-script parse error only in the panel). Proven here
    against a scratch HTTP server standing in for /hooks/preview-render - BUILD_GALLERY_RENDER_CHECK_ENDPOINT
    overrides the script's endpoint so this never reaches the real 127.0.0.1:27182 daemon, same
    safety rule as test_post_against_scratch_server above."""
    store = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            payload = json.loads(self.rfile.read(length))
            html_in = payload.get("html", "")
            page_id = "bad" if "THROW_MARKER" in html_in else "good"
            store[page_id] = html_in
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": page_id}).encode("utf-8"))

        def do_GET(self):
            page_id = self.path.rsplit("/", 1)[-1]
            html_out = store.get(page_id, "<html><body>missing</body></html>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html_out.encode("utf-8"))

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    env = dict(os.environ)
    env["BUILD_GALLERY_RENDER_CHECK_ENDPOINT"] = f"http://127.0.0.1:{port}/hooks/preview-render"

    good_html = tmp / "good.html"
    good_html.write_text("<!doctype html><html><body>fine</body></html>", encoding="utf-8")
    bad_html = tmp / "bad.html"
    bad_html.write_text(
        "<!doctype html><html><body><script>/*THROW_MARKER*/undefinedFn();</script></body></html>",
        encoding="utf-8",
    )

    try:
        proc_good = run(str(good_html), "--check", env=env, timeout=45)
        unavailable = any(
            marker in (proc_good.stdout + proc_good.stderr)
            for marker in ("playwright not found", "chromium revision", "not installed")
        )
        if unavailable:
            print("SKIP --check cases: playwright/chromium unavailable on this machine")
            print(proc_good.stdout + proc_good.stderr)
        else:
            check(
                "--check passes a page with no JS error",
                proc_good.returncode == 0 and "check OK" in proc_good.stdout,
                proc_good.stdout + proc_good.stderr,
            )

            proc_bad = run(str(bad_html), "--check", env=env, timeout=45)
            check(
                "--check fails a page that throws",
                proc_bad.returncode != 0 and "check FAILED" in (proc_bad.stdout + proc_bad.stderr),
                proc_bad.stdout + proc_bad.stderr,
            )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


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
        test_lightbox_markup(tmp)
        test_check_flag_cli(tmp)
    test_missing_path_errors()

    if fails:
        print(f"FAIL: {len(fails)} case(s) failed: {fails}")
        return 1
    print("OK: all build_gallery.py cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
