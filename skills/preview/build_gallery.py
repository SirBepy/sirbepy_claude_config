#!/usr/bin/env python3
"""Builds a /preview gallery page from one or more images (or a directory of
them), or pushes a single existing .html file - one command instead of the
hand-typed node-builder-plus-curl ritual the image branch used to require.
Mirrors render_markdown.py's pattern: prints the output path, then with
--post sends the same POST /preview's HTML steps describe, by hand, today.

Stdlib only (urllib, base64, mimetypes) - no new dependency, matching the
rest of this skill (render_markdown.py is the one exception, for the
markdown library it already depended on before this script existed)."""
import argparse
import base64
import html as html_mod
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ENDPOINT = "http://127.0.0.1:27182/hooks/preview"
DEFAULT_BUDGET_MB = 1.5
# Test-only override (todo 995's 2026-10-03 fold-in): never set this for a real push. It exists
# so tools/test_build_gallery.py can point --check at a scratch HTTP server instead of the live
# Conductor daemon on 27182.
RENDER_CHECK_ENDPOINT = os.environ.get(
    "BUILD_GALLERY_RENDER_CHECK_ENDPOINT", "http://127.0.0.1:27182/hooks/preview-render"
)
_RESOLVER_PATH = Path(__file__).resolve().parent.parent / "_shared" / "playwright-resolve.cjs"

# Pure inline CSS+JS, no external deps (todo 995, 2026-10-05 fold-in: Joe asked to click a
# gallery image to open it full-size). Reuses each thumbnail's own data-URI <img src> instead of
# duplicating the base64 payload into a JS array, so the lightbox adds no bytes toward the
# raw-byte budget this script already caps.
_LIGHTBOX_CSS = (
    ".gallery-img{cursor:pointer}"
    "#lightbox{display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);"
    "align-items:center;justify-content:center;z-index:1000}"
    "#lightbox.open{display:flex}"
    "#lightbox img{max-width:90vw;max-height:90vh}"
    "#lightbox .lightbox-arrow{position:absolute;top:50%;transform:translateY(-50%);"
    "font-size:3rem;color:#fff;cursor:pointer;user-select:none;padding:0 24px}"
    ".lightbox-prev{left:0}.lightbox-next{right:0}"
    "#lightbox .lightbox-close{position:absolute;top:16px;right:24px;font-size:2rem;"
    "color:#fff;cursor:pointer;user-select:none}"
)

_LIGHTBOX_HTML = (
    '<div id="lightbox" onclick="lbBackdropClick(event)">'
    '<span class="lightbox-close" onclick="closeLightbox()">&times;</span>'
    '<span class="lightbox-arrow lightbox-prev" onclick="event.stopPropagation();lbNav(-1)">'
    "&#8249;</span>"
    '<img id="lightbox-img" src="" alt="">'
    '<span class="lightbox-arrow lightbox-next" onclick="event.stopPropagation();lbNav(1)">'
    "&#8250;</span>"
    "</div>"
    "<script>"
    "var lbIndex=0;"
    "function lbImgs(){return document.querySelectorAll('.gallery-img');}"
    "function openLightbox(i){"
    "lbIndex=i;"
    "document.getElementById('lightbox-img').src=lbImgs()[i].src;"
    "document.getElementById('lightbox').classList.add('open');"
    "}"
    "function closeLightbox(){document.getElementById('lightbox').classList.remove('open');}"
    "function lbNav(delta){"
    "var n=lbImgs().length;"
    "lbIndex=(lbIndex+delta+n)%n;"
    "document.getElementById('lightbox-img').src=lbImgs()[lbIndex].src;"
    "}"
    "function lbBackdropClick(e){if(e.target.id==='lightbox')closeLightbox();}"
    "document.addEventListener('keydown',function(e){"
    "var lb=document.getElementById('lightbox');"
    "if(!lb.classList.contains('open'))return;"
    "if(e.key==='Escape')closeLightbox();"
    "else if(e.key==='ArrowLeft')lbNav(-1);"
    "else if(e.key==='ArrowRight')lbNav(1);"
    "});"
    "</script>"
)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "page"


def collect_images(paths):
    """Expands directories into their image files (sorted); keeps file args
    as-is, same convention as render_markdown.py's collect_md_files."""
    files = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(q for q in p.iterdir() if q.suffix.lower() in IMAGE_EXTS))
        else:
            files.append(p)
    return files


