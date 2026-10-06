#!/usr/bin/env python3
"""Shortcut bulk-triage pipeline: search -> dossier -> render -> batch -> consensus.

Consolidates the client, dossier shaping, batching and N-judge tally that got
hand-built three times in the 2026-10-05 zng-biller session (todo 1096), as
one versioned script instead of scratch code under C:/tmp.

READ-ONLY, hard rule: `api_call` refuses any HTTP method other than GET, so
this script structurally cannot PUT/POST/DELETE to Shortcut even by mistake.
Mutating a story stays `/ticket`'s job.

Token resolution matches the shared recipe in `refs/shortcut-api.md`:
`~/.claude/.env`, key `SHORTCUT_API_TOKEN`, BOM + CRLF stripped once here.

Subcommands:
    search      query Shortcut, write a trimmed candidate list
    dossier     shape raw story JSON (+ optional ref lookups) into one
                panel-ready JSON file per ticket
    render      turn a dossier JSON into the markdown block a panel reads
    batch       group rendered markdown dossiers into size-capped batch files
    consensus   merge N judge verdict files into a vote tally or a
                per-key median (e.g. estimate_hours)
"""

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

BASE_URL = "https://api.app.shortcut.com"
ENV_PATH = os.path.join(os.path.expanduser("~"), ".claude", ".env")
DEFAULT_SPLIT_TYPES = ("feature", "bug", "chore")


# ---------------------------------------------------------------------------
# Token + low-level HTTP (GET only, enforced)
# ---------------------------------------------------------------------------

