#!/usr/bin/env python3
"""Renders markdown file(s)/a directory into one self-contained HTML page:
sidebar nav per document, anchor nav per heading. Prints the output path
for /preview's existing POST step. Never inlines images (endpoint caps at
~2MB)."""
import argparse
import html as html_mod
import re
import sys
from pathlib import Path

import markdown

MD_EXTENSIONS = ["toc", "tables", "fenced_code", "sane_lists", "attr_list"]

CSS = """
:root{--ink:#11161c;--muted:#5b6570;--line:#e4e8ec;--bg:#fbfcfd;--accent:#0b63f6}
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
#wrap{display:grid;grid-template-columns:290px 1fr;min-height:100vh}
#side{position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--line);background:#fff;padding:22px 16px}
#side h1{font-size:15px;margin:0 0 4px;letter-spacing:-.01em}
#side .sub{font-size:12px;color:var(--muted);margin:0 0 16px}
.doc{display:none}
#filter{width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:7px;font-size:13px;margin-bottom:14px}
a.nav{display:flex;align-items:baseline;gap:8px;padding:7px 10px;border-radius:7px;text-decoration:none;color:var(--ink);font-size:13px}
a.nav:hover{background:#f2f5f8}
a.nav.active{background:#e8f0fe;color:var(--accent);font-weight:650}
a.nav .nt{flex:1}
a.doc-link{padding-left:10px}
a.toc-link{display:block;padding:4px 10px 4px 26px;font-size:12px;color:var(--muted);text-decoration:none;border-radius:6px}
a.toc-link:hover{background:#f2f5f8;color:var(--ink)}
a.toc-link.lvl-3{padding-left:38px}
#main{padding:34px 44px 120px;max-width:920px}
.doc.on{display:block}
.dochead{display:flex;gap:10px;align-items:center;margin-bottom:6px}
.docname{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:26px;letter-spacing:-.02em;margin:.3em 0 .5em}
h2{font-size:19px;letter-spacing:-.01em;margin:1.7em 0 .5em;padding-bottom:5px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:1.4em 0 .4em}
p,li{color:#1c242c}
code{font:12.5px ui-monospace,Menlo,monospace;background:#eef2f6;padding:1px 5px;border-radius:4px}
pre{background:#0f1720;color:#e6edf3;padding:14px 16px;border-radius:8px;overflow:auto}
pre code{background:none;color:inherit;padding:0}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top}
th{background:#f4f7fa;font-weight:650}
blockquote{margin:1em 0;padding:10px 16px;border-left:3px solid var(--accent);background:#f4f8ff;color:#26313c}
blockquote p{margin:.3em 0}
hr{border:0;border-top:1px solid var(--line);margin:2em 0}
a{color:var(--accent)}
ul,ol{padding-left:22px}
li{margin:.25em 0}
"""

SCRIPT = """
const docs=[...document.querySelectorAll('.doc')],links=[...document.querySelectorAll('a.nav')];
function show(slug){
  docs.forEach(d=>d.classList.toggle('on',d.id===slug));
  links.forEach(l=>l.classList.toggle('active',l.dataset.slug===slug));
  document.getElementById('main').scrollTo(0,0);
  window.scrollTo(0,0);
  if(location.hash.slice(1)!==slug) history.replaceState(null,'','#'+slug);
}
links.forEach(l=>l.addEventListener('click',e=>{
  if(l.dataset.slug){e.preventDefault();show(l.dataset.slug)}
}));
document.getElementById('filter').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();
  links.forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?'':'none');
});
const startDoc=docs.find(d=>d.id===location.hash.slice(1))?location.hash.slice(1):(docs[0]&&docs[0].id);
if(startDoc) show(startDoc);
"""


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "doc"


def collect_md_files(paths):
    """Expands directories into their .md files (recursive, sorted); keeps
    file args as-is. Order is preserved: each directory's files are sorted
    among themselves but the directories/files stay in argv order."""
    files = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.md")))
        else:
            files.append(p)
    return files


def build_page(files, page_title):
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    seen_slugs = set()
    nav_parts = []
    section_parts = []

    for f in files:
        text = f.read_text(encoding="utf-8")
        md.reset()
        body_html = md.convert(text)

        base_slug = slugify(f.stem)
        slug = base_slug
        n = 2
        while slug in seen_slugs:
            slug = f"{base_slug}-{n}"
            n += 1
        seen_slugs.add(slug)

        doc_title = f.stem.replace("-", " ").replace("_", " ")
        nav_parts.append(
            f'<a class="nav doc-link" href="#{slug}" data-slug="{slug}">'
            f'<span class="nt">{html_mod.escape(doc_title)}</span></a>'
        )
        for tok in getattr(md, "toc_tokens", []):
            if tok["level"] <= 3:
                nav_parts.append(
                    f'<a class="toc-link lvl-{tok["level"]}" '
                    f'href="#{slug}-{tok["id"]}">{html_mod.escape(tok["name"])}</a>'
                )

        # Namespace each doc's own anchor ids with its slug so two docs that
        # both have e.g. an "#overview" heading don't collide on one page.
        for tok in getattr(md, "toc_tokens", []):
            body_html = re.sub(
                rf'id="{re.escape(tok["id"])}"', f'id="{slug}-{tok["id"]}"', body_html, count=1
            )

        section_parts.append(
            f'<section id="{slug}" class="doc">'
            f'<div class="dochead"><span class="docname">{html_mod.escape(doc_title)}</span></div>'
            f"{body_html}</section>"
        )

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html_mod.escape(page_title)}</title><style>{CSS}</style></head><body>
<div id="wrap">
<aside id="side">
<h1>{html_mod.escape(page_title)}</h1>
<p class="sub">{len(files)} document{"s" if len(files) != 1 else ""}</p>
<input id="filter" placeholder="Filter" autocomplete="off">
{"".join(nav_parts)}
</aside>
<main id="main">{"".join(section_parts)}</main>
</div>
<script>{SCRIPT}</script></body></html>"""


def default_out(paths):
    first = paths[0]
    base = first.name if first.is_dir() else first.stem
    parent = first if first.is_dir() else first.parent
    return parent / f"{slugify(base)}-preview.html"


def default_title(paths):
    first = paths[0]
    name = first.name if first.is_dir() else first.stem
    return name.replace("-", " ").replace("_", " ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="One or more .md files, and/or directories of .md files")
    parser.add_argument("--title", help="Page title (default: derived from the first path)")
    parser.add_argument("--out", help="Output HTML path (default: sibling of the first path)")
    args = parser.parse_args()

    paths = [Path(p) for p in args.paths]
    for p in paths:
        if not p.exists():
            print(f"error: path does not exist: {p}", file=sys.stderr)
            sys.exit(1)

    files = collect_md_files(paths)
    if not files:
        print("error: no .md files found in the given paths", file=sys.stderr)
        sys.exit(1)

    title = args.title or default_title(paths)
    page = build_page(files, title)

    out_path = Path(args.out) if args.out else default_out(paths)
    out_path.write_text(page, encoding="utf-8")
    print(str(out_path.resolve()))


if __name__ == "__main__":
    main()
