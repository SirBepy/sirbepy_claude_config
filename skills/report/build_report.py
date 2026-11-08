#!/usr/bin/env python3
"""Builds the fixed /report HTML page from a JSON spec.

Usage: python build_report.py <spec.json> [--out report.html] [--post] [--slug S] [--title T]

One layout, always: header, summary box, optional stat tiles, numbered sections, optional
next steps / open questions, optional sources footer. The page is self-contained on purpose:
inline CSS only, no script, no font/CDN/image fetch, no icon library. Conductor's "Publish to
claude.ai" uploads the page as-is, and a published artifact may be offline or sandboxed, so
anything that fetches would render differently for the teammate than for the dev.

Every string in the spec is HTML-escaped; the only markup a spec can produce is the fixed
layout plus `**bold**`, `` `code` `` and http(s) source links. Exit 1 names the field at fault.
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TONES = ("good", "warn", "bad", "neutral")
# Tone is never colour alone: each tone also prints a word, so a colour-blind reader and a
# greyscale print both still get the signal.
TONE_WORD = {"good": "OK", "warn": "Watch", "bad": "Problem", "neutral": ""}
BLOCK_KEYS = ("p", "bullets", "numbered", "table", "callout", "code")
PUSH_HTML = Path(__file__).resolve().parent.parent / "preview" / "push_html.py"


class SpecError(ValueError):
    pass


def esc(text) -> str:
    return html.escape(str(text), quote=True)


_INLINE = re.compile(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*")


def inline(text) -> str:
    # One left-to-right pass over the escaped text, so a span opened inside another is never
    # re-parsed: two sequential substitutions would interleave `**a `b** c`` into mis-nested tags.
    def span(m):
        return f"<code>{m.group(1)}</code>" if m.group(1) is not None else f"<strong>{m.group(2)}</strong>"

    return _INLINE.sub(span, esc(text))


def scalar(value, where: str) -> str:
    # A None or nested list would otherwise print as "None" / "[['x']]" in the page.
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise SpecError(f"{where} must be a string or number")
    return str(value)


def need_str(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{where} must be a non-empty string")
    return value


def need_list(value, where: str) -> list:
    if not isinstance(value, list) or not value:
        raise SpecError(f"{where} must be a non-empty list")
    return value


def tone_of(item: dict, where: str) -> str:
    tone = item.get("tone", "neutral")
    if tone not in TONES:
        raise SpecError(f"{where}.tone must be one of {', '.join(TONES)}, got {tone!r}")
    return tone


def render_block(block, where: str) -> str:
    if not isinstance(block, dict):
        raise SpecError(f"{where} must be an object")
    kinds = [k for k in BLOCK_KEYS if k in block]
    if len(kinds) != 1:
        raise SpecError(f"{where} needs exactly one of {', '.join(BLOCK_KEYS)}, got {kinds or 'none'}")
    kind = kinds[0]
    value = block[kind]
    if kind == "p":
        return f"<p>{inline(need_str(value, where + '.p'))}</p>"
    if kind in ("bullets", "numbered"):
        items = need_list(value, f"{where}.{kind}")
        tag = "ul" if kind == "bullets" else "ol"
        lis = "".join(f"<li>{inline(need_str(i, f'{where}.{kind}[{n}]'))}</li>" for n, i in enumerate(items))
        return f"<{tag}>{lis}</{tag}>"
    if kind == "code":
        return f"<pre><code>{esc(need_str(value, where + '.code'))}</code></pre>"
    if kind == "callout":
        tone = tone_of(block, where)
        word = TONE_WORD[tone]
        label = f'<span class="tw">{word}</span> ' if word else ""
        return f'<aside class="callout t-{tone}">{label}{inline(need_str(value, where + ".callout"))}</aside>'
    # table
    if not isinstance(value, dict):
        raise SpecError(f"{where}.table must be an object with columns and rows")
    cols = need_list(value.get("columns"), f"{where}.table.columns")
    rows = need_list(value.get("rows"), f"{where}.table.rows")
    cols = [scalar(c, f"{where}.table.columns[{n}]") for n, c in enumerate(cols)]
    head = "".join(f"<th>{inline(c)}</th>" for c in cols)
    body = []
    for n, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(cols):
            raise SpecError(f"{where}.table.rows[{n}] needs {len(cols)} cells to match the columns")
        # data-label feeds the phone layout, where each row becomes a labelled card.
        cells = "".join(
            f'<td data-label="{esc(c.replace("**", "").replace(chr(96), ""))}">'
            f'{inline(scalar(cell, f"{where}.table.rows[{n}][{k}]"))}</td>'
            for k, (c, cell) in enumerate(zip(cols, row))
        )
        body.append(f"<tr>{cells}</tr>")
    return f'<table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def render_stats(stats) -> str:
    tiles = []
    for n, s in enumerate(need_list(stats, "stats")):
        where = f"stats[{n}]"
        if not isinstance(s, dict):
            raise SpecError(f"{where} must be an object")
        tone = tone_of(s, where)
        word = TONE_WORD[tone]
        label = f'<span class="tw">{word}</span>' if word else ""
        note = f'<div class="note">{inline(s["note"])}</div>' if s.get("note") else ""
        tiles.append(
            f'<div class="tile t-{tone}"><div class="lbl">{inline(need_str(s.get("label"), where + ".label"))} {label}</div>'
            f'<div class="val">{inline(need_str(scalar(s.get("value", ""), where + ".value"), where + ".value"))}</div>{note}</div>'
        )
    return f'<section class="stats">{"".join(tiles)}</section>'


def render_sections(sections) -> str:
    out = []
    for n, sec in enumerate(need_list(sections, "sections"), 1):
        where = f"sections[{n - 1}]"
        if not isinstance(sec, dict):
            raise SpecError(f"{where} must be an object")
        heading = need_str(sec.get("heading"), where + ".heading")
        blocks = "".join(
            render_block(b, f"{where}.blocks[{i}]") for i, b in enumerate(need_list(sec.get("blocks"), where + ".blocks"))
        )
        out.append(f'<section class="sec"><h2><span class="num">{n}</span>{inline(heading)}</h2>{blocks}</section>')
    return "".join(out)


def render_list_section(title: str, items, where: str) -> str:
    lis = "".join(f"<li>{inline(need_str(i, f'{where}[{n}]'))}</li>" for n, i in enumerate(need_list(items, where)))
    return f'<section class="sec side"><h2>{esc(title)}</h2><ul>{lis}</ul></section>'


def render_sources(sources) -> str:
    lis = []
    for n, s in enumerate(need_list(sources, "sources")):
        where = f"sources[{n}]"
        if isinstance(s, str):
            lis.append(f"<li>{inline(s)}</li>")
            continue
        if not isinstance(s, dict):
            raise SpecError(f"{where} must be a string or an object with label and optional url")
        label = need_str(s.get("label"), where + ".label")
        url = s.get("url")
        if url is None:
            lis.append(f"<li>{inline(label)}</li>")
        elif isinstance(url, str) and re.match(r"https?://", url, re.I):
            lis.append(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{inline(label)}</a></li>')
        else:
            raise SpecError(f"{where}.url must start with http:// or https://")
    return f'<footer class="sources"><h2>Sources</h2><ul>{"".join(lis)}</ul></footer>'


CSS = """
:root{--ink:#16202a;--muted:#5d6874;--line:#e2e7ec;--bg:#f6f8fa;--card:#fff;--accent:#0b63f6;--code:#eef2f6;--good:#16794a;--warn:#a65f00;--bad:#b3261e;--neutral:#5d6874;color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--ink:#e6edf3;--muted:#9aa6b2;--line:#2b3540;--bg:#0d1117;--card:#151b23;--accent:#6ea8fe;--code:#222c37;--good:#4cc38a;--warn:#e5a13a;--bad:#ff7b72;--neutral:#9aa6b2}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 20px 72px}
header{margin-bottom:22px}
.kicker{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
h1{font-size:28px;line-height:1.2;letter-spacing:-.02em;margin:.25em 0 .2em}
.subtitle{color:var(--muted);font-size:16px;margin:0 0 8px}
.meta{color:var(--muted);font-size:12.5px}
.summary{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:16px 20px;margin:0 0 22px}
.summary h2{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 6px;border:0;padding:0}
.summary p{margin:.3em 0;font-size:16px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 26px}
.tile{background:var(--card);border:1px solid var(--line);border-top:3px solid var(--neutral);border-radius:10px;padding:12px 14px}
.tile.t-good{border-top-color:var(--good)}.tile.t-warn{border-top-color:var(--warn)}.tile.t-bad{border-top-color:var(--bad)}
.lbl{font-size:12px;color:var(--muted)}
.val{font-size:26px;font-weight:700;letter-spacing:-.02em;line-height:1.2}
.note{font-size:12px;color:var(--muted)}
.tw{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase}
.t-good .tw{color:var(--good)}.t-warn .tw{color:var(--warn)}.t-bad .tw{color:var(--bad)}
.sec{margin:0 0 28px}
h2{font-size:19px;letter-spacing:-.01em;margin:0 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.num{display:inline-block;min-width:26px;height:26px;line-height:26px;text-align:center;border-radius:13px;background:var(--accent);color:var(--bg);font-size:13px;margin-right:10px;vertical-align:2px}
p,li{margin:.4em 0}
ul,ol{padding-left:22px}
code{font:12.5px ui-monospace,Menlo,Consolas,monospace;background:var(--code);padding:1px 5px;border-radius:4px}
pre{background:var(--code);padding:12px 14px;border-radius:8px;overflow:auto}
pre code{padding:0;background:none}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px;background:var(--card)}
th,td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top}
th{background:var(--code);font-weight:650}
.callout{border:1px solid var(--line);border-left:4px solid var(--neutral);border-radius:8px;background:var(--card);padding:10px 14px;margin:12px 0}
.callout.t-good{border-left-color:var(--good)}.callout.t-warn{border-left-color:var(--warn)}.callout.t-bad{border-left-color:var(--bad)}
.sources{border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:13px}
.sources h2{font-size:13px;border:0;margin:0 0 4px;text-transform:uppercase;letter-spacing:.08em}
.sources a{color:var(--accent)}
/* Phone: a many-column table reads better as labelled cards than squeezed. */
@media (max-width:640px){
main{padding:20px 14px 56px}h1{font-size:23px}
table,thead,tbody,tr,td{display:block}thead{display:none}
tr{border:1px solid var(--line);border-radius:8px;margin:0 0 10px;padding:4px 0}
td{border:0;padding:5px 12px}td::before{content:attr(data-label) ": ";font-weight:650;color:var(--muted)}
}
@media print{body{background:#fff}.summary,.tile,.callout{break-inside:avoid}}
"""


def build(spec) -> str:
    if not isinstance(spec, dict):
        raise SpecError("spec must be a JSON object")
    title = need_str(spec.get("title"), "title")
    summary = spec.get("summary")
    paras = [summary] if isinstance(summary, str) else summary
    paras = need_list(paras, "summary")
    summary_html = "".join(f"<p>{inline(need_str(p, f'summary[{n}]'))}</p>" for n, p in enumerate(paras))
    meta = " · ".join(esc(spec[k]) for k in ("date", "author", "scope") if spec.get(k))
    parts = [
        '<header><div class="kicker">' + esc(spec.get("kicker") or "Report") + "</div>"
        f"<h1>{inline(title)}</h1>"
        + (f'<p class="subtitle">{inline(spec["subtitle"])}</p>' if spec.get("subtitle") else "")
        + (f'<div class="meta">{meta}</div>' if meta else "")
        + "</header>",
        f'<section class="summary"><h2>Summary</h2>{summary_html}</section>',
    ]
    if "stats" in spec:
        parts.append(render_stats(spec["stats"]))
    parts.append(render_sections(spec.get("sections")))
    if "next_steps" in spec:
        parts.append(render_list_section("Next steps", spec["next_steps"], "next_steps"))
    if "open_questions" in spec:
        parts.append(render_list_section("Open questions", spec["open_questions"], "open_questions"))
    if "sources" in spec:
        parts.append(render_sources(spec["sources"]))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="preview-template" content="bare">'
        f"<title>{esc(title)}</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>"
    )


def default_slug(title: str) -> str:
    return "report-" + (re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "untitled")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--post", action="store_true", help="push the built page via preview/push_html.py")
    ap.add_argument("--slug")
    ap.add_argument("--title")
    args = ap.parse_args(argv)

    try:
        # utf-8-sig: PowerShell 5.1 writes a BOM, which json.loads rejects.
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:  # ValueError: bad JSON or a non-UTF-8 file
        print(f"build_report: cannot read spec {args.spec}: {e}", file=sys.stderr)
        return 1
    try:
        page = build(spec)
    except SpecError as e:
        print(f"build_report: bad spec: {e}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path(args.spec).with_suffix(".html")
    try:
        out.write_text(page, encoding="utf-8")
    except OSError as e:
        print(f"build_report: cannot write {out}: {e}", file=sys.stderr)
        return 1
    print(out)
    if not args.post:
        return 0
    slug = args.slug or default_slug(spec["title"])
    cmd = [sys.executable, str(PUSH_HTML), str(out), "--slug", slug, "--title", args.title or spec["title"]]
    return subprocess.run(cmd, env=os.environ).returncode


if __name__ == "__main__":
    sys.exit(main())
