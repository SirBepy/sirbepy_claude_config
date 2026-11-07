"""Cross-project lessons (todo 1154): promote a feedback memory learned in one
project to every project, without growing CLAUDE.md.

An explicit command run by ONE session, never a hook, so concurrent sessions
cannot race on it. Three subcommands:

  scan     Dry run, read-only. Reads every project's feedback memories, clusters
           the same lesson appearing in 2+ distinct projects and prints the
           candidates with their source files. A cluster with any member from a
           client repo's project is never listed (counted only): client facts
           are never promoted.
  promote  Writes one lesson into the tracked global store (lessons/), through
           the refs/memory-rubric.md gate: ADD when the slug is new, UPDATE in
           place when it exists (re-reading the file right before writing).
           Refuses any source that lives in a client project. --supersede then
           stamps `superseded_by:` on each source and drops its MEMORY.md line,
           so the original stops loading once the global copy does.
  index    Rebuilds lessons/INDEX.md, the byte-capped index the SessionStart hook
           (hooks/lessons-index.py) injects into every session. Individual
           lessons load through hooks/memory-trigger.py when they declare
           `triggers:`.

Store: `~/.claude/lessons/` (override with CLAUDE_LESSONS_DIR), allowlisted in
.gitignore. Memory roots: CLAUDE_MEMORY_TRIGGER_ROOTS or the two default
projects dirs, same as the trigger hook.
"""

import argparse
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "hooks"))

import _memory_triggers as mt  # noqa: E402

INDEX_BYTE_CAP = 4096
JACCARD_JOIN = 0.35
MIN_PROJECTS = 2
CLIENT_REPOS_FILE = os.path.join(_REPO, "refs", "client-repos.txt")

STOPWORDS = frozenset(
    "the and for with that this from into when then than not are was were has have had but all any "
    "its it's use used using never always only your you per via one two new old out off get got set "
    "can does did how why what who which will would should could must may might too also more most "
    "claude joe joes code file files memory session sessions task tasks don't doesn't".split()
)


def lessons_dir() -> str:
    return mt.lessons_dir()


def today() -> str:
    return datetime.date.today().isoformat()


# ------------------------------------------------------------------ corpus

def project_key(dirname: str) -> str:
    """Project dir name with any worktree suffix removed, so a repo and its
    linked worktrees count as one project (not as independent confirmation)."""
    return re.sub(r"-+claude-worktrees-.*$", "", dirname)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def client_basenames(path: str = CLIENT_REPOS_FILE) -> list[str]:
    bases = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "/" in line:
                    bases.append(_norm(line.split("/", 1)[1]))
    except OSError:
        pass
    return bases


def is_client_project(key: str, bases: list[str]) -> bool:
    """Conservative: a project dir name that ends in, or contains as a whole
    hyphen-delimited run, a client repo's name counts as client. Over-matching
    only costs a missed promotion; under-matching leaks client content."""
    k = "-" + _norm(key) + "-"
    return any(("-" + b + "-") in k for b in bases if b)


def _frontmatter_type(fm_lines: list[str]) -> str:
    for l in fm_lines:
        m = re.match(r"\s*(?:node_)?type\s*:\s*([A-Za-z_-]+)", l)
        if m and m.group(1).lower() in ("feedback", "user", "project", "reference"):
            return m.group(1).lower()
    return ""


def gather_feedback(roots: list[str]) -> list[dict]:
    """Every non-superseded feedback memory in every project under roots."""
    items = []
    for root in roots:
        try:
            projects = sorted(os.scandir(root), key=lambda e: e.name)
        except OSError:
            continue
        for proj in projects:
            mem = os.path.join(proj.path, "memory")
            if not os.path.isdir(mem):
                continue
            files: list = []
            mt._walk_md(mem, files)
            for path, _ in files:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                parts = mt.split_frontmatter(text)
                if parts is None:
                    continue
                meta = mt.parse_frontmatter(parts[0])
                if meta.get("superseded_by"):
                    continue
                kind = _frontmatter_type(parts[0])
                base = os.path.basename(path)
                if kind != "feedback" and not (not kind and base.startswith("feedback_")):
                    continue
                name = meta.get("name") or os.path.splitext(base)[0]
                items.append({
                    "project": project_key(proj.name),
                    "path": path,
                    "name": name,
                    "description": meta.get("description", ""),
                    "body": parts[1].strip(),
                })
    return items


# -------------------------------------------------------------- clustering