def build_gallery_html(files, title, budget_bytes):
    """Caps by RAW byte size before base64 (which adds ~33%), so the budget
    lands under the endpoint's ~2MB cap. Once one file would push the running
    total over budget, it and every file after it are dropped - never
    truncate what made it in, never let a later POST hit 413."""
    included, dropped = [], []
    used = 0
    over_budget = False
    for f in files:
        size = f.stat().st_size
        if over_budget or used + size > budget_bytes:
            dropped.append(f)
            over_budget = True
            continue
        used += size
        included.append(f)

    figs = []
    for idx, f in enumerate(included):
        mime = mimetypes.guess_type(str(f))[0] or "image/png"
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        figs.append(
            f'<figure><img class="gallery-img" data-idx="{idx}" '
            f'onclick="openLightbox({idx})" '
            f'src="data:{mime};base64,{b64}" style="max-width:100%">'
            f"<figcaption>{html_mod.escape(f.name)}</figcaption></figure>"
        )

    lightbox = _LIGHTBOX_HTML if included else ""

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{html_mod.escape(title)}</title>"
        f"<style>{_LIGHTBOX_CSS}</style>"
        "</head>"
        '<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;'
        'background:#fbfcfd;margin:0;padding:24px">'
        f"<h1>{html_mod.escape(title)}</h1>"
        + "".join(figs)
        + lightbox
        + "</body></html>"
    )
    return page, included, dropped


class ManifestError(Exception):
    """A manifest problem the caller can fix; the message names the item and shot at fault."""


# Section layout for the manifest branch. Shots sit side by side and shrink to fit, so a row of
# phone-width before/after captures stays visible without horizontal scrolling.
_PAIRS_CSS = (
    "section.item{margin:0 0 32px;padding:16px;border:1px solid #d8dde3;border-radius:8px;"
    "background:#fff}"
    "section.item h2{margin:0 0 4px;font-size:1.15rem}"
    ".badge{display:inline-block;min-width:1.6em;padding:0 .4em;margin-right:8px;"
    "border-radius:1em;background:#1f2937;color:#fff;text-align:center;font-size:.95em}"
    "p.note{margin:0 0 12px;color:#4b5563}"
    ".shots{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}"
    ".shots figure{flex:1 1 0;min-width:140px;max-width:360px;margin:0}"
    ".shots figcaption{font-weight:600;margin-bottom:6px;font-size:.9rem}"
    ".shots img{width:100%;border:1px solid #d8dde3}"
)


