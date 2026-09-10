"""Fetch a single Figma node, sample its rendered pixels, and cross-reference
its JSON tree for exact text/fills/color tokens.

Subcommands:
  fetch          Fetch one node's JSON tree + rendered PNG (cached).
  sample         Sample pixel color(s) at x,y coordinates in a PNG.
  crop           Crop a region out of a PNG.
  inspect        Walk a cached node tree for matching names; print
                 characters/fills.
  nearest-token  Map a sampled/given hex, or a numeric --value, to the
                 nearest token in a name->hex or name->number JSON map.
  measure        Bbox-detect a component in two local screenshots (render
                 vs design) and scale-normalize via a shared anchor. No
                 Figma fetch, no quota - see SKILL.md's local-raster mode.

Always node-scoped (never a whole board) - see ../SKILL.md for why this is
inherently low quota cost, and figma-tiles for the board-sweep workflow.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import figma_client as fc
import pixel_utils as pixu


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_distance(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def sample_pixel(png_path, x, y, radius=0):
    import numpy as np
    from PIL import Image
    arr = np.asarray(Image.open(png_path).convert("RGB")).astype(int)
    return pixu.sample_box(arr, x, y, radius)


def _load_rgb_array(png_path):
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def _corner_background(arr):
    """Average the 4 corner pixels of a region as its background color.
    Assumes the caller's region has a small margin so corners land on
    background, not on the target - true for a rough crop box (SKILL.md
    step 1), not for a box drawn tight to the edges."""
    import numpy as np
    h, w = arr.shape[0], arr.shape[1]
    corners = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    return tuple(int(round(c)) for c in np.mean(corners, axis=0))


def _detect_bbox(arr, bg, tolerance, row_frac, col_frac):
    """Threshold every pixel's distance from bg, then take a row/column
    profile and use a fraction-of-max cutoff (not the first nonzero pixel)
    to find the true edges. A naive first-differing-pixel bbox over-reads by
    1-2px per side from drop-shadow bleed and antialiasing (SKILL.md steps
    2-3): those rows/columns have only a handful of differing pixels, far
    below the object's full-width/height row/column count, so a fraction-of-
    max cutoff excludes them while a bare `> 0` check would not."""
    import numpy as np
    diff = np.sqrt(((arr - np.array(bg)) ** 2).sum(axis=2))
    mask = diff > tolerance
    row_profile = mask.sum(axis=1)
    col_profile = mask.sum(axis=0)
    max_row, max_col = row_profile.max(), col_profile.max()
    if max_row == 0 or max_col == 0:
        raise ValueError(
            "no pixels in this region differ from the detected background beyond --tolerance "
            f"({tolerance}) - widen --tolerance, check --bg, or the --*-box region"
        )
    row_idx = np.where(row_profile >= row_frac * max_row)[0]
    col_idx = np.where(col_profile >= col_frac * max_col)[0]
    top, bottom = int(row_idx.min()), int(row_idx.max())
    left, right = int(col_idx.min()), int(col_idx.max())
    return {"left": left, "top": top, "right": right, "bottom": bottom,
            "width": right - left + 1, "height": bottom - top + 1}


def _measure_region(png_path, box_str, tolerance, row_frac, col_frac, bg_hex):
    """Crop png_path to the rough box_str region, detect the true bbox
    inside it, and report the bbox back in the full image's coordinates."""
    x0, y0, x1, y1 = (int(v) for v in box_str.split(","))
    region = _load_rgb_array(png_path)[y0:y1, x0:x1]
    bg = hex_to_rgb(bg_hex) if bg_hex else _corner_background(region)
    local = _detect_bbox(region, bg, tolerance, row_frac, col_frac)
    return {
        "region": [x0, y0, x1, y1],
        "background": pixu.hex_from_rgb(bg),
        "bbox": [x0 + local["left"], y0 + local["top"], x0 + local["right"] + 1, y0 + local["bottom"] + 1],
        "width": local["width"],
        "height": local["height"],
    }


def cmd_fetch(args):
    token = fc.resolve_token()
    file_key = fc.parse_file_key(args.file_key or args.url)
    node_id = fc.parse_node_id(args.node_id or args.url)
    os.makedirs(args.out, exist_ok=True)

    tree = fc.fetch_node_tree(file_key, node_id, token, depth=args.depth, cache_dir=args.cache_dir)
    tree_path = os.path.join(args.out, f"{node_id.replace(':', '-')}.json")
    with open(tree_path, "w", encoding="utf-8") as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)

    images = fc.fetch_images(file_key, [node_id], token, args.out, scale=args.scale)
    print(f"tree: {tree_path}")
    print(f"png: {images.get(node_id, '(render failed)')}")


