#!/usr/bin/env python3
"""Renders markdown file(s)/a directory into one self-contained HTML page:
nav per document, anchor nav per heading (a sidebar on desktop, a collapsible
block at the top on a phone, where tables also become labelled cards). Prints
the output path for /preview's existing POST step. Never inlines images
(endpoint caps at ~2MB)."""
import argparse
import html as html_mod
import re
import sys
from pathlib import Path

import markdown

MD_EXTENSIONS = ["toc", "tables", "fenced_code", "sane_lists", "attr_list"]

CSS = """
:root{--ink:#11161c;--muted:#5b6570;--line:#e4e8ec;--bg:#fbfcfd;--accent:#0b63f6;--surface:#fff;--hover:#f2f5f8;--active:#e8f0fe;--text:#1c242c;--code-bg:#eef2f6;--th-bg:#f4f7fa;--quote-bg:#f4f8ff;--quote-ink:#26313c;--pre-bg:#0f1720;--pre-ink:#e6edf3;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--muted:#9aa6b2;--line:#2b3540;--bg:#0d1117;--accent:#6ea8fe;--surface:#151b23;--hover:#1f2833;--active:#1d2f4d;--text:#d5dde5;--code-bg:#222c37;--th-bg:#1b232c;--quote-bg:#14202f;--quote-ink:#c5d0db;--pre-bg:#070b10;--pre-ink:#e6edf3}}
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 -apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
#wrap{display:grid;grid-template-columns:290px 1fr;min-height:100vh}
#side{position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--line);background:var(--surface);padding:22px 16px}
#side h1{font-size:15px;margin:0 0 4px;letter-spacing:-.01em}
#side .sub{font-size:12px;color:var(--muted);margin:0 0 16px}
#navbox>summary{display:none}
.doc{display:none}
#filter{width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:7px;font-size:13px;margin-bottom:14px;background:var(--surface);color:var(--ink)}
a.nav{display:flex;align-items:baseline;gap:8px;padding:7px 10px;border-radius:7px;text-decoration:none;color:var(--ink);font-size:13px}
a.nav:hover{background:var(--hover)}
a.nav.active{background:var(--active);color:var(--accent);font-weight:650}
a.nav .nt{flex:1}
a.doc-link{padding-left:10px}
a.toc-link{display:block;padding:4px 10px 4px 26px;font-size:12px;color:var(--muted);text-decoration:none;border-radius:6px}
a.toc-link:hover{background:var(--hover);color:var(--ink)}
a.toc-link.lvl-3{padding-left:38px}
#main{padding:34px 44px 120px;max-width:920px}
.doc.on{display:block}
.dochead{display:flex;gap:10px;align-items:center;margin-bottom:6px}
.docname{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:26px;letter-spacing:-.02em;margin:.3em 0 .5em}
h2{font-size:19px;letter-spacing:-.01em;margin:1.7em 0 .5em;padding-bottom:5px;border-bottom:1px solid var(--line)}
h3{font-size:15px;margin:1.4em 0 .4em}
p,li{color:var(--text)}
code{font:12.5px ui-monospace,Menlo,monospace;background:var(--code-bg);padding:1px 5px;border-radius:4px}
pre{background:var(--pre-bg);color:var(--pre-ink);padding:14px 16px;border-radius:8px;overflow:auto}
pre code{background:none;color:inherit;padding:0}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:14px}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top}
th{background:var(--th-bg);font-weight:650}
blockquote{margin:1em 0;padding:10px 16px;border-left:3px solid var(--accent);background:var(--quote-bg);color:var(--quote-ink)}
blockquote p{margin:.3em 0}
hr{border:0;border-top:1px solid var(--line);margin:2em 0}
a{color:var(--accent)}
ul,ol{padding-left:22px}
li{margin:.25em 0}
#top{display:none}
/* Phone layout. Below 700px the 290px sidebar would leave the text column
   too narrow, and a many-column table reads better as cards than squeezed. */
@media (max-width:700px){
body{font-size:17px}
#wrap{display:block}
#side{position:static;height:auto;overflow:visible;border-right:0;border-bottom:1px solid var(--line);padding:14px 16px}
#side .sub{margin-bottom:10px}
#navbox>summary{display:block;padding:10px 12px;border:1px solid var(--line);border-radius:8px;font-size:15px;font-weight:650;cursor:pointer;list-style:none}
#navbox>summary::-webkit-details-marker{display:none}
#navbox>summary::after{content:"+";float:right}
#navbox[open]>summary{margin-bottom:12px}
#navbox[open]>summary::after{content:"-"}
#filter{font-size:16px;padding:10px 12px}
a.nav{font-size:15px;padding:10px}
a.toc-link{font-size:14px;padding-top:7px;padding-bottom:7px}
#main{padding:18px 16px 96px;max-width:none;overflow-wrap:anywhere}
h1{font-size:24px}
h2{font-size:21px}
h3{font-size:18px}
img{max-width:100%;height:auto}
code{white-space:normal;overflow-wrap:anywhere}
pre{max-width:100%;overflow-x:auto;overflow-wrap:normal}
pre code{white-space:pre;overflow-wrap:normal}
table{font-size:15px}
thead{display:none}
table,tbody,tr,td{display:block;width:100%}
tr{border:1px solid var(--line);border-radius:10px;margin:0 0 12px;padding:4px 12px;background:var(--surface)}
td{border:0;border-bottom:1px solid var(--line);padding:8px 0}
td:last-child{border-bottom:0}
td::before{content:attr(data-label);display:block;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
td.rank{display:none}
td[data-rank]{font-weight:650;font-size:17px}
td[data-rank]::before{content:attr(data-rank) ". ";display:inline;font-size:inherit;letter-spacing:0;text-transform:none;color:inherit}
#top{display:block;position:fixed;right:14px;bottom:14px;padding:10px 16px;border-radius:999px;background:var(--accent);color:var(--surface);font-size:14px;font-weight:650;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.3)}
}
"""

