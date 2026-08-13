"""Turn a Figma board into per-screen tiles plus a comment digest.

Subcommands:
  sweep     API path - fetch a section's screens, render each at scale 2,
            attach anchored comments, write manifest.json + comments.md.
  slice     Offline fallback - cut per-screen tiles out of a manually
            exported section PNG (no API calls at all).
  comments  Standalone comment digest, for a re-run that only needs the
            thread markdown refreshed (cache-only if already fetched).

See ../SKILL.md for the quota rules and the Dev Mode MCP alternative.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import figma_client as fc

# Anything roughly phone-shaped; excludes arrows, labels, swatches.
MIN_W, MAX_W, MIN_H = 300, 500, 400


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "untitled"


def walk_screens(node, path, out, min_w, max_w, min_h):
    box = node.get("absoluteBoundingBox") or {}
    w, h = box.get("width", 0), box.get("height", 0)
    is_screen = node["type"] in ("FRAME", "COMPONENT", "INSTANCE") and min_w <= w <= max_w and h >= min_h
    if is_screen:
        out.append({"id": node["id"], "name": node["name"], "path": path, "w": round(w), "h": round(h)})
        return  # don't descend into a screen
    for child in node.get("children", []):
        walk_screens(child, path + [node["name"]], out, min_w, max_w, min_h)


def render_comments_digest(comments):
    by_parent = {}
    for c in comments:
        if c.get("parent_id"):
            by_parent.setdefault(c["parent_id"], []).append(c)
    roots = sorted((c for c in comments if not c.get("parent_id")), key=lambda c: c["created_at"], reverse=True)

    lines = [f"# Figma comments ({len(roots)} threads, {len(comments)} messages)", ""]
    for r in roots:
        node = (r.get("client_meta") or {}).get("node_id", "-")
        state = "RESOLVED" if r.get("resolved_at") else "OPEN"
        lines.append(f"## [{state}] {r['created_at'][:10]} {r['user']['handle']} (node {node})")
        lines.append(r["message"].strip() or "(empty)")
        for rep in sorted(by_parent.get(r["id"], []), key=lambda c: c["created_at"]):
            lines.append(f"  - **{rep['user']['handle']}** {rep['created_at'][:10]}: {rep['message'].strip()}")
        lines.append("")
    return "\n".join(lines)


def anchor_comments(screens, comments):
    by_node = {}
    for c in comments:
        nid = (c.get("client_meta") or {}).get("node_id")
        if nid:
            by_node.setdefault(nid, []).append(c)
    for s in screens:
        roots = {c["id"] for c in by_node.get(s["id"], [])}
        replies = [c for c in comments if c.get("parent_id") in roots]
        s["comments"] = [
            {"author": c["user"]["handle"], "at": c["created_at"][:10],
             "resolved": bool(c.get("resolved_at")), "text": c["message"]}
            for c in sorted(by_node.get(s["id"], []) + replies, key=lambda c: c["created_at"])
        ]


def cmd_sweep(args):
    token = fc.resolve_token()
    file_key = fc.parse_file_key(args.file_key)
    section_ids = [fc.parse_node_id(s) for s in args.section]
    os.makedirs(args.out, exist_ok=True)

    screens = []
    for sid in section_ids:
        doc = fc.fetch_node_tree(file_key, sid, token, depth=args.depth, cache_dir=args.cache_dir)["nodes"][sid]["document"]
        before = len(screens)
        walk_screens(doc, [], screens, args.min_w, args.max_w, args.min_h)
        print(f"{doc['name']!r}: {len(screens) - before} screen frames")

    print(f"total: {len(screens)} screen frames")
    for s in screens:
        s["file"] = f"{slug(' '.join(s['path']) + ' ' + s['name'])}--{s['id'].replace(':', '-')}.png"

    node_ids = [s["id"] for s in screens]
    rendered = fc.fetch_images(file_key, node_ids, token, args.out, scale=args.scale)
    for s in screens:
        if s["id"] not in rendered:
            print(f"  no image for {s['id']} {s['name']}")

    comments = fc.fetch_comments(file_key, token, cache_dir=args.cache_dir)
    anchor_comments(screens, comments)

    manifest = os.path.join(args.out, "manifest.json")
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump({"sections": section_ids, "screens": screens}, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.out, "comments.md"), "w", encoding="utf-8") as f:
        f.write(render_comments_digest(comments))
    print(f"manifest: {manifest}")
    print(f"screens with anchored comments: {sum(1 for s in screens if s['comments'])}")


def cmd_slice(args):
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None

    GAP, CHUNK_H, OVERLAP, UPSCALE_BELOW = 14, 1750, 250, 500

    def bands(mask, axis, gap):
        """Runs along `axis` that carry real content, ignoring thin connector arrows."""
        filled = (mask.sum(axis=axis) / max(1, mask.shape[1 - axis])) > 0.03
        out, start, blank = [], None, 0
        for i, v in enumerate(filled):
            if v:
                start, blank = (i if start is None else start), 0
            elif start is not None:
                blank += 1
                if blank >= gap:
                    out.append((start, i - blank + 1))
                    start, blank = None, 0
        if start is not None:
            out.append((start, len(filled)))
        return [(a, b) for a, b in out if b - a >= args.min_h // 4]

    def split(fg, x0, y0, x1, y1, out, depth):
        sub = fg[y0:y1, x0:x1]
        w, h = x1 - x0, y1 - y0
        if depth >= 8 or w < args.min_w or h < args.min_h:
            return
        rows, cols = bands(sub, 1, GAP), bands(sub, 0, GAP)
        if len(rows) > 1 or len(cols) > 1:
            targets = [(x0 + a, y0, x0 + b, y1) for a, b in cols] if len(cols) > 1 \
                else [(x0, y0 + a, x1, y0 + b) for a, b in rows]
            for t in targets:
                split(fg, *t, out, depth + 1)
            return
        if rows and cols:
            out.append((x0 + cols[0][0], y0 + rows[0][0], x0 + cols[0][1], y0 + rows[0][1]))

    os.makedirs(args.out, exist_ok=True)
    img = Image.open(args.export).convert("RGB")
    img = img.crop((args.margin, args.margin, img.width - args.margin, img.height - args.margin))
    print(f"{img.width}x{img.height} after trimming {args.margin}px")

    bg = np.array(max(img.resize((300, 300)).getcolors(90000), key=lambda c: c[0])[1])
    a = np.asarray(img).astype(np.int16)
    fg = (np.abs(a - bg) > 12).any(axis=2)
    del a

    boxes = []
    split(fg, 0, 0, fg.shape[1], fg.shape[0], boxes, 0)
    boxes.sort(key=lambda b: (b[0], b[1]))
    print(f"{len(boxes)} frames")

    out = []
    for i, (x0, y0, x1, y1) in enumerate(boxes, 1):
        crop = img.crop((x0, y0, x1, y1))
        if crop.width < UPSCALE_BELOW:
            crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
        parts = [crop]
        if crop.height > CHUNK_H * 1.15:
            step = CHUNK_H - OVERLAP
            parts = [crop.crop((0, t, crop.width, min(crop.height, t + CHUNK_H)))
                     for t in range(0, crop.height - OVERLAP, step)]
        for j, part in enumerate(parts):
            suffix = "" if len(parts) == 1 else chr(ord("a") + j)
            fn = f"{args.slug}-{i:02d}{suffix}.png"
            part.save(os.path.join(args.out, fn))
            out.append({"file": fn, "w": part.width, "h": part.height})

    with open(os.path.join(args.out, f"{args.slug}_index.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"{len(out)} tiles")


def cmd_comments(args):
    token = fc.resolve_token()
    file_key = fc.parse_file_key(args.file_key)
    comments = fc.fetch_comments(file_key, token, cache_dir=args.cache_dir)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render_comments_digest(comments))
    print(f"{args.out}: {len(comments)} messages")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("sweep", help="Fetch + render + digest via the Figma API")
    sp.add_argument("--file-key", required=True, help="Figma file key or URL")
    sp.add_argument("--section", nargs="+", required=True, help="Section node id(s) or share URL(s)")
    sp.add_argument("--out", required=True)
    sp.add_argument("--cache-dir", default=None, help="Persistent cache dir; strongly recommended")
    sp.add_argument("--depth", type=int, default=3)
    sp.add_argument("--scale", type=int, default=2)
    sp.add_argument("--min-w", type=int, default=MIN_W)
    sp.add_argument("--max-w", type=int, default=MAX_W)
    sp.add_argument("--min-h", type=int, default=MIN_H)
    sp.set_defaults(func=cmd_sweep)

    sl = sub.add_parser("slice", help="Offline: slice a manually exported section PNG")
    sl.add_argument("--export", required=True)
    sl.add_argument("--slug", required=True)
    sl.add_argument("--out", required=True)
    sl.add_argument("--margin", type=int, default=60)
    sl.add_argument("--min-w", type=int, default=240)
    sl.add_argument("--min-h", type=int, default=300)
    sl.set_defaults(func=cmd_slice)

    cm = sub.add_parser("comments", help="Standalone comment digest")
    cm.add_argument("--file-key", required=True)
    cm.add_argument("--out", required=True)
    cm.add_argument("--cache-dir", default=None)
    cm.set_defaults(func=cmd_comments)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
