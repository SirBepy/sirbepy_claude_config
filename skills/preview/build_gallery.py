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
import subprocess
import sys
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
        "paths", nargs="+", help="Image file(s)/directory, or a single existing .html file"
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

    is_html_push = len(paths) == 1 and paths[0].is_file() and paths[0].suffix.lower() == ".html"

    if is_html_push:
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
        render_url = f"{RENDER_CHECK_ENDPOINT.rstrip('/')}/{render_id}"
        ok, message = check_rendered_page(render_url)
        if not ok:
            print(f"check FAILED: {message}", file=sys.stderr)
            sys.exit(1)
        print(f"check OK: {render_url}")

    if args.post:
        status, resp_body = post_preview(html_text, title, slug)
        print(f"HTTP {status}: {resp_body}")


if __name__ == "__main__":
    main()
