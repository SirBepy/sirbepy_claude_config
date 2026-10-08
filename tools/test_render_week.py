"""Self-test for skills/clockify-reconciliator/scripts/render_week.cjs's HTML output.

Run directly: python tools/test_render_week.py
Exits 0 on all-pass, 1 on any failure.

Builds a 4-block fixture week whose durations land in each of render_week.cjs's
four height tiers at HOUR_PX=34 (full >=26px, time-only 14-26px, dot-glyph
8-14px, blank <8px), renders it for real via `node render_week.cjs`, and
asserts on the emitted HTML:

- todo 1048: Phosphor loads via the <script> tag (the form that actually
  injects the icon CSS), never the old <link rel="stylesheet"> that silently
  no-ops.
- todo 1036 (P2s): a sub-14px block keeps a visible dot glyph instead of a
  blank div, hour gridlines exist on the day columns, and .chip-old carries
  a non-default accent color.
- todo 1036 (P3): rendering a full Mon-Sun week where only Monday has
  entries puts the diagonal hatch class on the two empty weekend columns
  (Sat, Oct 3 / Sun, Oct 4) and nowhere else - the four empty weekdays in
  between (Tue-Fri) stay plain, since an empty weekday is the thing the
  hatch exists to NOT look like.
- the actual "safe path" this suite exists to pin down: a description
  containing HTML metacharacters comes out of escHtml escaped, never
  injected raw - nothing else in the skill exercises that against an
  adversarial string.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
import _testlib  # noqa: E402

SCRIPT = ROOT / "skills" / "clockify-reconciliator" / "scripts" / "render_week.cjs"
TIMEOUT_SECONDS = 60

# Each duration times HOUR_PX=34 lands in a different height tier:
#   50min -> 28.3px (full: time + desc)      30min -> 17.0px (time only)
#   20min -> 11.3px (dot glyph)              10min ->  5.7px (blank)
# The 20min block's desc carries an XSS/quote payload - it never renders at
# that tier (dot only), but it still reaches the tooltip's data-tip attribute,
# which is the actual escaping path under test.
ENTRIES = [
    {"date": "2026-09-28", "start": "09:00", "end": "09:50", "desc": "Normal task notes", "state": "old"},
    {"date": "2026-09-28", "start": "12:00", "end": "12:30", "desc": "Mid block", "state": "old"},
    {"date": "2026-09-28", "start": "10:00", "end": "10:20", "desc": 'Short <script>alert(1)</script> & "quoted"', "state": "edit"},
    {"date": "2026-09-28", "start": "11:00", "end": "11:10", "desc": "Tiny sliver", "state": "new"},
]

OLD_PHOSPHOR_LINK = '<link rel="stylesheet" href="https://unpkg.com/@phosphor-icons/web"></link>'
NEW_PHOSPHOR_SCRIPT = '<script src="https://unpkg.com/@phosphor-icons/web"></script>'


def render(tmp_dir: Path) -> str:
    entries_path = tmp_dir / "entries.json"
    out_path = tmp_dir / "out.html"
    entries_path.write_text(json.dumps(ENTRIES), encoding="utf-8")
    result = subprocess.run(
        ["node", str(SCRIPT), "--entries", str(entries_path), "--out", str(out_path),
         "--project", "TestProj", "--week-start", "2026-09-28", "--week-end", "2026-10-04",
         "--target-hours", "8"],
        capture_output=True, text=True, cwd=str(ROOT), timeout=TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError(f"render_week.cjs exited {result.returncode}\n{result.stdout}\n{result.stderr}")
    if '"ok":true' not in result.stdout:
        raise RuntimeError(f"render_week.cjs did not report ok:true\n{result.stdout}")
    return out_path.read_text(encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        html = render(Path(tmp))

    fails = []

    def check(ok: bool, label: str) -> None:
        if not _testlib.report(ok, label):
            fails.append(label)

    check(NEW_PHOSPHOR_SCRIPT in html, "Phosphor loads via <script>, the form that injects the icon CSS")
    check(OLD_PHOSPHOR_LINK not in html, "the old no-op <link rel=stylesheet> Phosphor tag is gone")

    check(html.count('class="v2-block ') == 4, "all four fixture blocks render a .v2-block div")
    check(html.count('class="v2-time"') == 2, "full and time-only tiers (50min, 30min) each show a time label")
    check(html.count('class="v2-dot"') == 1, "the 8-14px tier (20min block) keeps a visible dot glyph, not a blank div")

    check("repeating-linear-gradient(to bottom" in html, "day columns carry an hour-gridline background")
    check("34px" in html, "the gridline step matches HOUR_PX (34)")

    check(".chip-old { color:#8fd6ab; }" in html, ".chip-old carries the critique's non-default accent color")

    # 2026-09-28 is a Monday; the --week-end 2026-10-04 above runs the grid through that Sunday, so
    # Sat 10/3 and Sun 10/4 are the only two columns with zero entries AND a weekend date. Match the
    # div's class attribute specifically - "v2-colbody-hatch" alone also matches its own CSS rule
    # selector earlier in the same document, which would overcount by one.
    check(html.count('class="v2-colbody v2-colbody-hatch"') == 2, "exactly the two empty weekend columns (Sat, Sun) get the hatch class")
    check(html.count('class="v2-colbody"') == 5, "Monday (has data) and the four empty weekdays (Tue-Fri) stay plain, no hatch class")

    check('<script>alert(1)</script>' not in html, "raw HTML in a description never reaches the output unescaped")
    check('&lt;script&gt;alert(1)&lt;/script&gt;' in html, "the same description comes out escaped")
    check('&quot;quoted&quot;' in html, "a quote in a description is escaped, not left to break an attribute")
    check('&amp;' in html, "an ampersand in a description is escaped")

    if fails:
        print(f"\nFAILURES: {fails}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