def tokens(item: dict) -> frozenset:
    words = re.findall(r"[a-z][a-z0-9]{2,}", (item["name"] + " " + item["description"]).lower().replace("_", " "))
    return frozenset(w for w in words if w not in STOPWORDS)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(items: list[dict]) -> list[list[dict]]:
    """Union-find on pairs that are the same lesson: an identical normalized
    name, or description-and-name token Jaccard >= JACCARD_JOIN. Only pairs
    from different projects are joined: two memories in ONE project saying
    similar things is a /cleanup-memory dedupe, not cross-project evidence."""
    n = len(items)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    toks = [tokens(it) for it in items]
    names = [_norm(it["name"]) for it in items]
    for i in range(n):
        for j in range(i + 1, n):
            if items[i]["project"] == items[j]["project"]:
                continue
            if names[i] == names[j] or jaccard(toks[i], toks[j]) >= JACCARD_JOIN:
                parent[find(i)] = find(j)
    groups: dict = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(items[i])
    return [g for g in groups.values() if len(g) > 1]


def candidates(items: list[dict], bases: list[str], min_projects: int = MIN_PROJECTS) -> tuple[list[list[dict]], int]:
    """(promotable clusters ranked by project count, number of clusters held
    back because a member belongs to a client project)."""
    out, held = [], 0
    for g in cluster(items):
        if len({m["project"] for m in g}) < min_projects:
            continue
        if any(is_client_project(m["project"], bases) for m in g):
            held += 1
            continue
        out.append(g)
    out.sort(key=lambda g: (-len({m["project"] for m in g}), g[0]["name"]))
    return out, held


def format_scan(cands: list[list[dict]], held: int, total: int) -> str:
    lines = [f"{total} feedback memories read; {len(cands)} cross-project candidate cluster(s); {held} held back (client project involved)."]
    for i, g in enumerate(cands, 1):
        projects = sorted({m["project"] for m in g})
        lines.append(f"\n[{i}] {len(projects)} projects, {len(g)} memories: {g[0]['name']}")
        lines.append(f"    {g[0]['description'][:160]}")
        for m in g:
            lines.append(f"    - {m['project']}: {m['path']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- promote

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,60}$")


def lesson_text(name: str, description: str, body: str, sources: list[str], paths: list[str], skills: list[str]) -> str:
    fm = [f"name: {name}", f"description: {description}", f"promoted: {today()}", f"verified: {today()}"]
    if paths or skills:
        fm.append("triggers:")
        if paths:
            fm.append("  paths: [" + ", ".join(json.dumps(p) for p in paths) + "]")
        if skills:
            fm.append("  skills: [" + ", ".join(skills) + "]")
    fm.append("sources:")
    fm.extend(f"  - {s}" for s in sources)
    fm.extend(["metadata:", "  type: feedback", "  scope: global"])
    return "---\n" + "\n".join(fm) + "\n---\n" + body.strip() + "\n"