def load_manifest(path):
    """Reads and validates a manifest: a JSON list of items, or {"title": ..., "items": [...]}.
    Each item is {id, title, note?, shots: [[caption, path], ...]}; shot paths resolve against
    the manifest's own directory. Returns (title_or_None, items) with shot paths as Path objects.
    Every problem names the item and shot so a 14-item manifest is fixable from one message."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestError(f"manifest is not valid JSON: {path}: {e}")
    title = None
    if isinstance(data, dict):
        title = data.get("title")
        data = data.get("items")
    if not isinstance(data, list) or not data:
        raise ManifestError(f"manifest needs a non-empty list of items: {path}")

    items, seen = [], set()
    for n, raw in enumerate(data, 1):
        if not isinstance(raw, dict):
            raise ManifestError(f"item #{n}: expected an object, got {type(raw).__name__}")
        item_id = str(raw.get("id") or "").strip()
        if not item_id:
            raise ManifestError(f"item #{n}: missing 'id'")
        if item_id in seen:
            raise ManifestError(f"item '{item_id}': duplicate id")
        seen.add(item_id)
        if not str(raw.get("title") or "").strip():
            raise ManifestError(f"item '{item_id}': missing 'title'")
        shots_raw = raw.get("shots")
        if not isinstance(shots_raw, list) or not shots_raw:
            raise ManifestError(f"item '{item_id}': 'shots' must be a non-empty list of [caption, path]")
        shots = []
        for s in shots_raw:
            if not (isinstance(s, (list, tuple)) and len(s) == 2 and all(isinstance(x, str) for x in s)):
                raise ManifestError(f"item '{item_id}': each shot must be [caption, path], got {s!r}")
            shot_path = Path(s[1])
            if not shot_path.is_absolute():
                shot_path = path.resolve().parent / shot_path
            if not shot_path.is_file():
                raise ManifestError(f"item '{item_id}' shot '{s[0]}': file not found: {shot_path}")
            if shot_path.suffix.lower() not in IMAGE_EXTS:
                raise ManifestError(f"item '{item_id}' shot '{s[0]}': not an image file: {shot_path}")
            shots.append((s[0], shot_path))
        items.append(
            {"id": item_id, "title": str(raw["title"]), "note": str(raw.get("note") or ""), "shots": shots}
        )
    return title, items


def convert_to_webp(src, tmp_dir):
    """Returns (mime, bytes) for `src`, re-encoded to WebP via ffmpeg when that is smaller. PNG
    screenshots shrink several-fold, which is what lets a 14-item gallery fit the ~2MB cap. Falls
    back to the original bytes when ffmpeg is missing or fails; gif/webp are never re-encoded
    (a gif may be animated)."""
    mime = mimetypes.guess_type(str(src))[0] or "image/png"
    original = src.read_bytes()
    ffmpeg = shutil.which("ffmpeg")
    if src.suffix.lower() not in {".png", ".jpg", ".jpeg"} or not ffmpeg:
        return mime, original
    out = Path(tmp_dir) / f"{len(list(Path(tmp_dir).iterdir()))}.webp"
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-y", "-i", str(src), "-c:v", "libwebp", "-quality", "80", str(out)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not out.is_file():
        print(f"warning: ffmpeg could not convert {src.name}, using the original", file=sys.stderr)
        return mime, original
    converted = out.read_bytes()
    if len(converted) >= len(original):
        return mime, original
    return "image/webp", converted


def build_manifest_html(items, title, budget_bytes, convert=convert_to_webp):
    """Renders one numbered section per item with its labelled shots side by side. The budget is
    enforced per item, not per shot: from the first item that would overflow, it and every item
    after it are dropped whole, so a before is never shown without its after."""
    included, dropped = [], []
    used = 0
    over_budget = False
    sections = []
    img_idx = 0
    taken_ids = set()
    with tempfile.TemporaryDirectory() as tmp_dir:
        for item in items:
            # Assigned for every item in manifest order, before any budget drop, so an item's
            # anchor does not shift with the budget.
            base_id = f"item-{slugify(item['id'])}"
            section_id, n = base_id, 1
            while section_id in taken_ids:
                n += 1
                section_id = f"{base_id}-{n}"
            taken_ids.add(section_id)

            encoded = [(cap, *convert(p, tmp_dir)) for cap, p in item["shots"]]
            size = sum(len(b) for _, _, b in encoded)
            if size > budget_bytes:
                # The dropped-items follow-up moves leftovers into a second manifest; an item
                # that cannot fit even alone would be dropped again every rerun, never converging.
                raise ManifestError(
                    f"item '{item['id']}': its shots alone are {size} bytes, over the whole "
                    f"{budget_bytes}-byte budget; raise --budget-mb or use smaller shots"
                )
            if over_budget or used + size > budget_bytes:
                dropped.append(item["id"])
                over_budget = True
                continue
            used += size
            included.append(item["id"])
            figs = []
            for cap, mime, data in encoded:
                b64 = base64.b64encode(data).decode("ascii")
                figs.append(
                    f"<figure><figcaption>{html_mod.escape(cap)}</figcaption>"
                    f'<img class="gallery-img" data-idx="{img_idx}" onclick="openLightbox({img_idx})" '
                    f'src="data:{mime};base64,{b64}" alt="{html_mod.escape(item["title"] + " - " + cap)}">'
                    "</figure>"
                )
                img_idx += 1
            note = f'<p class="note">{html_mod.escape(item["note"])}</p>' if item["note"] else ""
            sections.append(
                f'<section class="item" id="{section_id}">'
                f'<h2><span class="badge">{len(included)}</span>{html_mod.escape(item["title"])}</h2>'
                f'{note}<div class="shots">{"".join(figs)}</div></section>'
            )

    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{html_mod.escape(title)}</title>"
        f"<style>{_LIGHTBOX_CSS}{_PAIRS_CSS}</style>"
        "</head>"
        '<body style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;'
        'background:#fbfcfd;margin:0;padding:24px">'
        f"<h1>{html_mod.escape(title)}</h1>"
        + "".join(sections)
        + (_LIGHTBOX_HTML if included else "")
        + "</body></html>"
    )
    return page, included, dropped


def render_url(render_id, base=RENDER_CHECK_ENDPOINT):
    """/hooks/preview-render/<id> serves a posted page outside the panel; the one place that URL
    is formed, shared by --check and the post-response iframe URL."""
    return f"{base.rstrip('/')}/{render_id}"


def render_url_from_response(status, body, base=RENDER_CHECK_ENDPOINT):
    """The inline-card iframe URL for a successful POST, or None. The daemon answers 200
    {"id": ...}; /hooks/preview-render/<id> serves that same page outside the panel."""
    if status != 200:
        return None
    try:
        render_id = json.loads(body).get("id")
    except (json.JSONDecodeError, AttributeError):
        return None
    return render_url(render_id, base) if render_id else None


def default_slug(paths):
    first = paths[0]
    base = first.name if first.is_dir() else first.stem
    return slugify(base)


def default_title(paths):
    first = paths[0]
    name = first.name if first.is_dir() else first.stem
    return name.replace("-", " ").replace("_", " ")


def post_preview(html_text, title, slug, endpoint=ENDPOINT):
    """POSTs the same body shape documented in preview/SKILL.md's Steps
    section. Returns (status, body) - status is None on connection failure
    (Conductor unreachable), matching the skill's own fallback branch."""
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    body = json.dumps(
        {
            "title": title,
            "slug": slug,
            "html": html_text,
            "source": "terminal",
            "session_id": session_id,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        return None, str(e.reason)


# Loads a URL headless via the same shared chromium resolver screenshot-helper.cjs uses, and
# reports a page error. Guards the 2026-10-03 incident: a doc that rendered fine from file://
# threw an inline-script parse error only once served through the panel's own page.
_PAGE_ERROR_CHECK_JS = """
const { getChromium } = require(process.argv[1]);
const url = process.argv[2];
(async () => {
  const chromium = getChromium();
  const browser = await chromium.launch();
  const page = await browser.newPage();
  let pageError = null;
  page.on('pageerror', (err) => { pageError = pageError || err.message; });
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  } catch (e) {
    pageError = pageError || e.message;
  }
  await browser.close();
  if (pageError) {
    console.error('PAGE_ERROR: ' + pageError);
    process.exitCode = 1;
    return;
  }
  console.log('PAGE_OK');
})();
"""


def post_render_check(html_text, endpoint=RENDER_CHECK_ENDPOINT):
    """POSTs to the render-check hook (distinct from /hooks/preview - this one never shows up in
    the panel) and returns its parsed {"id": ...} response, for --check to then load headless."""
    body = json.dumps({"html": html_text}).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def check_rendered_page(url, resolver_path=_RESOLVER_PATH, timeout=30):
    """Loads `url` in headless chromium and returns (ok, message). ok is False on either a page
    error or a chromium-launch failure (message then explains why, e.g. playwright missing)."""
    try:
        proc = subprocess.run(
            ["node", "-e", _PAGE_ERROR_CHECK_JS, str(resolver_path), url],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return False, "node not found on PATH, cannot run the headless render check"
    except subprocess.TimeoutExpired:
        return False, f"headless render check timed out after {timeout}s"
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, (proc.stderr or proc.stdout).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", nargs="*", help="Image file(s)/directory, or a single existing .html file"
    )
    parser.add_argument(
        "--manifest",
        help="JSON of before/after items [{id, title, note, shots: [[caption, path], ...]}]; "
        "builds numbered paired sections with WebP-converted shots instead of a flat gallery",
    )
    parser.add_argument("--slug")
    parser.add_argument("--title")
    parser.add_argument("--budget-mb", type=float, default=DEFAULT_BUDGET_MB)
    parser.add_argument("--out", help="Write the built gallery HTML here (default: sibling file)")
    parser.add_argument(
        "--post", action="store_true", help="POST the built/given HTML to the preview endpoint"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Before posting, load the built HTML headless and fail if it throws a page error",
    )
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths]
    for p in paths:
        if not p.exists():
            print(f"error: path does not exist: {p}", file=sys.stderr)
            sys.exit(1)
    if args.manifest and paths:
        print("error: give either --manifest or image paths, not both", file=sys.stderr)
        sys.exit(1)
    if not args.manifest and not paths:
        print("error: give image paths, an .html file, or --manifest", file=sys.stderr)
        sys.exit(1)

    is_html_push = len(paths) == 1 and paths[0].is_file() and paths[0].suffix.lower() == ".html"

    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_file():
            print(f"error: manifest does not exist: {manifest_path}", file=sys.stderr)
            sys.exit(1)
        try:
            manifest_title, items = load_manifest(manifest_path)
        except ManifestError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        title = args.title or manifest_title or manifest_path.stem.replace("-", " ").replace("_", " ")
        slug = args.slug or slugify(manifest_path.stem)
        budget_bytes = int(args.budget_mb * 1024 * 1024)
        try:
            html_text, included, dropped = build_manifest_html(items, title, budget_bytes)
        except ManifestError as e:
            print(f"error: {e}", file=sys.stderr)
            sys.exit(1)
        out_path = Path(args.out) if args.out else manifest_path.parent / f"{slug}-gallery.html"
        out_path.write_text(html_text, encoding="utf-8")
        print(f"out: {out_path.resolve()}")
        print(f"included: {len(included)} dropped: {dropped}")
        if dropped:
            print(
                f"follow-up: move the dropped items into a second manifest and rerun with "
                f'--slug {slug}-2 --title "{title} (2)" --post'
            )
    elif is_html_push:
        html_path = paths[0]
        html_text = html_path.read_text(encoding="utf-8")
        title = args.title or html_path.stem.replace("-", " ").replace("_", " ")
        slug = args.slug or slugify(html_path.stem)
        print(f"out: {html_path.resolve()}")
    else:
        files = collect_images(paths)
        files = [f for f in files if f.suffix.lower() in IMAGE_EXTS]
        if not files:
            print("error: no image files found in the given paths", file=sys.stderr)
            sys.exit(1)

        title = args.title or default_title(paths)
        slug = args.slug or default_slug(paths)
        budget_bytes = int(args.budget_mb * 1024 * 1024)
        # The follow-up below reruns the dropped files; one that cannot fit even alone would be
        # dropped again every rerun, so it is an error up front instead.
        oversize = [f for f in files if f.stat().st_size > budget_bytes]
        if oversize:
            print(
                f"error: {oversize[0].name} alone is {oversize[0].stat().st_size} bytes, over the whole "
                f"{budget_bytes}-byte budget; raise --budget-mb or use a smaller image",
                file=sys.stderr,
            )
            sys.exit(1)
        html_text, included, dropped = build_gallery_html(files, title, budget_bytes)

        if args.out:
            out_path = Path(args.out)
        else:
            first = paths[0]
            parent = first if first.is_dir() else first.parent
            out_path = parent / f"{slug}-gallery.html"
        out_path.write_text(html_text, encoding="utf-8")

        print(f"out: {out_path.resolve()}")
        dropped_names = [f.name for f in dropped]
        print(f"included: {len(included)} dropped: {dropped_names}")
        if dropped:
            remainder = " ".join(f'"{f}"' for f in dropped)
            script = Path(__file__).resolve()
            print(
                f"follow-up: python \"{script}\" {remainder} "
                f'--slug {slug}-2 --title "{title} (2)" --post'
            )

    if args.check:
        try:
            render_resp = post_render_check(html_text)
        except (urllib.error.URLError, OSError) as e:
            print(f"check: could not reach render-check endpoint: {e}", file=sys.stderr)
            sys.exit(1)
        render_id = render_resp.get("id")
        if not render_id:
            print(f"check FAILED: render-check endpoint returned no id: {render_resp}", file=sys.stderr)
            sys.exit(1)
        check_url = render_url(render_id)
        ok, message = check_rendered_page(check_url)
        if not ok:
            print(f"check FAILED: {message}", file=sys.stderr)
            sys.exit(1)
        print(f"check OK: {check_url}")

    if args.post:
        status, resp_body = post_preview(html_text, title, slug)
        print(f"HTTP {status}: {resp_body}")
        posted_url = render_url_from_response(status, resp_body)
        if posted_url:
            print(f"render-url: {posted_url}")


if __name__ == "__main__":
    main()
