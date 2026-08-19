"""Render-and-diff a built screenshot against a design tile: content bands,
gaps, ink margins and pixel samples, all normalized to LOGICAL px so a
capture taken at a different device-pixel-ratio than the design frame can
never be misread as a spacing/size defect. No network calls - both images
must already exist on disk (a locally rendered build, a design PNG export).

Subcommands:
  bands     Row-profile content bands for one image (logical y0-y1, height,
            gap-above, ink L/R margins).
  compare   Run `bands` on a design tile and a built screenshot, then print
            the delta table matched by band index.
  ink-box   Ink bounding box within a logical region (button/icon geometry,
            fill/corner color samples).
  sample    Pixel color at logical x,y (averaged over --radius).

Generalized from the throwaway measure.py/nav.py/colours.py scripts written
ad hoc in a zng-app session (todo 362) - see e2e/SKILL.md for the workflow
and the three Flutter-web capture gotchas this tool does not itself guard.
"""
import argparse
import json
import os

import numpy as np
from PIL import Image


def load(path):
    return np.array(Image.open(path).convert("RGB")).astype(int)


def scale_of(arr, logical_width):
    return arr.shape[1] / logical_width


def hexc(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(int(round(c)) for c in rgb))


def bg_color(arr):
    """Median of the four corners plus top-mid, 2px inset - robust to a stray
    icon/rule sitting in exactly one corner."""
    h, w, _ = arr.shape
    pts = [(2, 2), (2, w - 3), (h - 3, 2), (h - 3, w - 3), (2, w // 2)]
    return np.median(np.array([arr[y, x] for y, x in pts]), axis=0)


def apply_excludes(arr, excludes_px):
    """Zero out (set to background-diff-proof, i.e. drop) given pixel y-ranges
    before banding - used to clip a CTA bar that may be mid-spinner-flash."""
    if not excludes_px:
        return arr
    arr = arr.copy()
    bg = bg_color(arr)
    for y0, y1 in excludes_px:
        arr[y0:y1, :, :] = bg
    return arr


def row_bands(arr, bg, tol, min_gap_px):
    """Boolean row-content mask -> merged (start,end) inclusive pixel bands,
    gaps smaller than min_gap_px absorbed into the surrounding band."""
    diff = np.abs(arr - bg).sum(axis=-1)
    mask = diff.max(axis=1) > tol
    idx = np.where(mask)[0]
    if len(idx) == 0:
        return []
    bands, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - prev - 1 >= min_gap_px:
            bands.append((start, prev))
            start = i
        prev = i
    bands.append((start, prev))
    return bands


def ink_bounds_x(arr, bg, y0, y1, tol):
    diff = np.abs(arr[y0:y1 + 1] - bg).sum(axis=-1)
    cols = np.where((diff > tol).any(axis=0))[0]
    if len(cols) == 0:
        return None, None
    return int(cols.min()), int(cols.max())


def ink_box(arr, bg, x0, x1, y0, y1, tol):
    region = arr[y0:y1, x0:x1]
    diff = np.abs(region - bg).sum(axis=-1)
    ys, xs = np.where(diff > tol)
    if len(xs) == 0:
        return None
    return {
        "x0": x0 + int(xs.min()), "x1": x0 + int(xs.max()),
        "y0": y0 + int(ys.min()), "y1": y0 + int(ys.max()),
    }


def sample_pixel(arr, x, y, radius=0):
    box = arr[max(0, y - radius):y + radius + 1, max(0, x - radius):x + radius + 1]
    return tuple(box.reshape(-1, 3).mean(axis=0))


def band_report(arr, scale, tol, min_gap_logical, excludes_logical):
    excludes_px = [(int(a * scale), int(b * scale)) for a, b in excludes_logical]
    clipped = apply_excludes(arr, excludes_px)
    bg = bg_color(clipped)
    bands = row_bands(clipped, bg, tol, max(1, int(min_gap_logical * scale)))
    rows, prev_end = [], None
    for (a, b) in bands:
        lo, hi = ink_bounds_x(clipped, bg, a, b, tol)
        rows.append({
            "y0": a / scale, "y1": b / scale, "height": (b - a + 1) / scale,
            "gap_above": None if prev_end is None else (a - prev_end - 1) / scale,
            "ink_left": None if lo is None else lo / scale,
            "ink_right": None if hi is None else hi / scale,
        })
        prev_end = b
    return {"bg": hexc(bg), "logical_width": arr.shape[1] / scale, "bands": rows}


def print_bands(label, report):
    print(f"\n=== {label} (bg {report['bg']}, {report['logical_width']:.1f} logical wide) ===")
    print(f"{'band(logical y)':>22} {'height':>7} {'gap-above':>10}  {'inkL':>6} {'inkR':>6}")
    for b in report["bands"]:
        gap = "-" if b["gap_above"] is None else f"{b['gap_above']:.1f}"
        lo = "-" if b["ink_left"] is None else f"{b['ink_left']:.1f}"
        hi = "-" if b["ink_right"] is None else f"{b['ink_right']:.1f}"
        print(f"{b['y0']:9.1f}-{b['y1']:<9.1f} {b['height']:7.1f} {gap:>10}  {lo:>6} {hi:>6}")


def parse_ranges(vals):
    out = []
    for v in vals or []:
        a, b = v.split(",")
        out.append((float(a), float(b)))
    return out


def cmd_bands(args):
    arr = load(args.img)
    scale = scale_of(arr, args.logical_width)
    report = band_report(arr, scale, args.tol, args.min_gap, parse_ranges(args.exclude))
    print_bands(os.path.basename(args.img), report)
    if args.json:
        print(json.dumps(report, indent=2))


def cmd_compare(args):
    d_arr, b_arr = load(args.design), load(args.built)
    d_scale = scale_of(d_arr, args.design_width)
    b_scale = scale_of(b_arr, args.built_width)
    if args.design_width != args.built_width:
        print(f"WARNING: design logical width {args.design_width} != built logical width "
              f"{args.built_width} - confirm these are really the same frame before trusting deltas.")
    d = band_report(d_arr, d_scale, args.tol, args.min_gap, parse_ranges(args.exclude_design))
    b = band_report(b_arr, b_scale, args.tol, args.min_gap, parse_ranges(args.exclude_built))
    print_bands("DESIGN", d)
    print_bands("BUILT", b)

    print(f"\n=== DELTA (built - design, logical px) ===")
    if len(d["bands"]) != len(b["bands"]):
        print(f"WARNING: band count differs (design {len(d['bands'])} vs built {len(b['bands'])}) "
              "- index-matched rows below may not be the same element.")
    print(f"{'idx':>3} {'design-h':>9} {'built-h':>9} {'delta-h':>9} {'delta-gap':>9}")
    for i, (db, bb) in enumerate(zip(d["bands"], b["bands"])):
        dh = bb["height"] - db["height"]
        dgap = (bb["gap_above"] or 0) - (db["gap_above"] or 0) if i > 0 else 0
        print(f"{i:>3} {db['height']:9.1f} {bb['height']:9.1f} {dh:+9.1f} {dgap:+9.1f}")


def cmd_ink_box(args):
    arr = load(args.img)
    scale = scale_of(arr, args.logical_width)
    x0, y0, x1, y1 = (float(v) for v in args.box.split(","))
    bg = bg_color(arr)
    box_px = ink_box(arr, bg, int(x0 * scale), int(x1 * scale), int(y0 * scale), int(y1 * scale), args.tol)
    if box_px is None:
        print("no ink found in that region")
        return
    w = (box_px["x1"] - box_px["x0"] + 1) / scale
    h = (box_px["y1"] - box_px["y0"] + 1) / scale
    cx, cy = (box_px["x0"] + box_px["x1"]) // 2, (box_px["y0"] + box_px["y1"]) // 2
    corner = sample_pixel(arr, box_px["x0"] + 1, box_px["y0"] + 1)
    fill = sample_pixel(arr, cx, cy)
    print(f"box: x {box_px['x0']/scale:.1f}..{box_px['x1']/scale:.1f}  "
          f"y {box_px['y0']/scale:.1f}..{box_px['y1']/scale:.1f}  {w:.1f}x{h:.1f} logical")
    print(f"fill @center {hexc(fill)}   corner {hexc(corner)} (near bg => rounded corner)")


def cmd_sample(args):
    arr = load(args.img)
    scale = scale_of(arr, args.logical_width)
    points = []
    for spec in args.at:
        x, y = (float(v) for v in spec.split(","))
        rgb = sample_pixel(arr, int(x * scale), int(y * scale), args.radius)
        points.append({"x": x, "y": y, "hex": hexc(rgb)})
    print(json.dumps(points, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bands")
    b.add_argument("--img", required=True)
    b.add_argument("--logical-width", type=float, required=True)
    b.add_argument("--tol", type=int, default=12)
    b.add_argument("--min-gap", type=float, default=1.5, help="logical px")
    b.add_argument("--exclude", action="append", help="y0,y1 logical, repeatable")
    b.add_argument("--json", action="store_true")
    b.set_defaults(func=cmd_bands)

    c = sub.add_parser("compare")
    c.add_argument("--design", required=True)
    c.add_argument("--design-width", type=float, required=True)
    c.add_argument("--built", required=True)
    c.add_argument("--built-width", type=float, required=True)
    c.add_argument("--tol", type=int, default=12)
    c.add_argument("--min-gap", type=float, default=1.5)
    c.add_argument("--exclude-design", action="append")
    c.add_argument("--exclude-built", action="append")
    c.set_defaults(func=cmd_compare)

    i = sub.add_parser("ink-box")
    i.add_argument("--img", required=True)
    i.add_argument("--logical-width", type=float, required=True)
    i.add_argument("--box", required=True, help="x0,y0,x1,y1 logical")
    i.add_argument("--tol", type=int, default=6)
    i.set_defaults(func=cmd_ink_box)

    s = sub.add_parser("sample")
    s.add_argument("--img", required=True)
    s.add_argument("--logical-width", type=float, required=True)
    s.add_argument("--at", action="append", required=True, help="x,y logical, repeatable")
    s.add_argument("--radius", type=int, default=0)
    s.set_defaults(func=cmd_sample)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