def read_token(env_path=ENV_PATH):
    """Read SHORTCUT_API_TOKEN out of the shared .env file.

    `utf-8-sig` strips the BOM ~/.claude/.env carries; CRLF/quotes are
    stripped on top, same two gotchas refs/shortcut-api.md calls out.
    """
    with open(env_path, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip().strip("\r")
            if line.startswith("SHORTCUT_API_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError(f"SHORTCUT_API_TOKEN not found in {env_path}")


def api_call(method, path, token, body=None, timeout=30):
    """Single HTTP entry point. GET only - this is the read-only guarantee.

    Every caller in this file passes "GET" literally; this check exists so a
    future edit cannot accidentally wire a write verb through the same path.
    """
    if method != "GET":
        raise ValueError(f"shortcut_triage.py is read-only: refused method {method!r}")
    url = path if path.startswith("http") else BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Shortcut-Token": token, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _search_one(query, token, page_size, detail):
    params = {"query": query, "page_size": page_size}
    if detail:
        params["detail"] = detail
    path = "/api/v3/search/stories?" + urllib.parse.urlencode(params)
    out = []
    while path:
        r = api_call("GET", path, token)
        out.extend(r.get("data", []))
        path = r.get("next") or None
    return out


def search_stories(query, token, split_types=None, page_size=250, detail=None):
    """Search Shortcut, merging by id.

    The search API caps at 1000 results for a single query - a broad query
    (e.g. "!is:done !is:archived") silently truncates past that. Passing
    `split_types` runs one `query + " type:<t>"` search per type and merges
    the results, which is how the 2026-10-05 prototype worked around the cap.
    """
    if not split_types:
        return _search_one(query, token, page_size, detail)
    by_id = {}
    for t in split_types:
        for s in _search_one(f"{query} type:{t}", token, page_size, detail):
            by_id[s["id"]] = s
    return list(by_id.values())


def shape_candidate(story):
    """Trim a raw story object down to what a candidate list needs."""
    return {
        "id": story["id"],
        "name": story.get("name"),
        "story_type": story.get("story_type"),
        "workflow_state_id": story.get("workflow_state_id"),
        "updated_at": story.get("updated_at"),
        "archived": story.get("archived", False),
    }


def cmd_search(args):
    token = read_token()
    split_types = args.split_types.split(",") if args.split_types else None
    stories = search_stories(args.query, token, split_types=split_types, page_size=args.page_size)
    candidates = [shape_candidate(s) for s in stories]
    _write_json(candidates, args.out)
    print(f"{len(candidates)} candidate(s)")
    return 0


# ---------------------------------------------------------------------------
# dossier
# ---------------------------------------------------------------------------

DESCRIPTION_CHAR_CAP = 8000


def load_refs(refs_dir):
    """Load the optional member/epic/workflow/custom-field lookups.

    Any missing file degrades gracefully (dossier falls back to raw ids)
    rather than erroring - a panel run with no ref dump is still useful.
    """
    refs = {"members": {}, "epics": {}, "states": {}, "cf_values": {}, "cf_names": {}}
    if not refs_dir:
        return refs

    def _load(name):
        path = os.path.join(refs_dir, name)
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    members = _load("members.json")
    if members:
        refs["members"] = {m["id"]: m["profile"]["mention_name"] for m in members}
    epics = _load("epics.json")
    if epics:
        refs["epics"] = {e["id"]: e["name"] for e in epics}
    workflows = _load("workflows.json")
    if workflows:
        refs["states"] = {
            s["id"]: (wf["name"], s["name"]) for wf in workflows for s in wf["states"]
        }
    custom_fields = _load("custom-fields.json")
    if custom_fields:
        refs["cf_values"] = {
            v["id"]: v["value"] for c in custom_fields for v in c.get("values", [])
        }
        refs["cf_names"] = {c["id"]: c["name"] for c in custom_fields}
    return refs


def _who(refs, member_id):
    return refs["members"].get(member_id, member_id or "-")


def build_dossier(story, refs=None, reasons=None):
    """Shape one raw Shortcut story into the fields a triage panel needs.

    Returns a plain dict (JSON-serializable), not markdown - `render`
    converts it to the prose block a panel prompt actually reads.
    """
    refs = refs or load_refs(None)
    wf_name, state_name = refs["states"].get(story["workflow_state_id"], (None, None))
    custom_fields = [
        {
            "field": refs["cf_names"].get(f["field_id"], f["field_id"]),
            "value": refs["cf_values"].get(f.get("value_id"), f.get("value")),
        }
        for f in story.get("custom_fields", [])
    ]
    links = [
        {
            "verb": l["verb"],
            "other_id": l["object_id"] if l["subject_id"] == story["id"] else l["subject_id"],
            "direction": "out" if l["subject_id"] == story["id"] else "in",
        }
        for l in story.get("story_links", [])
    ]
    pr_refs = (
        [p.get("url") for p in story.get("pull_requests", [])]
        + [b.get("name") for b in story.get("branches", [])]
        + [c.get("message", "")[:80] for c in story.get("commits", [])]
    )
    tasks = [
        {"complete": t["complete"], "description": t["description"]}
        for t in story.get("tasks", [])
    ]
    description = (story.get("description") or "").strip()
    truncated = len(description) > DESCRIPTION_CHAR_CAP
    if truncated:
        description = description[:DESCRIPTION_CHAR_CAP]
    comments = [
        {
            "author": _who(refs, c.get("author_id")),
            "date": (c.get("created_at") or "")[:10],
            "text": (c.get("text") or "").strip(),
        }
        for c in story.get("comments", [])
        if not c.get("deleted")
    ]
    dossier = {
        "id": story["id"],
        "name": story.get("name"),
        "story_type": story.get("story_type"),
        "workflow": wf_name,
        "state": state_name,
        "archived": story.get("archived", False),
        "owners": [_who(refs, o) for o in story.get("owner_ids", [])],
        "requester": _who(refs, story.get("requested_by_id")),
        "epic": refs["epics"].get(story.get("epic_id")),
        "labels": [l["name"] for l in story.get("labels", [])],
        "custom_fields": custom_fields,
        "created_at": (story.get("created_at") or "")[:10],
        "updated_at": (story.get("updated_at") or "")[:10],
        "started_at": (story.get("started_at") or "")[:10] or None,
        "deadline": (story.get("deadline") or "")[:10] or None,
        "story_links": links,
        "pr_refs": [x for x in pr_refs if x],
        "tasks": tasks,
        "description": description,
        "description_truncated": truncated,
        "comments": comments,
    }
    if reasons:
        dossier["match_reasons"] = list(reasons)
    return dossier


def cmd_dossier(args):
    refs = load_refs(args.refs)
    os.makedirs(args.out, exist_ok=True)
    ids = args.ids or [
        os.path.splitext(f)[0] for f in os.listdir(args.story_dir) if f.endswith(".json")
    ]
    written = 0
    for sid in ids:
        story_path = os.path.join(args.story_dir, f"{sid}.json")
        if not os.path.isfile(story_path):
            print(f"skip {sid}: no {story_path}")
            continue
        with open(story_path, "r", encoding="utf-8") as f:
            story = json.load(f)
        dossier = build_dossier(story, refs)
        with open(os.path.join(args.out, f"{sid}.json"), "w", encoding="utf-8") as f:
            json.dump(dossier, f, indent=2)
        written += 1
    print(f"{written} dossier(s) written to {args.out}")
    return 0


# ---------------------------------------------------------------------------
# render (dossier JSON -> markdown block)
# ---------------------------------------------------------------------------

def render_markdown(dossier):
    """Render a shaped dossier dict into the markdown block a panel prompt reads."""
    lines = [
        f"## sc-{dossier['id']}: {dossier['name']}",
        f"- type: {dossier['story_type']} | workflow: {dossier['workflow']} | "
        f"state: {dossier['state']} | archived: {dossier['archived']}",
        f"- owners: {', '.join(dossier['owners']) or '-'} | requester: {dossier['requester']}",
        f"- epic: {dossier['epic'] or '-'} | labels: {', '.join(dossier['labels']) or '-'}",
        f"- custom fields: "
        + ("; ".join(f"{cf['field']}={cf['value']}" for cf in dossier["custom_fields"]) or "-"),
        f"- created: {dossier['created_at']} | updated: {dossier['updated_at']} | "
        f"started: {dossier['started_at'] or '-'}",
    ]
    if dossier.get("match_reasons"):
        lines.append(f"- matched filter by: {', '.join(dossier['match_reasons'])}")
    if dossier["story_links"]:
        link_str = "; ".join(
            f"{l['verb']} sc-{l['other_id']} ({l['direction']})" for l in dossier["story_links"]
        )
        lines.append(f"- story links: {link_str}")
    if dossier["pr_refs"]:
        lines.append(f"- PRs/branches/commits: {'; '.join(dossier['pr_refs'])}")
    if dossier["tasks"]:
        task_str = " | ".join(
            f"[{'x' if t['complete'] else ' '}] {t['description']}" for t in dossier["tasks"]
        )
        lines.append(f"- tasks: {task_str}")
    desc = dossier["description"] or "(empty)"
    if dossier.get("description_truncated"):
        desc += f"\n[... description truncated at {DESCRIPTION_CHAR_CAP} chars]"
    lines.append("\n### Description\n" + desc)
    lines.append(f"\n### Comments ({len(dossier['comments'])})")
    for c in dossier["comments"]:
        lines.append(f"- **{c['author']}** {c['date']}: {c['text']}")
    return "\n".join(lines)


def cmd_render(args):
    os.makedirs(args.out, exist_ok=True)
    files = args.files or [
        os.path.join(args.in_dir, f) for f in os.listdir(args.in_dir) if f.endswith(".json")
    ]
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            dossier = json.load(f)
        md = render_markdown(dossier)
        out_path = os.path.join(args.out, f"{dossier['id']}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)
    print(f"{len(files)} rendered to {args.out}")
    return 0


# ---------------------------------------------------------------------------
# batch (pack rendered markdown into size-capped batch files)
# ---------------------------------------------------------------------------

def batch_items(items, target_chars):
    """Greedily pack strings into batches under `target_chars` each.

    A single item bigger than target_chars still gets its own batch rather
    than being dropped or erroring - the cap is a packing target, not a hard
    limit on any one dossier.
    """
    batches, cur, size = [], [], 0
    for item in items:
        if cur and size + len(item) > target_chars:
            batches.append(cur)
            cur, size = [], 0
        cur.append(item)
        size += len(item)
    if cur:
        batches.append(cur)
    return batches


def cmd_batch(args):
    files = sorted(
        os.path.join(args.in_dir, f) for f in os.listdir(args.in_dir) if f.endswith(".md")
    )
    texts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            texts.append(f.read())
    batches = batch_items(texts, args.target_chars)
    os.makedirs(args.out, exist_ok=True)
    for n, batch in enumerate(batches, 1):
        out_path = os.path.join(args.out, f"{args.prefix}-{n:02d}.md")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(batch))
        print(out_path, len(batch), "dossiers", sum(map(len, batch)), "chars")
    return 0


# ---------------------------------------------------------------------------
# consensus (merge N judge verdict files)
# ---------------------------------------------------------------------------

def tally_vote(all_decisions):
    """Merge N judges' categorical verdicts per ticket id.

    `all_decisions` is a list (one per judge) of lists of
    {"id": ..., "verdict": ...} dicts. An id voted on by every judge with the
    same verdict lands in `agreed`; full coverage with differing verdicts
    lands in `disputed`; partial coverage lands in `incomplete` only, never
    silently counted as agreed.
    """
    judge_count = len(all_decisions)
    votes = defaultdict(list)
    for decisions in all_decisions:
        # One vote per judge per id (a judge restating an id keeps its last
        # verdict), so coverage counts judges, not raw entries.
        per_judge = {d["id"]: d["verdict"] for d in decisions}
        for id_, verdict in per_judge.items():
            votes[id_].append(verdict)

    agreed = defaultdict(list)
    disputed = {}
    incomplete = {}
    for id_, verdicts in votes.items():
        if len(verdicts) < judge_count:
            incomplete[id_] = verdicts
        elif len(set(verdicts)) == 1:
            agreed[verdicts[0]].append(id_)
        else:
            disputed[id_] = verdicts
    return {
        "judge_count": judge_count,
        "agreed": dict(agreed),
        "disputed": disputed,
        "incomplete": incomplete,
    }


def tally_median(all_decisions, field, key_field="key"):
    """Merge N judges' numeric estimates per group key, taking the median.

    `all_decisions` is a list (one per judge) of lists of dicts each carrying
    `key_field` (what is being estimated) and a numeric `field`.
    """
    by_key = defaultdict(list)
    for decisions in all_decisions:
        # One estimate per judge per key, same rule as tally_vote.
        per_judge = {d[key_field]: d for d in decisions}
        for key, d in per_judge.items():
            by_key[key].append(d)
    summary = {}
    for key, ds in by_key.items():
        values = sorted(d[field] for d in ds)
        summary[key] = {
            "values": values,
            "median": statistics.median(values),
            "judge_count": len(ds),
        }
    return summary


def cmd_consensus(args):
    all_decisions = []
    for path in args.verdicts:
        with open(path, "r", encoding="utf-8") as f:
            all_decisions.append(json.load(f))
    if args.mode == "vote":
        result = tally_vote(all_decisions)
    else:
        result = tally_median(all_decisions, args.field, args.key_field)
    _write_json(result, args.out)
    return 0


# ---------------------------------------------------------------------------
# plumbing
# ---------------------------------------------------------------------------

def _write_json(obj, out_path):
    text = json.dumps(obj, indent=2)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="shortcut_triage.py",
        description="Read-only Shortcut bulk-triage pipeline (search/dossier/render/batch/consensus).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="query Shortcut, write a candidate list")
    p_search.add_argument("query")
    p_search.add_argument("--split-types", default=",".join(DEFAULT_SPLIT_TYPES))
    p_search.add_argument("--page-size", type=int, default=250)
    p_search.add_argument("--out", default=None)
    p_search.set_defaults(func=cmd_search)

    p_dossier = sub.add_parser("dossier", help="shape raw story JSON into panel-ready dossiers")
    p_dossier.add_argument("ids", nargs="*", help="story ids; default is every *.json in --story-dir")
    p_dossier.add_argument("--story-dir", required=True)
    p_dossier.add_argument("--refs", default=None, help="dir with members/epics/workflows/custom-fields.json")
    p_dossier.add_argument("--out", required=True)
    p_dossier.set_defaults(func=cmd_dossier)

    p_render = sub.add_parser("render", help="render dossier JSON into markdown blocks")
    p_render.add_argument("files", nargs="*", help="dossier JSON files; default is every *.json in --in-dir")
    p_render.add_argument("--in-dir", dest="in_dir", default=None)
    p_render.add_argument("--out", required=True)
    p_render.set_defaults(func=cmd_render)

    p_batch = sub.add_parser("batch", help="pack rendered markdown into size-capped batches")
    p_batch.add_argument("--in-dir", dest="in_dir", required=True)
    p_batch.add_argument("--out", required=True)
    p_batch.add_argument("--prefix", default="batch")
    p_batch.add_argument("--target-chars", type=int, default=120000)
    p_batch.set_defaults(func=cmd_batch)

    p_consensus = sub.add_parser("consensus", help="merge N judge verdict files into a tally")
    p_consensus.add_argument("--verdicts", nargs="+", required=True)
    p_consensus.add_argument("--mode", choices=("vote", "median"), default="vote")
    p_consensus.add_argument("--field", default="estimate")
    p_consensus.add_argument("--key-field", dest="key_field", default="key")
    p_consensus.add_argument("--out", default=None)
    p_consensus.set_defaults(func=cmd_consensus)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (RuntimeError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
