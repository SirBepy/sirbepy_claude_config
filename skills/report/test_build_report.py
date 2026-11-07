"""Self-test for build_report.py.

Run: python skills/report/test_build_report.py   (exit 0 = all pass)
"""

import contextlib
import importlib.util
import io
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("build_report", HERE / "build_report.py")
br = importlib.util.module_from_spec(spec)
spec.loader.exec_module(br)

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def raises(fn, needle):
    try:
        fn()
    except br.SpecError as e:
        return needle in str(e)
    return False


FULL = {
    "title": "Q3 <b>latency</b> report",
    "subtitle": "API p95 by route",
    "date": "2026-11-07",
    "summary": ["p95 fell **18%**.", "Two routes still slow."],
    "stats": [
        {"label": "p95", "value": "212 ms", "tone": "good", "note": "was 259 ms"},
        {"label": "Errors", "value": "0.4%", "tone": "bad"},
        {"label": "Routes", "value": "41"},
    ],
    "sections": [
        {"heading": "What changed", "blocks": [
            {"p": "Cache added to `/v1/users`."},
            {"bullets": ["one", "two"]},
            {"numbered": ["a", "b"]},
            {"callout": "Watch the cold start.", "tone": "warn"},
            {"code": "SELECT 1 < 2;"},
            {"table": {"columns": ["Route", "p95"], "rows": [["/a", "10"], ["/b", "20"]]}},
        ]},
    ],
    "next_steps": ["Ship it"],
    "open_questions": ["Keep the cache TTL at 60 s?"],
    "sources": ["local logs", {"label": "Grafana", "url": "https://example.com/d/1"}],
}

page = br.build(FULL)
check(page.startswith("<!doctype html>"), "full page is a complete document")
check("<script" not in page.lower(), "no script element")
check(not re.search(r"(src|srcset)\s*=|url\(\s*['\"]?https?:|@import|<link\b", page), "no external fetch (src, url(), @import, link)")
check("&lt;b&gt;latency&lt;/b&gt;" in page and "<b>latency" not in page, "title markup is escaped")
check("<strong>18%</strong>" in page, "bold inline works")
check("<code>/v1/users</code>" in page, "code inline works")
check("SELECT 1 &lt; 2;" in page, "code block is escaped")
check(page.count('<section class="sec"><h2><span class="num">') == 1, "sections are numbered")
check('data-label="Route"' in page, "table cells carry data-label for the phone layout")
check('<span class="tw">OK</span>' in page and '<span class="tw">Problem</span>' in page, "tone also prints a word")
check('rel="noopener noreferrer"' in page and 'href="https://example.com/d/1"' in page, "source link rendered with rel")
check('content="bare"' in page, "bare template meta present")
check(page.index("Summary") < page.index("What changed") < page.index("Next steps") < page.index("Sources"), "fixed section order")

minimal = br.build({"title": "T", "summary": "S", "sections": [{"heading": "H", "blocks": [{"p": "x"}]}]})
check("class=\"stats\"" not in minimal and "Next steps" not in minimal and "Sources" not in minimal, "optional parts omitted when absent")

check(raises(lambda: br.build({"summary": "S", "sections": []}), "title"), "missing title rejected")
check(raises(lambda: br.build({"title": "T", "sections": [{"heading": "H", "blocks": [{"p": "x"}]}]}), "summary"), "missing summary rejected")
check(raises(lambda: br.build({"title": "T", "summary": "S"}), "sections"), "missing sections rejected")
check(raises(lambda: br.build({**FULL, "sections": [{"heading": "H", "blocks": [{"p": "x", "bullets": ["y"]}]}]}), "exactly one"), "block with two kinds rejected")
check(raises(lambda: br.build({**FULL, "sections": [{"heading": "H", "blocks": [{"table": {"columns": ["a", "b"], "rows": [["1"]]}}]}]}), "2 cells"), "ragged table row rejected")
check(raises(lambda: br.build({**FULL, "stats": [{"label": "x", "value": "1", "tone": "purple"}]}), "tone"), "unknown tone rejected")
check(raises(lambda: br.build({**FULL, "sources": [{"label": "x", "url": "javascript:alert(1)"}]}), "http"), "non-http source url rejected")

