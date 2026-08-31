"""Fetch Dev Mode annotations for a set of frame ids and write a deduped
markdown digest.

Annotations are a different Figma primitive than comments: they hang off the
node's own `annotations` field, nested under the frame, and
`/v1/files/{key}/comments` never returns them. A `sweep`'s depth=3 cap misses
almost all of them, so this fetches each frame id individually at depth=10 -
measured cheap (see SKILL.md's Quota rules) unlike a whole-page deep read.
Labels arrive as Quill HTML and are flattened to markdown; the same
annotation repeats across sibling frames, so entries are deduped by label
text, not node id.

Usage:
  python figma_annotations.py --file-key <url-or-key> \
      --manifest <tile-dir>/manifest.json --out <tile-dir>/annotations.md \
      --cache-dir <persistent-cache-dir>

  python figma_annotations.py --file-key <url-or-key> --ids <id1,id2,...> \
      --out annotations.md --cache-dir <persistent-cache-dir>
"""
import argparse
import html
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_shared"))
import figma_client as fc

BATCH = 5
GAP_S = 6
DEPTH = 10


def walk(node, trail, found):
    if isinstance(node, dict):
        name = node.get("name")
        here = trail + [name] if isinstance(name, str) else trail
        if node.get("annotations"):
            found.append({"id": node.get("id"), "trail": [t for t in here if t][-4:],
                          "annotations": node["annotations"]})
        for value in node.values():
            walk(value, here, found)
    elif isinstance(node, list):
        for item in node:
            walk(item, trail, found)


def fetch_annotated(file_key, ids, token, cache_dir):
    found = []
    n_batches = -(-len(ids) // BATCH)
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        url = f"{fc.API}/files/{file_key}/nodes?ids={','.join(chunk)}&depth={DEPTH}"
        key = f"annotations:{file_key}:{','.join(chunk)}:{DEPTH}"
        data = fc.api_get(url, token, cache_dir, key)
        before = len(found)
        walk(data, [], found)
        print(f"  batch {i // BATCH + 1}/{n_batches}: {len(chunk)} frames, "
              f"+{len(found) - before} annotated nodes")
        if i + BATCH < len(ids):
            time.sleep(GAP_S)

    seen, unique = set(), []
    for f in found:
        if f["id"] in seen:
            continue
        seen.add(f["id"])
        unique.append(f)
    return unique


def plain(text):
    """Annotation labels arrive as Quill HTML; flatten to readable text."""
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"</p>|<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def render(nodes):
    # The same annotation repeats across sibling frames; dedupe on label text, not node id.
    seen = {}
    for node in nodes:
        for a in node.get("annotations", []):
            label = plain(a.get("label") or a.get("labelMarkdown") or "")
            if not label:
                continue
            seen.setdefault(label, set()).add(" > ".join(node.get("trail", [])[-2:]))

    lines = [
        "# Dev Mode annotations",
        "",
        "Pulled from the Figma node trees, **not** the comments endpoint, which never carries "
        "them. `sweep` caps depth at 3 and misses these; these came from scoped per-frame reads "
        "at depth 10. Duplicates across sibling frames are merged.",
        "",
        f"**{len(seen)} distinct annotations.**",
        "",
    ]
    for i, (label, where) in enumerate(sorted(seen.items(), key=lambda kv: -len(kv[0])), 1):
        lines.append(f"## {i}. {sorted(where)[0]}")
        lines.append("")
        lines.append(label)
        if len(where) > 1:
            lines.append("")
            lines.append(f"*Appears on {len(where)} node paths.*")
        lines.append("")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file-key", required=True, help="Figma file key or URL")
    p.add_argument("--manifest", help="sweep's manifest.json; uses its screen ids")
    p.add_argument("--ids", help="Comma-separated frame node ids, if not using --manifest")
    p.add_argument("--out", required=True)
    p.add_argument("--cache-dir", default=None)
    args = p.parse_args()

    if not args.manifest and not args.ids:
        sys.exit("Pass --manifest <sweep's manifest.json> or --ids <id1,id2,...>")

    if args.manifest:
        ids = [s["id"] for s in json.load(open(args.manifest, encoding="utf-8"))["screens"]]
    else:
        ids = [i for i in args.ids.split(",") if i]

    token = fc.resolve_token()
    file_key = fc.parse_file_key(args.file_key)
    nodes = fetch_annotated(file_key, ids, token, args.cache_dir)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(nodes))
    total = sum(len(n["annotations"]) for n in nodes)
    print(f"{args.out}: {total} annotation entries on {len(nodes)} annotated nodes")


if __name__ == "__main__":
    main()