def cmd_sample(args):
    points = []
    for spec in args.at:
        x, y = (int(v) for v in spec.split(","))
        rgb = sample_pixel(args.png, x, y, args.radius)
        points.append({"x": x, "y": y, "hex": pixu.hex_from_rgb(rgb), "rgb": list(rgb)})
    print(json.dumps(points, indent=2))


def cmd_crop(args):
    from PIL import Image
    x0, y0, x1, y1 = (int(v) for v in args.box.split(","))
    Image.open(args.png).crop((x0, y0, x1, y1)).save(args.out)
    print(f"saved: {args.out}")


def _walk_inspect(node, name_filter, out):
    if name_filter.lower() in (node.get("name") or "").lower():
        entry = {"id": node.get("id"), "name": node.get("name"), "type": node.get("type")}
        if node.get("type") == "TEXT" and node.get("characters"):
            entry["characters"] = node["characters"]
        fills = []
        for f in node.get("fills") or []:
            if f.get("type") == "SOLID" and f.get("visible", True):
                c = f["color"]
                rgb = tuple(round(c[k] * 255) for k in ("r", "g", "b"))
                fills.append({"hex": pixu.hex_from_rgb(rgb), "opacity": f.get("opacity", 1)})
        if fills:
            entry["fills"] = fills
        out.append(entry)
    for child in node.get("children", []):
        _walk_inspect(child, name_filter, out)


def cmd_inspect(args):
    raw = json.load(open(args.node_json, encoding="utf-8"))
    docs = [n["document"] for n in raw.get("nodes", {}).values()] if "nodes" in raw else [raw]
    matches = []
    for doc in docs:
        _walk_inspect(doc, args.name, matches)
    print(json.dumps(matches, indent=2, ensure_ascii=False))


def cmd_nearest_token(args):
    tokens = json.load(open(args.tokens, encoding="utf-8"))
    if args.value is not None:
        scored = sorted(
            ((name, abs(args.value - v), v) for name, v in tokens.items()),
            key=lambda t: t[1],
        )
        best = scored[0]
        print(json.dumps({
            "target_value": args.value,
            "nearest_token": best[0],
            "nearest_value": best[2],
            "distance": round(best[1], 2),
            "exact_match": best[1] == 0,
            "needs_new_token": best[1] > args.threshold,
        }, indent=2))
        return

    target = hex_to_rgb(args.hex) if args.hex else sample_pixel(args.png, args.x, args.y, args.radius)
    scored = sorted(
        ((name, color_distance(target, hex_to_rgb(v)), v) for name, v in tokens.items()),
        key=lambda t: t[1],
    )
    best = scored[0]
    print(json.dumps({
        "target_hex": pixu.hex_from_rgb(target),
        "nearest_token": best[0],
        "nearest_hex": best[2],
        "distance": round(best[1], 2),
        "exact_match": best[1] == 0,
        "needs_new_token": best[1] > args.threshold,
    }, indent=2))


