"""Self-test for the --manifest (before/after pairs) branch of build_gallery.py.

Run: python skills/preview/test_build_gallery.py   (exit 0 = all pass)

Todo 1174: the flat gallery had no pairing, per-item notes or WebP step, so a 14-item keep/drop
sweep was hand-built each time. These cases drive the real script as a subprocess against
synthetic PNGs written with zlib (no Pillow, so it runs on CI's bare Windows runner). Nothing
here POSTs: --post and --check need the live Conductor daemon, so the post-response URL logic is
proven through render_url_from_response() alone.
"""

import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

SCRIPT = Path(os.environ.get("BUILD_GALLERY_SCRIPT") or Path(__file__).resolve().parent / "build_gallery.py")
TIMEOUT_SECONDS = 60
CAP_BYTES = 2 * 1024 * 1024

failures = []


def check(cond, label, detail=""):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)
        if detail:
            print(f"  {detail}")


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=TIMEOUT_SECONDS
    )


def write_png(path, seed, width=160, height=300):
    """A banded gradient PNG: compresses like a real flat-UI screenshot, differs per seed."""
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row += bytes(((x + seed * 7) % 256, (y // 8 * 5 + seed * 13) % 256, (x // 16 * 20) % 256))
        rows.append(bytes(row))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    raw = b"".join(rows)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def make_manifest(root, count, as_object=False):
    shots_dir = root / "shots"
    shots_dir.mkdir(exist_ok=True)
    items = []
    for n in range(1, count + 1):
        write_png(shots_dir / f"{n}-before.png", n)
        write_png(shots_dir / f"{n}-after.png", n + 100)
        items.append(
            {
                "id": f"fix-{n}",
                "title": f"Fix number {n}",
                "note": f"Note for {n}",
                "shots": [["Before", f"shots/{n}-before.png"], ["After", f"shots/{n}-after.png"]],
            }
        )
    manifest = root / "sweep.json"
    manifest.write_text(json.dumps({"title": "Sweep", "items": items} if as_object else items), encoding="utf-8")
    return manifest


def load_module():
    spec = importlib.util.spec_from_file_location("build_gallery_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_twelve_pairs_build_under_cap(root):
    (root / "big").mkdir()
    manifest = make_manifest(root / "big", 12, as_object=True)
    proc = run("--manifest", str(manifest))
    check(proc.returncode == 0, "12-item manifest builds", f"stderr={proc.stderr!r}")
    out = root / "big" / "sweep-gallery.html"
    check(out.is_file(), "output html is written next to the manifest")
    if not out.is_file():
        return
    html = out.read_text(encoding="utf-8")
    check(len(html.encode("utf-8")) < CAP_BYTES, "12 pairs stay under the 2MB endpoint cap", str(len(html)))
    check("included: 12 dropped: []" in proc.stdout, "all 12 items included, none dropped", proc.stdout)

    titles = [html.find(f"Fix number {n}<") for n in range(1, 13)]
    check(all(t > 0 for t in titles) and titles == sorted(titles), "sections render in manifest order")
    badges = re.findall(r'<span class="badge">(\d+)</span>', html)
    check(badges == [str(n) for n in range(1, 13)], "badges number 1..12", str(badges))
    captions = re.findall(r"<figcaption>(\w+)</figcaption>", html)
    check(captions == ["Before", "After"] * 12, "each section shows Before then After", str(captions[:6]))
    idxs = re.findall(r'class="gallery-img" data-idx="(\d+)"', html)
    check(idxs == [str(i) for i in range(24)], "every shot joins the lightbox sequence 0..23")
    check("function openLightbox" in html and html.count('id="lightbox"') == 1, "lightbox is included once")
    check("Note for 7" in html and "<title>Sweep</title>" in html, "notes and the manifest title render")


def test_budget_drops_whole_items(root):
    d = root / "budget"
    d.mkdir()
    manifest = make_manifest(d, 6)
    probe = run("--manifest", str(manifest))
    if probe.returncode != 0:
        check(False, "budget probe build exits 0", probe.stderr)
        return
    first_size = len((d / "sweep-gallery.html").read_bytes())
    # A budget of roughly one item (raw bytes, before base64) forces a drop after item 1.
    one_item_bytes = int(first_size / 6 / 1.34)
    mb = max(one_item_bytes * 1.5 / (1024 * 1024), 0.001)
    proc = run("--manifest", str(manifest), "--budget-mb", f"{mb:.6f}")
    check(probe.returncode == 0 and proc.returncode == 0, "budgeted build exits 0", proc.stderr)
    m = re.search(r"included: (\d+) dropped: \[(.*)\]", proc.stdout)
    check(bool(m) and 0 < int(m.group(1)) < 6, "a tight budget drops some items", proc.stdout)
    html = (d / "sweep-gallery.html").read_text(encoding="utf-8")
    shots = html.count('class="gallery-img"')
    check(m is not None and shots == int(m.group(1)) * 2, "no pair is split by the budget drop", f"{shots} shots")
    check("follow-up:" in proc.stdout, "a follow-up hint is printed for the dropped items")


def test_missing_shot_error(root):
    d = root / "missing"
    d.mkdir()
    manifest = make_manifest(d, 3)
    (d / "shots" / "2-after.png").unlink()
    proc = run("--manifest", str(manifest))
    check(proc.returncode == 1, "a missing shot exits 1")
    check(
        "item 'fix-2'" in proc.stderr and "shot 'After'" in proc.stderr and "2-after.png" in proc.stderr,
        "the error names the item, the shot caption and the path",
        proc.stderr,
    )
    check(not (d / "sweep-gallery.html").exists(), "no output is written on a failed validation")


def test_validation_errors(root):
    d = root / "invalid"
    d.mkdir()
    write_png(d / "a.png", 1)
    ok_shot = [["Before", "a.png"]]

    def attempt(label, payload, expect):
        f = d / "m.json"
        f.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
        proc = run("--manifest", str(f))
        check(proc.returncode == 1 and expect in proc.stderr, label, proc.stderr)

    attempt("bad JSON is reported", "{not json", "not valid JSON")
    attempt("an empty list is rejected", [], "non-empty list of items")
    attempt("a missing id is reported", [{"title": "t", "shots": ok_shot}], "item #1: missing 'id'")
    attempt("a missing title is reported", [{"id": "x", "shots": ok_shot}], "item 'x': missing 'title'")
    attempt(
        "a duplicate id is reported",
        [{"id": "x", "title": "t", "shots": ok_shot}, {"id": "x", "title": "u", "shots": ok_shot}],
        "item 'x': duplicate id",
    )
    attempt("empty shots are rejected", [{"id": "x", "title": "t", "shots": []}], "item 'x': 'shots'")
    attempt(
        "a malformed shot is rejected",
        [{"id": "x", "title": "t", "shots": [["only-caption"]]}],
        "each shot must be [caption, path]",
    )
    attempt(
        "a non-image shot is rejected",
        [{"id": "x", "title": "t", "shots": [["Before", "m.json"]]}],
        "not an image file",
    )
    proc = run("--manifest", str(d / "m.json"), str(d / "a.png"))
    check(proc.returncode == 1 and "not both" in proc.stderr, "--manifest plus image paths is rejected")
    proc = run()
    check(proc.returncode == 1 and "--manifest" in proc.stderr, "no input at all is an error, not a traceback")


def test_webp_conversion(root):
    mod = load_module()
    d = root / "webp"
    d.mkdir()
    src = d / "s.png"
    write_png(src, 3, width=400, height=700)
    with tempfile.TemporaryDirectory() as tmp:
        mime, data = mod.convert_to_webp(src, tmp)
    if shutil.which("ffmpeg"):
        check(mime == "image/webp" and data[:4] == b"RIFF" and data[8:12] == b"WEBP", "PNG is re-encoded to WebP")
        check(len(data) < src.stat().st_size, "the WebP is smaller than the PNG")
    else:
        check(mime == "image/png" and data == src.read_bytes(), "no ffmpeg: the original is kept")
    gif = d / "a.gif"
    gif.write_bytes(b"GIF89a" + b"0" * 20)
    with tempfile.TemporaryDirectory() as tmp:
        mime, data = mod.convert_to_webp(gif, tmp)
    check(mime == "image/gif" and data == gif.read_bytes(), "gifs are never re-encoded")


def test_relative_paths_and_escaping(root):
    d = root / "escape"
    (d / "sub").mkdir(parents=True)
    write_png(d / "sub" / "a.png", 1)
    manifest = d / "m.json"
    manifest.write_text(
        json.dumps([{"id": "a b", "title": "<b>bold</b> & co", "shots": [["Be<fore", "sub/a.png"]]}]),
        encoding="utf-8",
    )
    proc = run("--manifest", str(manifest), "--out", str(d / "o.html"))
    html = (d / "o.html").read_text(encoding="utf-8") if (d / "o.html").exists() else ""
    check(proc.returncode == 0, "relative shot paths resolve against the manifest directory", proc.stderr)
    check("&lt;b&gt;bold&lt;/b&gt; &amp; co" in html and "<b>bold</b>" not in html, "titles are HTML-escaped")
    check("Be&lt;fore" in html, "captions are HTML-escaped")
    check('id="item-a-b"' in html, "section anchors are slugified")


def test_render_url():
    mod = load_module()
    base = "http://127.0.0.1:27182/hooks/preview-render"
    check(
        mod.render_url_from_response(200, '{"id": "abc123"}', base) == f"{base}/abc123",
        "a 200 response yields the preview-render URL",
    )
    check(mod.render_url_from_response(413, "too big", base) is None, "a non-200 response yields no URL")
    check(mod.render_url_from_response(200, "not json", base) is None, "an unparseable body yields no URL")
    check(mod.render_url_from_response(200, "{}", base) is None, "a body without an id yields no URL")
    check(mod.render_url_from_response(None, "refused", base) is None, "a refused connection yields no URL")


def test_render_url_helper():
    mod = load_module()
    base = "http://127.0.0.1:27182/hooks/preview-render"
    check(hasattr(mod, "render_url"), "render_url helper exists")
    if not hasattr(mod, "render_url"):
        return
    check(mod.render_url("abc123", base) == f"{base}/abc123", "render_url joins base and id")
    check(mod.render_url("abc123", base + "/") == f"{base}/abc123", "render_url tolerates a trailing slash")
    check(
        mod.render_url("zz9") == f"{mod.RENDER_CHECK_ENDPOINT.rstrip('/')}/zz9",
        "render_url defaults to the render-check endpoint",
    )
    # The --check path is untestable without a live daemon plus chromium, so prove it shares the
    # helper structurally: the endpoint join must be spelled out in exactly one place.
    source = SCRIPT.read_text(encoding="utf-8")
    check(source.count(".rstrip('/')") == 1, "the render URL is formed in one place only", str(source.count(".rstrip('/')")))


def test_duplicate_slug_ids_are_unique(root):
    d = root / "slugs"
    d.mkdir()
    write_png(d / "a.png", 1)
    shot = [["Before", "a.png"]]
    ids = ["a b", "a-b", "A B", "a-b-2", "other"]
    manifest = d / "m.json"
    manifest.write_text(
        json.dumps([{"id": i, "title": f"T{n}", "shots": shot} for n, i in enumerate(ids)]), encoding="utf-8"
    )
    proc = run("--manifest", str(manifest), "--out", str(d / "o.html"))
    check(proc.returncode == 0, "ids that slugify alike still build", proc.stderr)
    html = (d / "o.html").read_text(encoding="utf-8") if (d / "o.html").exists() else ""
    found = re.findall(r'<section class="item" id="([^"]+)"', html)
    check(len(found) == len(ids) and len(set(found)) == len(found), "every section has a unique html id", str(found))
    check(found[:3] == ["item-a-b", "item-a-b-2", "item-a-b-3"], "collisions take -2, -3 in manifest order", str(found))
    check(found[3:] == ["item-a-b-2-2", "item-other"], "a later literal slug does not reuse a taken id", str(found))


def test_single_oversize_item_is_an_error(root):
    d = root / "oversize"
    d.mkdir()
    manifest = make_manifest(d, 2)
    # A budget far below any one item: the old behaviour dropped everything and printed a
    # follow-up whose rerun would drop the same item again, forever.
    proc = run("--manifest", str(manifest), "--budget-mb", "0.0001")
    check(proc.returncode == 1, "an item larger than the whole budget exits 1", f"rc={proc.returncode} out={proc.stdout!r}")
    check(
        "fix-1" in proc.stderr and "budget" in proc.stderr,
        "the error names the item and the budget",
        proc.stderr,
    )
    check("follow-up:" not in proc.stdout, "no follow-up hint that could never converge", proc.stdout)
    check(not (d / "sweep-gallery.html").exists(), "no half-built gallery is written")


def test_flat_single_oversize_file_is_an_error(root):
    d = root / "flat-oversize"
    d.mkdir()
    (d / "big.png").write_bytes(b"\x89PNG" + b"\0" * 400)
    proc = run(str(d), "--budget-mb", "0.0001", "--slug", "flat")
    check(proc.returncode == 1, "a flat-gallery file larger than the whole budget exits 1", f"rc={proc.returncode} out={proc.stdout!r}")
    check("big.png" in proc.stderr and "budget" in proc.stderr, "the error names the file and the budget", proc.stderr)
    check("follow-up:" not in proc.stdout, "no flat follow-up hint that could never converge", proc.stdout)
    check(not (d / "flat-gallery.html").exists(), "no flat gallery is written")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        test_twelve_pairs_build_under_cap(root)
        test_budget_drops_whole_items(root)
        test_missing_shot_error(root)
        test_validation_errors(root)
        test_webp_conversion(root)
        test_relative_paths_and_escaping(root)
        test_duplicate_slug_ids_are_unique(root)
        test_single_oversize_item_is_an_error(root)
        test_flat_single_oversize_file_is_an_error(root)
    test_render_url()
    test_render_url_helper()
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall build_gallery manifest tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