two = br.build({"title": "T", "summary": "S", "sections": [
    {"heading": "One", "blocks": [{"p": "x"}]}, {"heading": "Two", "blocks": [{"p": "y"}]}]})
check(two.count('<span class="num">1</span>') == 1 and two.count('<span class="num">2</span>') == 1, "two sections are numbered 1 and 2")
check(br.inline("**a `b** c`") == "<strong>a `b</strong> c`", "interleaved bold and code never mis-nest")
check(br.inline("`x **y` z**") == "<code>x **y</code> z**", "code wins when it opens first")
quoted = br.build({"title": "T", "summary": "S", "sections": [{"heading": "H", "blocks": [
    {"table": {"columns": ['a"><i>', "**p95**"], "rows": [["1", "2"]]}}]}]})
check('data-label="a&quot;&gt;&lt;i&gt;"' in quoted and 'data-label="p95"' in quoted, "data-label is escaped and carries no markdown markers")
check(raises(lambda: br.build({**FULL, "sections": [{"heading": "H", "blocks": [{"table": {"columns": ["a"], "rows": [[None]]}}]}]}), "string or number"), "None table cell rejected")
check(raises(lambda: br.build({**FULL, "stats": [{"label": "x", "value": None}]}), "string or number"), "None stat value rejected")
check("HTTPS://example.com/x" in br.build({**FULL, "sources": [{"label": "x", "url": "HTTPS://example.com/x"}]}), "uppercase URL scheme accepted")
check("color:var(--bg)" in br.CSS, "section badge text follows the theme so dark mode keeps contrast")

check(br.default_slug("Q3 Latency: report!") == "report-q3-latency-report", "slug derived from title")
check(br.default_slug("!!!") == "report-untitled", "slug fallback")

with tempfile.TemporaryDirectory() as tmp:
    good = Path(tmp) / "r.json"
    good.write_text(json.dumps(FULL), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = br.main([str(good)])
    check(code == 0 and (Path(tmp) / "r.html").is_file() and out.getvalue().strip().endswith("r.html"), "main writes html next to the spec and prints its path")

    bad = Path(tmp) / "bad.json"
    bad.write_text(json.dumps({"title": "T"}), encoding="utf-8")
    with contextlib.redirect_stderr(io.StringIO()) as err:
        code = br.main([str(bad)])
    check(code == 1 and "bad spec" in err.getvalue() and not (Path(tmp) / "bad.html").exists(), "bad spec exits 1 and writes nothing")

    latin = Path(tmp) / "latin.json"
    latin.write_bytes('{"title": "caf\u00e9"}'.encode("latin-1"))
    with contextlib.redirect_stderr(io.StringIO()) as err:
        code = br.main([str(latin)])
    check(code == 1 and "cannot read" in err.getvalue(), "non-UTF-8 spec exits 1 without a traceback")
    with contextlib.redirect_stderr(io.StringIO()) as err:
        code = br.main([str(good), "--out", str(Path(tmp) / "no-such-dir" / "r.html")])
    check(code == 1 and "cannot write" in err.getvalue(), "unwritable --out exits 1 without a traceback")
    with contextlib.redirect_stderr(io.StringIO()) as err:
        code = br.main([str(Path(tmp) / "nope.json")])
    check(code == 1 and "cannot read" in err.getvalue(), "missing spec file exits 1")

    bom = Path(tmp) / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf" + json.dumps(FULL).encode("utf-8"))
    with contextlib.redirect_stdout(io.StringIO()):
        code = br.main([str(bom)])
    check(code == 0 and (Path(tmp) / "bom.html").is_file(), "a spec saved with a BOM (PowerShell 5.1) builds")

print(f"\n{len(failures)} failure(s)" if failures else "\nall passed")
sys.exit(1 if failures else 0)
