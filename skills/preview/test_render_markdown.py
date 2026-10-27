"""Self-test for the phone-responsive output of render_markdown.py.

Run: python skills/preview/test_render_markdown.py   (exit 0 = all pass)

Drives the real script as a subprocess against synthetic markdown and inspects the HTML it
writes. Set RENDER_MARKDOWN_SCRIPT to point the same cases at another copy of the renderer
(used to prove the cases fail against the pre-responsive version).
"""

import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

SCRIPT = Path(os.environ.get("RENDER_MARKDOWN_SCRIPT") or Path(__file__).resolve().parent / "render_markdown.py")
TIMEOUT_SECONDS = 60

failures = []

TABLE_MD = """# Hosts

| # | Provider | Region | Price | Cores | Notes |
|---|----------|--------|-------|-------|-------|
| 1 | OVHcloud | EU | 5 | 4 | cheap |
| 2 | Hetzner | DE | 6 | 8 | fast & loud |
"""


def check(cond, label, detail=""):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)
        if detail:
            print(f"  {detail}")


class TableCells(HTMLParser):
    """Collects each table as a list of rows; a row is a list of (tag, attrs dict, text)."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr" and self.tables:
            self.tables[-1].append([])
        elif tag in ("th", "td") and self.tables and self.tables[-1]:
            self._cell = [tag, dict(attrs), ""]
            self.tables[-1][-1].append(self._cell)

    def handle_endtag(self, tag):
        if tag in ("th", "td"):
            self._cell = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell[2] += data


def parse_tables(html):
    p = TableCells()
    p.feed(html)
    return p.tables


def render(root, name, files):
    """Writes {filename: markdown} into root/name and renders them; returns (proc, html)."""
    d = root / name
    d.mkdir()
    paths = []
    for fname, text in files.items():
        (d / fname).write_text(text, encoding="utf-8")
        paths.append(str(d / fname))
    out = d / "out.html"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *paths, "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    html = out.read_text(encoding="utf-8") if out.exists() else ""
    return proc, html


def test_viewport_meta(root):
    proc, html = render(root, "viewport", {"a.md": "# A\n\ntext\n"})
    check(proc.returncode == 0, "single doc renders", proc.stderr)
    check(
        '<meta name="viewport" content="width=device-width,initial-scale=1">' in html,
        "viewport meta is present",
    )


def test_table_labels(root):
    proc, html = render(root, "labels", {"t.md": TABLE_MD})
    tables = parse_tables(html)
    check(proc.returncode == 0 and len(tables) == 1, "6-column table renders as one table", proc.stderr)
    if not tables:
        return
    rows = tables[0]
    headers = [c[2] for c in rows[0]]
    check(headers == ["#", "Provider", "Region", "Price", "Cores", "Notes"], "header row has six columns", str(headers))
    body = rows[1:]
    check(len(body) == 2 and all(len(r) == 6 for r in body), "both body rows have six cells")
    for r in body:
        labels = [c[1].get("data-label") for c in r]
        check(labels == headers, "every td data-label matches its column header", str(labels))
    check(
        body[1][5][2] == "fast & loud" and "fast &amp; loud" in html,
        "cell content survives labelling, still escaped",
    )


def test_rank_column(root):
    proc, html = render(root, "rank", {"t.md": TABLE_MD})
    tables = parse_tables(html)
    if not tables:
        check(False, "rank table renders", proc.stderr)
        return
    rows = tables[0]
    check("rank" in rows[0][0][1].get("class", "").split(), "the # header cell is marked class=rank")
    for n, r in enumerate(rows[1:], start=1):
        check("rank" in r[0][1].get("class", "").split(), f"row {n}: the rank cell is marked class=rank")
        check(r[1][1].get("data-rank") == str(n), f"row {n}: the next cell carries data-rank={n}", str(r[1][1]))
        check("data-rank" not in r[2][1], f"row {n}: only the first data cell gets data-rank")
    check(
        re.search(r"td\[data-rank\]::before\{content:attr\(data-rank\)", html) is not None,
        "CSS turns data-rank into the card title prefix",
    )

    _, plain = render(root, "norank", {"t.md": "| Name | Qty |\n|---|---|\n| a | 1 |\n"})
    plain_rows = parse_tables(plain)[0]
    check(
        all("data-rank" not in c[1] and "rank" not in c[1].get("class", "") for r in plain_rows for c in r),
        "a table without a # column gets no rank markup",
    )
    check([c[1].get("data-label") for c in plain_rows[1]] == ["Name", "Qty"], "plain table still gets labels")


def test_multi_doc(root):
    files = {
        "alpha.md": "## Overview\n\ntext a\n",
        "beta.md": "## Overview\n\n| X | Y |\n|---|---|\n| 1 | 2 |\n",
        "gamma.md": "### Deep\n\ntext g\n",
    }
    proc, html = render(root, "multi", files)
    check(proc.returncode == 0, "three docs render", proc.stderr)
    for slug in ("alpha", "beta", "gamma"):
        check(f'<section id="{slug}" class="doc">' in html, f"section {slug} is present")
        check(f'class="nav doc-link" href="#{slug}" data-slug="{slug}"' in html, f"doc nav link {slug} is present")
    check('href="#alpha-overview"' in html and 'href="#beta-overview"' in html, "per-doc heading links stay namespaced")
    check('id="alpha-overview"' in html and 'id="beta-overview"' in html, "per-doc heading ids stay namespaced")
    check('id="filter"' in html and "function show(slug" in html, "filter box and doc switcher script are kept")
    check(
        re.search(r'<details id="navbox" open>.*id="filter".*href="#alpha".*</details>', html, re.S) is not None,
        "filter and nav links sit inside the collapsible nav block",
    )
    beta_table = parse_tables(html)[0]
    check([c[1].get("data-label") for c in beta_table[1]] == ["X", "Y"], "tables in a later doc are labelled too")


def test_h1_led_docs(root):
    # Python-Markdown nests every H2/H3 under a leading H1 as that token's children.
    files = {
        "one.md": "# One\n\n## Overview\n\ntext\n\n### Detail\n\nmore\n",
        "two.md": "# Two\n\n## Overview\n\ntext\n",
    }
    proc, html = render(root, "h1led", files)
    check(proc.returncode == 0, "two H1-led docs render", proc.stderr)
    check('href="#one-overview"' in html and 'href="#two-overview"' in html, "an H1-led doc's H2s are in the nav")
    check('class="toc-link lvl-3" href="#one-detail"' in html, "an H1-led doc's H3s are in the nav")
    check('id="one-overview"' in html and 'id="two-overview"' in html, "nested heading ids are namespaced per doc")
    check('id="overview"' not in html, "no bare nested heading id is left to collide across docs")

    proc, html = render(
        root,
        "inlinks",
        {"one.md": "# T\n\nSee [a](#a) and [site](https://x.test/#a).\n\n## A\n\ntext\n\n## One A\n\ntext\n"},
    )
    check('href="#one-a"' in html and 'href="#a"' not in html, "an in-doc #id link follows its renamed heading id")
    check('href="https://x.test/#a"' in html, "an external link's fragment is left alone")
    check(
        '<h2 id="one-a">A</h2>' in html and '<h2 id="one-one-a">One A</h2>' in html,
        "a heading whose id equals another's renamed id keeps its own id",
    )


def test_literal_id_text(root):
    # Prose that merely spells an id/href attribute is text, not markup: only real heading ids
    # and real <a href="#..."> links are namespaced.
    md = (
        "# T\n\n## Overview\n\n"
        'Write `id="overview"` or `href="#overview"` by hand, or [link](#overview).\n'
    )
    proc, html = render(root, "literal", {"one.md": md})
    check(proc.returncode == 0, "doc with literal id text renders", proc.stderr)
    check('<h2 id="one-overview">Overview</h2>' in html, "the real heading id is namespaced")
    check('<a href="#one-overview">link</a>' in html, "a real in-doc link is namespaced")
    check(
        "<code>id=\"overview\"</code>" in html or "<code>id=&quot;overview&quot;</code>" in html,
        "inline code spelling an id attribute is left unchanged",
    )
    check(
        "<code>href=\"#overview\"</code>" in html or "<code>href=&quot;#overview&quot;</code>" in html,
        "inline code spelling an href attribute is left unchanged",
    )
    check("one-overview&quot;" not in html and 'one-overview"</code>' not in html, "no literal text was rewritten")


def test_narrow_css(root):
    _, html = render(root, "css", {"t.md": TABLE_MD + "\n```\nlong code line\n```\n"})
    check("@media (max-width:700px)" in html, "the narrow media query exists")
    media = html.split("@media (max-width:700px)", 1)[-1]
    check("td::before{content:attr(data-label)" in media, "narrow CSS shows data-label on each cell")
    check("thead{display:none}" in media, "narrow CSS hides the table head")
    check("body{font-size:17px}" in media, "narrow body text is 17px")
    check("overflow-wrap:anywhere" in media, "narrow CSS wraps long words")
    check("pre{max-width:100%;overflow-x:auto" in media, "narrow pre scrolls inside itself")
    check("#wrap{display:block}" in media, "narrow layout drops the sidebar grid column")
    check('<a id="top" href="#">Top</a>' in html and "#top{display:block;position:fixed" in media, "a floating Top link exists on narrow")
    check("show(startDoc,true)" in html and "if(!init&&" in html, "first paint adds no hash (it would scroll a phone past the nav)")
    check("@media (prefers-color-scheme:dark)" in html, "a dark palette exists")
    check(
        "background:#fff" not in html and "background:#f2f5f8" not in html and "color:#1c242c" not in html,
        "base rules use variables, not hardcoded surface colours",
    )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        test_viewport_meta(root)
        test_table_labels(root)
        test_rank_column(root)
        test_multi_doc(root)
        test_h1_led_docs(root)
        test_literal_id_text(root)
        test_narrow_css(root)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall render_markdown tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
