"""Self-test for skills/screenshot/measure-box.py.

Run directly: python tools/test_screenshot_measure.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Todo 1012: measuring a rendered box's geometry from a screenshot (the
canvas-rendered equivalent of getBoundingClientRect, for surfaces like
Flutter web/CanvasKit with no DOM box to query) was hand-rolled fresh every
time, and the first hand-rolled attempt (a column scan) is the one that
fails - antialiased glyph edges match a column scan's colour tolerance and
return bogus one-pixel runs. This suite synthesizes a PNG with Pillow
(already a project dependency, no browser involved) containing two outlined
boxes of known, DIFFERENT heights (48px and 45px, the exact defect size
named in the todo) and asserts the row-scan-plus-pairing algorithm recovers
both heights correctly - runs fully offline, no browser needed.
"""
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "screenshot" / "measure-box.py"
TIMEOUT_SECONDS = 30
BORDER_COLOR = (58, 123, 213)  # #3a7bd5

fails = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'} {label}")
    if not condition:
        fails.append(label)
        if detail:
            print(f"  {detail}")


def load_module():
    spec = importlib.util.spec_from_file_location("measure_box", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_fixture(path: Path) -> None:
    """Two outlined boxes, same width (>= default --min-run), different
    x-bands so they measure as separate boxes, and different heights (48 vs
    45) reproducing the exact defect the todo's Context section describes."""
    im = Image.new("RGB", (400, 90), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    # height 48: bottom - top + 1 == 48
    draw.rectangle([20, 10, 139, 57], outline=BORDER_COLOR, width=2)
    # height 45: a separate x-band, so it does not merge with the box above
    draw.rectangle([200, 10, 319, 54], outline=BORDER_COLOR, width=2)
    im.save(path)


def test_script_exists():
    check("script exists", SCRIPT.is_file(), f"missing: {SCRIPT}")


def test_measure_boxes_function(png_path: Path):
    mod = load_module()
    boxes = mod.measure_boxes(str(png_path), "#3a7bd5", tol=14, min_run=60)
    heights = sorted(b["height"] for b in boxes)
    check(
        "detects exactly two boxes",
        len(boxes) == 2,
        f"boxes={boxes}",
    )
    check(
        "recovers the 48px and 45px heights from the fixture",
        heights == [45, 48],
        f"heights={heights}",
    )


def test_named_color_rejected_cleanly():
    mod = load_module()
    try:
        mod.parse_color("not-a-color")
        ok = False
    except ValueError:
        ok = True
    check("unrecognized colour raises ValueError", ok)


def test_cli_expect_height(png_path: Path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(png_path), "--color", "#3a7bd5", "--expect-height", "48"],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )
    check("CLI exits 0 when a box matches --expect-height", proc.returncode == 0, proc.stdout + proc.stderr)
    check("CLI prints PASS line", "PASS:" in proc.stdout, proc.stdout)

    proc_fail = subprocess.run(
        [sys.executable, str(SCRIPT), str(png_path), "--color", "#3a7bd5", "--expect-height", "999"],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )
    check("CLI exits 1 when no box matches --expect-height", proc_fail.returncode == 1, proc_fail.stdout + proc_fail.stderr)
    check("CLI prints FAIL line", "FAIL:" in proc_fail.stdout, proc_fail.stdout)


def test_crop_window(png_path: Path):
    mod = load_module()
    # Crop to just the left box's region - only one box should be detected.
    boxes = mod.measure_boxes(str(png_path), "#3a7bd5", tol=14, min_run=60, crop=(0, 0, 160, 90))
    check("crop window isolates a single box", len(boxes) == 1, f"boxes={boxes}")


def main() -> int:
    test_script_exists()
    with tempfile.TemporaryDirectory(prefix="measure_box_test_") as tmp_str:
        png_path = Path(tmp_str) / "fixture.png"
        make_fixture(png_path)
        test_measure_boxes_function(png_path)
        test_named_color_rejected_cleanly()
        test_cli_expect_height(png_path)
        test_crop_window(png_path)

    if fails:
        print(f"FAIL: {len(fails)} case(s) failed: {fails}")
        return 1
    print("OK: all measure-box.py cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
