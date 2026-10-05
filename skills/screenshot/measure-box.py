#!/usr/bin/env python3
"""Measures a rendered box's pixel geometry from a screenshot PNG - the
canvas-rendered equivalent of `getBoundingClientRect()` for a surface with
no DOM box to query (e.g. Flutter web/CanvasKit, which paints to <canvas>).

Scans each pixel ROW for a horizontal run of >= --min-run consecutive pixels
matching the target border colour, collapses vertically-contiguous runs in
the same x-band into one edge (an antialiased border is usually 1-3px tall),
then pairs consecutive edges in the same x-band into (top, bottom, height)
boxes. A per-column scan was tried first and rejected: antialiased glyph
edges match within any sane colour tolerance and return a dozen one-pixel
runs, never a usable box - rows do not have this problem because a solid
border run is much longer than any antialiased glyph stroke.

Usage:
    python measure-box.py <image.png> --color "#3a7bd5" [--min-run 60]
        [--tol 14] [--crop x0,y0,x1,y1] [--expect-height N]

Prints one line per detected box: "box x=<s>-<e> top=<t> bottom=<b> height=<h>".
With --expect-height, prints PASS/FAIL per box against that height and exits
1 if none match.
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    # Pillow is already a project dependency (see memory:
    # reference_character_creator_sources, PIL 12.2.0) - never add a new one.
    print("error: Pillow (PIL) is not installed in this interpreter", file=sys.stderr)
    sys.exit(1)

NAMED_COLORS = {
    "black": "#000000",
    "white": "#ffffff",
}


def parse_color(spec):
    spec = NAMED_COLORS.get(spec.lower(), spec)
    spec = spec.lstrip("#")
    if len(spec) == 3:
        spec = "".join(c * 2 for c in spec)
    if len(spec) != 6:
        raise ValueError(f"not a recognized colour: {spec!r} (use #rrggbb, #rgb, or a name)")
    return tuple(int(spec[i:i + 2], 16) for i in (0, 2, 4))


def near(pixel, target, tol):
    return all(abs(pixel[i] - target[i]) <= tol for i in range(3))


def find_row_runs(row_pixels, target, tol, min_run):
    """Runs of >= min_run consecutive matching pixels in one row."""
    runs = []
    start = None
    n = len(row_pixels)
    for x in range(n):
        if near(row_pixels[x], target, tol):
            if start is None:
                start = x
        else:
            if start is not None and x - start >= min_run:
                runs.append((start, x - 1))
            start = None
    if start is not None and n - start >= min_run:
        runs.append((start, n - 1))
    return runs


def x_overlap(a, b, slack=3):
    """Treats two x-ranges as the same band if they overlap, or come within
    slack px - a border's left/right edge can drift a pixel row to row from
    antialiasing without being a different band."""
    return not (a[1] + slack < b[0] or b[1] + slack < a[0])


def build_edge_bands(row_runs):
    """Collapses vertically-contiguous, x-overlapping runs into one edge
    band per border line (a solid border is 1-3px tall after antialiasing)."""
    active = []
    closed = []
    for y, runs in enumerate(row_runs):
        extended_ids = set()
        for run in runs:
            matched = False
            for band in active:
                if id(band) in extended_ids:
                    continue
                if x_overlap(band["x"], run):
                    band["x"] = run
                    band["y1"] = y
                    extended_ids.add(id(band))
                    matched = True
                    break
            if not matched:
                band = {"x": run, "y0": y, "y1": y}
                active.append(band)
                extended_ids.add(id(band))
        still_active = []
        for band in active:
            if id(band) in extended_ids:
                still_active.append(band)
            else:
                closed.append(band)
        active = still_active
    closed.extend(active)
    return closed


def pair_edges_into_boxes(edges):
    """Greedily pairs each edge with the next lower edge sharing its x-band
    into a (top, bottom, height) box - the top/bottom border lines of one
    rendered box."""
    edges = sorted(edges, key=lambda e: (e["x"][0], e["y0"]))
    boxes = []
    used = [False] * len(edges)
    for i, e in enumerate(edges):
        if used[i]:
            continue
        for j in range(i + 1, len(edges)):
            if used[j]:
                continue
            o = edges[j]
            if o["y0"] > e["y1"] and x_overlap(e["x"], o["x"]):
                # Outer bound of each edge band, not its midpoint: the box's
                # true top/bottom are the first and last border pixel, same
                # convention getBoundingClientRect uses (outer edge, not
                # border-thickness midpoint).
                top = e["y0"]
                bottom = o["y1"]
                x_start = min(e["x"][0], o["x"][0])
                x_end = max(e["x"][1], o["x"][1])
                boxes.append(
                    {
                        "x": (x_start, x_end),
                        "top": top,
                        "bottom": bottom,
                        "height": bottom - top + 1,
                    }
                )
                used[i] = used[j] = True
                break
    return boxes


def measure_boxes(image_path, color, tol=14, min_run=60, crop=None):
    im = Image.open(image_path).convert("RGB")
    if crop:
        im = im.crop(crop)
    width, height = im.size
    px = im.load()
    target = parse_color(color)

    row_runs = [
        find_row_runs([px[x, y] for x in range(width)], target, tol, min_run)
        for y in range(height)
    ]
    edges = build_edge_bands(row_runs)
    boxes = pair_edges_into_boxes(edges)
    boxes.sort(key=lambda b: (b["x"][0], b["top"]))
    return boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", help="Path to the screenshot PNG")
    parser.add_argument("--color", required=True, help="Target border colour: #rrggbb, #rgb, or a name")
    parser.add_argument("--tol", type=int, default=14, help="Per-channel colour tolerance (default 14)")
    parser.add_argument("--min-run", type=int, default=60, help="Minimum consecutive matching pixels per row (default 60)")
    parser.add_argument("--crop", help="Crop window x0,y0,x1,y1 before scanning")
    parser.add_argument("--expect-height", type=int, help="Print PASS/FAIL against this height")
    args = parser.parse_args()

    crop = None
    if args.crop:
        parts = [int(v) for v in args.crop.split(",")]
        if len(parts) != 4:
            print("error: --crop needs x0,y0,x1,y1", file=sys.stderr)
            sys.exit(1)
        crop = tuple(parts)

    try:
        boxes = measure_boxes(args.image, args.color, args.tol, args.min_run, crop)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if not boxes:
        print("no boxes detected - try a looser --tol or a shorter --min-run")
        sys.exit(1 if args.expect_height else 0)

    for b in boxes:
        x0, x1 = b["x"]
        print(f"box x={x0}-{x1} top={b['top']} bottom={b['bottom']} height={b['height']}")

    if args.expect_height is not None:
        matches = [b for b in boxes if b["height"] == args.expect_height]
        if matches:
            print(f"PASS: {len(matches)} box(es) match expected height {args.expect_height}")
        else:
            print(f"FAIL: no box matches expected height {args.expect_height}")
            sys.exit(1)


if __name__ == "__main__":
    main()
