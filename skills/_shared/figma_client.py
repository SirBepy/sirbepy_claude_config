"""Shared Figma REST API client: token resolution, 429 backoff, and a
persistent disk cache so a repeat run never re-spends quota on a fetch it
already made. Used by figma-tiles and figma-pixel-diff; see their SKILL.md
files for the workflow-level quota rules this module enforces.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

API = "https://api.figma.com/v1"
MAX_SAFE_DEPTH = 3
MAX_RETRY_AFTER = 300


class FigmaQuotaError(RuntimeError):
    pass


def resolve_token():
    """FIGMA_TOKEN env var first, then ~/.claude/.env (gitignored, existing
    convention). Never hardcode or print the value.
    """
    env = os.environ.get("FIGMA_TOKEN")
    if env:
        return env
    dotenv = os.path.expanduser("~/.claude/.env")
    if os.path.exists(dotenv):
        raw = open(dotenv, encoding="utf-8-sig").read()
        m = re.search(r"^FIGMA_TOKEN=(.+)$", raw, re.M)
        if m:
            return m.group(1).strip()
    raise RuntimeError(
        "FIGMA_TOKEN not set. Export it as an environment variable, or add "
        "FIGMA_TOKEN=<token> to ~/.claude/.env (gitignored). Generate a personal "
        "access token at figma.com > Settings > Personal access tokens."
    )


def parse_file_key(url_or_key):
    m = re.search(r"figma\.com/(?:file|design)/([a-zA-Z0-9]+)", url_or_key)
    return m.group(1) if m else url_or_key


def parse_node_id(url_or_id):
    m = re.search(r"node-id=([0-9]+)-([0-9]+)", url_or_id)
    if m:
        return f"{m.group(1)}:{m.group(2)}"
    if re.fullmatch(r"[0-9]+:[0-9]+", url_or_id):
        return url_or_id
    raise ValueError(f"Not a Figma node id or a URL with node-id=: {url_or_id!r}")


def _cache_path(cache_dir, key):
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    return os.path.join(cache_dir, f"{h}.json")


def api_get(url, token, cache_dir=None, cache_key=None, force=False):
    """GET with exponential/Retry-After backoff on 429. A cache_dir+cache_key
    hit costs zero quota - a real Retry-After on this API has run past 100
    hours, so re-fetching is never an acceptable default.
    """
    if cache_dir and cache_key and not force:
        path = _cache_path(cache_dir, cache_key)
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))

    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    result = None
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req) as r:
                result = json.load(r)
                break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            asked = int(e.headers.get("Retry-After") or 0) or min(60, 5 * 2 ** attempt)
            # This API really does return Retry-After past 100 hours when quota is
            # spent. Honour it up to a ceiling, then give up rather than sleep for days.
            if asked > MAX_RETRY_AFTER:
                raise FigmaQuotaError(
                    f"Figma asked for a {asked}s wait ({asked / 3600:.1f}h), past the "
                    f"{MAX_RETRY_AFTER}s ceiling. Quota is spent, not congested: use the "
                    "offline export/slice fallback or come back later."
                )
            print(f"  429, sleeping {asked}s (attempt {attempt + 1}/8)")
            time.sleep(asked)
    if result is None:
        raise FigmaQuotaError(
            "Rate limited out after 8 retries. Stop retrying and switch to the "
            "offline export/slice fallback instead."
        )

    if cache_dir and cache_key:
        os.makedirs(cache_dir, exist_ok=True)
        with open(_cache_path(cache_dir, cache_key), "w", encoding="utf-8") as f:
            json.dump(result, f)
    return result


def fetch_node_tree(file_key, node_id, token, depth=3, cache_dir=None, force=False):
    """Fetch ONE node's subtree, never a whole-page read. depth beyond
    MAX_SAFE_DEPTH is refused - a deep whole-page read is the exact mistake
    that triggered multi-day 429s (todo 301's incident). force=True overrides.
    """
    if depth > MAX_SAFE_DEPTH and not force:
        raise FigmaQuotaError(
            f"depth={depth} exceeds the safe cap of {MAX_SAFE_DEPTH}. Figma bills "
            "by tree size, not node count. Pass force=True only if you understand "
            "the cost."
        )
    url = f"{API}/files/{file_key}/nodes?ids={node_id}&depth={depth}"
    key = f"tree:{file_key}:{node_id}:{depth}"
    return api_get(url, token, cache_dir, key, force=force)


def fetch_images(file_key, node_ids, token, out_dir, scale=2, fmt="png", force=False):
    """Render node_ids via /v1/images - a quota separate from /v1/files.
    Chunks 10 ids per request and skips ids whose PNG already exists on disk,
    so a re-run after a partial failure costs nothing for what already landed.
    """
    os.makedirs(out_dir, exist_ok=True)
    paths, todo = {}, []
    for nid in node_ids:
        p = os.path.join(out_dir, f"{nid.replace(':', '-')}.{fmt}")
        if os.path.exists(p) and not force:
            paths[nid] = p
        else:
            todo.append(nid)

    for i in range(0, len(todo), 10):
        batch = todo[i:i + 10]
        url = f"{API}/images/{file_key}?ids={','.join(batch)}&format={fmt}&scale={scale}"
        res = api_get(url, token)
        if res.get("err"):
            raise FigmaQuotaError(f"/v1/images error: {res['err']}")
        for nid in batch:
            img_url = res["images"].get(nid)
            if not img_url:
                continue
            dest = os.path.join(out_dir, f"{nid.replace(':', '-')}.{fmt}")
            urllib.request.urlretrieve(img_url, dest)
            paths[nid] = dest
        time.sleep(0.4)
    return paths


def fetch_comments(file_key, token, cache_dir=None, force=False):
    url = f"{API}/files/{file_key}/comments"
    res = api_get(url, token, cache_dir, f"comments:{file_key}", force=force)
    return res["comments"]
