"""Fetch a single Figma node, sample its rendered pixels, and cross-reference
its JSON tree for exact text/fills/color tokens.

Subcommands:
  fetch          Fetch one node's JSON tree + rendered PNG (cached).
  sample         Sample pixel color(s) at x,y coordinates in a PNG.
  crop           Crop a region out of a PNG.
  inspect        Walk a cached node tree for matching names; print
                 characters/fills.
  nearest-token  Map a sampled/given hex to the nearest token in a
                 name->hex JSON map.

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
    target = hex_to_rgb(args.hex) if args.hex else sample_pixel(args.png, args.x, args.y, args.radius)
    tokens = json.load(open(args.tokens, encoding="utf-8"))
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
    s.add_argument("--at", nargs="+", required=True, help='One or more "x,y" points')
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

    n = sub.add_parser("nearest-token", help="Map a color to the nearest project token")
    n.add_argument("--hex", help="Target color, e.g. #1a73e8")
    n.add_argument("--png", help="Sample the target from a PNG instead of --hex")
    n.add_argument("--x", type=int)
    n.add_argument("--y", type=int)
    n.add_argument("--radius", type=int, default=0)
    n.add_argument("--tokens", required=True, help="JSON file: {tokenName: \"#hex\", ...}")
    n.add_argument("--threshold", type=float, default=30.0, help="Euclidean RGB distance above which no token matches")
    n.set_defaults(func=cmd_nearest_token)

    args = p.parse_args()
    if args.cmd == "nearest-token" and not args.hex and not (args.png and args.x is not None and args.y is not None):
        p.error("nearest-token needs either --hex or --png with --x/--y")
    args.func(args)


if __name__ == "__main__":
    main()