def cmd_measure(args):
    render_target = _measure_region(args.render, args.render_box, args.tolerance, args.row_frac, args.col_frac, args.bg)
    design_target = _measure_region(args.design, args.design_box, args.tolerance, args.row_frac, args.col_frac, args.bg)
    result = {"target": {"render": render_target, "design": design_target}}

    if args.anchor_render_box:
        anchor_render = _measure_region(args.render, args.anchor_render_box, args.tolerance, args.row_frac, args.col_frac, args.bg)
        anchor_design = _measure_region(args.design, args.anchor_design_box, args.tolerance, args.row_frac, args.col_frac, args.bg)
        result["anchor"] = {"render": anchor_render, "design": anchor_design}

        reference = args.reference
        other = "design" if reference == "render" else "render"
        ref_anchor_h = result["anchor"][reference]["height"]
        other_anchor_h = result["anchor"][other]["height"]
        # SKILL.md step 4: scale_factor = anchor_height_in_reference / anchor_height_in_other,
        # applied to the OTHER image's raw pixels to bring it into the reference image's units.
        scale_factor = ref_anchor_h / other_anchor_h
        other_target = result["target"][other]
        normalized_other = {
            "width": round(other_target["width"] * scale_factor, 2),
            "height": round(other_target["height"] * scale_factor, 2),
        }
        ref_target = result["target"][reference]
        result["reference"] = reference
        result["scale_factor"] = round(scale_factor, 4)
        result["normalized"] = {
            reference: {"width": ref_target["width"], "height": ref_target["height"]},
            other: normalized_other,
        }
        result["delta"] = {
            "width": round(ref_target["width"] - normalized_other["width"], 2),
            "height": round(ref_target["height"] - normalized_other["height"], 2),
        }
    else:
        result["note"] = (
            "no --anchor-*-box given: target widths/heights above are raw pixels from two "
            "possibly-different zoom levels and are NOT comparable to each other (SKILL.md step 4)."
        )

    print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="Fetch one node's tree + rendered PNG")
    f.add_argument("--url", help="Figma share URL with node-id=...")
    f.add_argument("--file-key", help="Overrides the URL-parsed file key")
    f.add_argument("--node-id", help="Overrides the URL-parsed node id (colon form, e.g. 1:2)")
    f.add_argument("--out", required=True)
    f.add_argument("--cache-dir", default=None, help="Persistent cache dir; strongly recommended")
    f.add_argument("--depth", type=int, default=2)
    f.add_argument("--scale", type=int, default=2)
    f.set_defaults(func=cmd_fetch)

    s = sub.add_parser("sample", help="Sample pixel color(s) in a PNG")
    s.add_argument("--png", required=True)
    s.add_argument("--at", action="append", required=True, help='"x,y" point, repeatable')
    s.add_argument("--radius", type=int, default=0, help="Average over a square of this radius")
    s.set_defaults(func=cmd_sample)

    c = sub.add_parser("crop", help="Crop a region out of a PNG")
    c.add_argument("--png", required=True)
    c.add_argument("--box", required=True, help="x0,y0,x1,y1")
    c.add_argument("--out", required=True)
    c.set_defaults(func=cmd_crop)

    i = sub.add_parser("inspect", help="Find nodes by name in a cached tree; print text/fills")
    i.add_argument("--node-json", required=True)
    i.add_argument("--name", required=True, help="Case-insensitive substring match")
    i.set_defaults(func=cmd_inspect)

    n = sub.add_parser("nearest-token", help="Map a color (or a numeric --value) to the nearest project token")
    n.add_argument("--hex", help="Target color, e.g. #1a73e8")
    n.add_argument("--png", help="Sample the target from a PNG instead of --hex")
    n.add_argument("--x", type=int)
    n.add_argument("--y", type=int)
    n.add_argument("--radius", type=int, default=0)
    n.add_argument("--value", type=float, help="Target number (e.g. a measured px size) instead of a color; --tokens must then be {tokenName: number, ...}")
    n.add_argument("--tokens", required=True, help='JSON file: {tokenName: "#hex", ...} for color mode, or {tokenName: number, ...} for --value mode')
    n.add_argument("--threshold", type=float, default=None, help="Distance above which no token matches. Color mode defaults to 30 (Euclidean RGB); --value mode has no universal default (spacing vs font-size scales differ) and requires this explicitly")
    n.set_defaults(func=cmd_nearest_token)

    m = sub.add_parser("measure", help="Bbox-detect a component in two local screenshots and scale-normalize via a shared anchor")
    m.add_argument("--render", required=True, help="Built/rendered screenshot PNG")
    m.add_argument("--design", required=True, help="Design mock screenshot PNG")
    m.add_argument("--render-box", required=True, help="Rough x0,y0,x1,y1 region containing the target component in --render (a small margin around it, for background sampling)")
    m.add_argument("--design-box", required=True, help="Rough x0,y0,x1,y1 region containing the target component in --design")
    m.add_argument("--anchor-render-box", help="Rough region containing a shared anchor (e.g. a label's glyph height) in --render. Omit only if both screenshots are already known to be at the same zoom")
    m.add_argument("--anchor-design-box", help="Same anchor's region in --design")
    m.add_argument("--reference", choices=["render", "design"], default="render", help="Which image's pixels are treated as the comparison unit (default: render, usually the one closer to 1:1 CSS px)")
    m.add_argument("--tolerance", type=float, default=24.0, help="Euclidean RGB distance from the detected background counted as 'part of the component' (default 24)")
    m.add_argument("--row-frac", type=float, default=0.5, help="Row-profile fraction-of-max used as the true top/bottom edge cutoff (default 0.5); lower catches thin features, higher rejects more shadow/antialiasing bleed")
    m.add_argument("--col-frac", type=float, default=0.5, help="Same as --row-frac, for the left/right edges")
    m.add_argument("--bg", help="Background hex override; default samples the 4 corners of each region")
    m.set_defaults(func=cmd_measure)

    args = p.parse_args()
    if args.cmd == "nearest-token":
        modes = [bool(args.hex), bool(args.png and args.x is not None and args.y is not None), args.value is not None]
        if sum(modes) != 1:
            p.error("nearest-token needs exactly one of: --hex, --png with --x/--y, or --value")
        if args.threshold is None:
            if args.value is not None:
                p.error("--value mode needs an explicit --threshold - there is no universal default across different token scales (spacing vs font-size)")
            args.threshold = 30.0
    if args.cmd == "measure" and bool(args.anchor_render_box) != bool(args.anchor_design_box):
        p.error("measure needs both --anchor-render-box and --anchor-design-box, or neither")
    args.func(args)


if __name__ == "__main__":
    main()