SCRIPT = """
const docs=[...document.querySelectorAll('.doc')],links=[...document.querySelectorAll('a.nav')];
const navBox=document.getElementById('navbox'),narrow=matchMedia('(max-width:700px)');
// Desktop keeps the nav always open (its summary is hidden); on a phone it starts collapsed.
function syncNav(){navBox.open=!narrow.matches}
syncNav();
narrow.addEventListener('change',syncNav);
navBox.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{if(narrow.matches)navBox.open=false}));
document.getElementById('top').addEventListener('click',e=>{e.preventDefault();window.scrollTo(0,0)});
function show(slug,init){
  docs.forEach(d=>d.classList.toggle('on',d.id===slug));
  links.forEach(l=>l.classList.toggle('active',l.dataset.slug===slug));
  document.getElementById('main').scrollTo(0,0);
  window.scrollTo(0,0);
  // On first paint a hash we add ourselves would make the browser scroll to that section after
  // load, which on a phone lands past the nav block at the top of the page.
  if(!init&&location.hash.slice(1)!==slug) history.replaceState(null,'','#'+slug);
}
links.forEach(l=>l.addEventListener('click',e=>{
  if(l.dataset.slug){e.preventDefault();show(l.dataset.slug)}
}));
document.getElementById('filter').addEventListener('input',e=>{
  const q=e.target.value.toLowerCase();
  links.forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?'':'none');
});
const startDoc=docs.find(d=>d.id===location.hash.slice(1))?location.hash.slice(1):(docs[0]&&docs[0].id);
if(startDoc) show(startDoc,true);
"""

TABLE_RE = re.compile(r"<table\b[^>]*>.*?</table>", re.S)
ROW_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.S)
CELL_RE = re.compile(r"<(t[hd])\b([^>]*)>(.*?)</\1>", re.S)
TAG_RE = re.compile(r"<[^>]+>")


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "doc"


def cell_text(inner):
    return html_mod.unescape(TAG_RE.sub("", inner)).strip()


def add_attr(attrs, name, value):
    """Appends name=value to a tag's attribute string; merges into an existing class."""
    value = html_mod.escape(value, quote=True)
    if name == "class":
        m = re.search(r'class="([^"]*)"', attrs)
        if m:
            return attrs[: m.start()] + f'class="{m.group(1)} {value}"' + attrs[m.end():]
    return f'{attrs} {name}="{value}"'


def label_table_cells(body_html):
    """Gives every <td> a data-label from its column's <th> so the phone CSS can
    turn rows into labelled cards. A leading "#" column is marked class="rank"
    and its value is copied to the next cell as data-rank, so the card title
    reads "1. Name" on a phone while desktop keeps the column. Tables with no
    <th> row are left alone."""

    def do_table(table_m):
        rows = ROW_RE.findall(table_m.group(0))
        headers = None
        for row in rows:
            ths = [cell_text(c.group(3)) for c in CELL_RE.finditer(row) if c.group(1) == "th"]
            if ths:
                headers = ths
                break
        if not headers:
            return table_m.group(0)
        has_rank = headers[0] == "#"

        def do_row(row_m):
            row = row_m.group(0)
            cells = list(CELL_RE.finditer(row))
            rank_text = cell_text(cells[0].group(3)) if cells and has_rank else ""
            idx = [-1]

            def do_cell(m):
                idx[0] += 1
                i, tag, attrs = idx[0], m.group(1), m.group(2)
                if has_rank and i == 0:
                    attrs = add_attr(attrs, "class", "rank")
                if tag == "td":
                    if i < len(headers) and headers[i]:
                        attrs = add_attr(attrs, "data-label", headers[i])
                    if has_rank and i == 1 and rank_text:
                        attrs = add_attr(attrs, "data-rank", rank_text)
                return f"<{tag}{attrs}>{m.group(3)}</{tag}>"

            return CELL_RE.sub(do_cell, row)

        return ROW_RE.sub(do_row, table_m.group(0))

    return TABLE_RE.sub(do_table, body_html)


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
        body_html = label_table_cells(md.convert(text))

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
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html_mod.escape(page_title)}</title><style>{CSS}</style></head><body>
<div id="wrap">
<aside id="side">
<h1>{html_mod.escape(page_title)}</h1>
<p class="sub">{len(files)} document{"s" if len(files) != 1 else ""}</p>
<details id="navbox" open>
<summary>Contents</summary>
<input id="filter" placeholder="Filter" autocomplete="off">
{"".join(nav_parts)}
</details>
</aside>
<main id="main">{"".join(section_parts)}</main>
</div>
<a id="top" href="#">Top</a>
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