def stamp_superseded(path: str, by: str) -> bool:
    """Add `superseded_by: <by>` to a source memory's frontmatter and drop its
    line from the sibling MEMORY.md. Re-reads right before each write."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        nl = "\r\n" if "\r\n" in text[:300] else "\n"
        lines = text.split(nl)
        if not lines or lines[0].strip() != "---":
            return False
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None:
            return False
        if not any(re.match(r"superseded_by\s*:", l) for l in lines[1:end]):
            lines.insert(end, f"superseded_by: {by}")
            mt._atomic_write(path, nl.join(lines))
        index = os.path.join(os.path.dirname(path), "MEMORY.md")
        if os.path.isfile(index):
            with open(index, "r", encoding="utf-8", errors="replace", newline="") as f:
                itext = f.read()
            base = os.path.basename(path)
            kept = [l for l in itext.split("\n") if f"({base})" not in l]
            if len(kept) != len(itext.split("\n")):
                mt._atomic_write(index, "\n".join(kept))
        return True
    except OSError:
        return False


def promote(name: str, description: str, body: str, sources: list[str], paths: list[str], skills: list[str],
            supersede: bool, bases: list[str]) -> tuple[int, str]:
    if not SLUG_RE.match(name):
        return 2, f"refused: name '{name}' must be a lowercase slug (a-z, 0-9, - or _)"
    for s in sources:
        key = project_key(os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(s)))))
        if is_client_project(key, bases):
            return 2, f"refused: source {s} belongs to client project '{key}'; client facts are never promoted"
    ldir = lessons_dir()
    target = os.path.join(ldir, name + ".md")
    verb = "UPDATE" if os.path.isfile(target) else "ADD"
    existing = []
    if verb == "UPDATE":
        # Re-read at write time: the gate's UPDATE keeps the file and merges sources.
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            parts = mt.split_frontmatter(f.read())
        if parts:
            existing = [m for m in re.findall(r"^\s*-\s+(.+)$", "\n".join(parts[0]), re.M) if os.path.isabs(m)]
            prior = mt.parse_frontmatter(parts[0])["triggers"]
            # An UPDATE that names no triggers keeps the ones the lesson already has.
            paths = paths or prior["paths"]
            skills = skills or prior["skills"]
    merged = sorted(set(existing) | {os.path.abspath(s) for s in sources})
    mt._atomic_write(target, lesson_text(name, description, body, merged, paths, skills))
    status = [f"{verb} {target}"]
    if supersede:
        for s in sources:
            status.append(f"superseded {s}: {'ok' if stamp_superseded(s, name) else 'FAILED'}")
    build_index()
    status.append(f"index rebuilt: {os.path.join(ldir, 'INDEX.md')}")
    return 0, "\n".join(status)


# ------------------------------------------------------------------ index

def build_index(cap: int = INDEX_BYTE_CAP) -> str:
    ldir = lessons_dir()
    rows = []
    try:
        names = sorted(n for n in os.listdir(ldir) if n.endswith(".md") and n != "INDEX.md")
    except OSError:
        names = []
    for n in names:
        try:
            with open(os.path.join(ldir, n), "r", encoding="utf-8", errors="replace") as f:
                parts = mt.split_frontmatter(f.read())
        except OSError:
            continue
        meta = mt.parse_frontmatter(parts[0]) if parts else {}
        rows.append(f"- [{meta.get('name') or n[:-3]}]({n}) - {meta.get('description', '')}".rstrip(" -"))
    header = "# Global lessons (learned in one project, true in all)\n\nFull text: ~/.claude/lessons/<file>. Lessons with triggers load on their own.\n\n"
    out, used = header, len(header.encode("utf-8"))
    kept = 0
    for r in rows:
        add = len((r + "\n").encode("utf-8"))
        if used + add > cap - 80:
            out += f"- (+{len(rows) - kept} more in ~/.claude/lessons/, over the {cap}-byte index cap)\n"
            break
        out += r + "\n"
        used += add
        kept += 1
    if rows:
        mt._atomic_write(os.path.join(ldir, "INDEX.md"), out)
    else:
        try:
            os.remove(os.path.join(ldir, "INDEX.md"))
        except OSError:
            pass
    return out if rows else ""


# -------------------------------------------------------------------- cli

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Cross-project lessons sweep (todo 1154)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="dry run: list cross-project candidate clusters")
    s.add_argument("--min-projects", type=int, default=MIN_PROJECTS)
    s.add_argument("--json", action="store_true")
    p = sub.add_parser("promote", help="write one lesson into the global store")
    p.add_argument("--name", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--source", action="append", required=True, help="a source memory file (repeatable)")
    p.add_argument("--body-file", help="lesson body; default is the first source's body")
    p.add_argument("--path", action="append", default=[], help="trigger path glob (repeatable)")
    p.add_argument("--skill", action="append", default=[], help="trigger skill name (repeatable)")
    p.add_argument("--supersede", action="store_true", help="mark each source superseded_by this lesson")
    sub.add_parser("index", help="rebuild lessons/INDEX.md")
    args = ap.parse_args(argv)

    bases = client_basenames()
    if args.cmd == "scan":
        items = gather_feedback(mt.memory_roots())
        cands, held = candidates(items, bases, args.min_projects)
        if args.json:
            print(json.dumps({"total": len(items), "held": held, "clusters": [
                [{k: m[k] for k in ("project", "path", "name", "description")} for m in g] for g in cands]}, indent=1))
        else:
            print(format_scan(cands, held, len(items)))
        return 0
    if args.cmd == "promote":
        if args.body_file:
            with open(args.body_file, "r", encoding="utf-8") as f:
                body = f.read()
        else:
            with open(args.source[0], "r", encoding="utf-8", errors="replace") as f:
                parts = mt.split_frontmatter(f.read())
            body = parts[1] if parts else ""
        code, msg = promote(args.name, args.description, body, args.source, args.path, args.skill, args.supersede, bases)
        print(msg, file=sys.stderr if code else sys.stdout)
        return code
    build_index()
    print(f"index rebuilt: {os.path.join(lessons_dir(), 'INDEX.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
