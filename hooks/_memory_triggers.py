"""Trigger-keyed memory (todo 1153): a memory file declares when it matters,
and the PreToolUse hook injects it the moment that thing is touched.

Frontmatter a memory file may carry (top level, block form):

    triggers:
      paths: ["**/clockify-reconciliator/**", "src/auth/*.ts"]
      skills: [clockify-reconciliator]
      repos: [claude_usage_in_taskbar]
    once: true            # prospective memory: retire after it fires
    fired: 2026-11-07     # written by the hook when a once-memory fires
    superseded_by: other  # a superseded memory never triggers

A path glob without a leading "/" or drive letter or "**" matches any path
whose tail it matches ("auth/*.ts" matches "C:/x/src/auth/a.ts"); "**"
crosses directories, "*" and "?" do not. Matching is case-insensitive and
slash-agnostic. A skill trigger matches the Skill tool's `skill` argument.
A repo trigger matches the name of the git repo root above the tool call's
cwd, on any covered tool.

Cost model: the hook must stay cheap on every Edit/Write/Read/Skill/Agent
call in every session, and the corpus is ~1,800 memory files. It never reads
memory bodies per call. It reads one precompiled table, validated against a
(file count, sum of mtimes, max mtime) fingerprint taken from a directory
walk alone (no file opens; DirEntry.stat() is free on Windows). The walk
itself (~23 ms) runs at most once per recheck window (20 s), using the table
file's own mtime as the "validated at" stamp. A changed fingerprint reparses
only the files whose mtime moved (seen.json) and rewrites the table.

State lives in hooks/.memory-triggers/ (gitignored): table.json, plus one
fired-set file per session so a memory is injected once per session.
"""

import json
import os
import re
import sys
import time

ROOTS_ENV = "CLAUDE_MEMORY_TRIGGER_ROOTS"
STATE_ENV = "CLAUDE_MEMORY_TRIGGER_STATE"
RECHECK_ENV = "CLAUDE_MEMORY_TRIGGER_RECHECK_S"
DEFAULT_RECHECK_S = 20.0

COVERED_TOOLS = ("Edit", "Write", "Read", "Skill", "Agent", "MultiEdit", "NotebookEdit")
FRONTMATTER_READ_BYTES = 6000
BODY_CHAR_CAP = 1800
TOTAL_CHAR_CAP = 5000
FIRED_FILE_MAX_AGE_S = 14 * 86400

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------- paths

def state_dir() -> str:
    return os.environ.get(STATE_ENV) or os.path.join(_HOOKS_DIR, ".memory-triggers")


def table_path() -> str:
    return os.path.join(state_dir(), "table.json")


def seen_path() -> str:
    return os.path.join(state_dir(), "seen.json")


def fired_path(session_id: str) -> str | None:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")
    return os.path.join(state_dir(), "fired", safe + ".json") if safe else None


def memory_roots() -> list[str]:
    """Directories whose children are project dirs holding a `memory/` folder."""
    raw = os.environ.get(ROOTS_ENV)
    if raw:
        candidates = [p for p in raw.split(os.pathsep) if p]
    else:
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, ".claude-personal", "projects"),
            os.path.join(home, ".claude", "projects"),
        ]
    seen, roots = set(), []
    for c in candidates:
        if not os.path.isdir(c):
            continue
        real = os.path.normcase(os.path.realpath(c))
        if real not in seen:
            seen.add(real)
            roots.append(c)
    return roots


# ------------------------------------------------------------- corpus walk

def _walk_md(directory: str, out: list) -> None:
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False):
                if e.name.lower() != "archive":
                    _walk_md(e.path, out)
            elif e.name.endswith(".md") and e.name != "MEMORY.md":
                out.append((e.path, e.stat().st_mtime_ns))
        except OSError:
            continue


def scan_memory_files(roots: list[str]) -> list[tuple[str, int]]:
    files: list[tuple[str, int]] = []
    for root in roots:
        try:
            projects = list(os.scandir(root))
        except OSError:
            continue
        for proj in projects:
            mem = os.path.join(proj.path, "memory")
            if os.path.isdir(mem):
                _walk_md(mem, files)
    return files


def fingerprint(files: list[tuple[str, int]]) -> dict:
    return {
        "count": len(files),
        "sum": sum(m for _, m in files) % (1 << 61),
        "max": max((m for _, m in files), default=0),
    }


# ------------------------------------------------------------ frontmatter

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _inline_list(value: str) -> list[str]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [_strip_quotes(p) for p in inner.split(",") if _strip_quotes(p)]
    return [_strip_quotes(value)] if value else []


def split_frontmatter(text: str) -> tuple[list[str], str] | None:
    """(frontmatter lines, body) or None when the file has no frontmatter."""
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r").strip() == "---":
            return [l.rstrip("\r") for l in lines[1:i]], "\n".join(lines[i + 1:])
    return None


def parse_frontmatter(fm_lines: list[str]) -> dict:
    meta: dict = {"triggers": {"paths": [], "skills": [], "repos": []}}
    top = None
    sub = None
    for raw in fm_lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            sub = None
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            top = key
            if key in ("name", "description", "fired", "superseded_by"):
                meta[key] = _strip_quotes(value)
            elif key == "once":
                meta["once"] = value.lower() in ("true", "yes", "1")
            elif key == "triggers" and value.startswith("{"):
                try:
                    obj = json.loads(value)
                    for k in ("paths", "skills", "repos"):
                        v = obj.get(k) or []
                        meta["triggers"][k] = [str(x) for x in v] if isinstance(v, list) else [str(v)]
                except ValueError:
                    pass
        elif top == "triggers":
            if line.startswith("- "):
                if sub in meta["triggers"]:
                    meta["triggers"][sub].append(_strip_quotes(line[2:]))
                continue
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key in meta["triggers"]:
                sub = key
                if value:
                    meta["triggers"][key].extend(_inline_list(value))
            else:
                sub = None
    return meta


def read_frontmatter(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = f.read(FRONTMATTER_READ_BYTES)
    except OSError:
        return None
    parts = split_frontmatter(head)
    if parts is None:
        return None
    return parse_frontmatter(parts[0])


# ------------------------------------------------------------------- glob

def _norm_path(p: str) -> str:
    return p.replace("\\", "/").lower()


def glob_to_regex(glob: str) -> str:
    g = _norm_path(glob)
    anchored = g.startswith("/") or g.startswith("**") or re.match(r"^[a-z]:/", g) is not None
    out = []
    i = 0
    while i < len(g):
        if g.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif g.startswith("**", i):
            out.append(".*")
            i += 2
        elif g[i] == "*":
            out.append("[^/]*")
            i += 1
        elif g[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(g[i]))
            i += 1
    return ("^" if anchored else "(?:^|.*/)") + "".join(out) + "$"


# ------------------------------------------------------------------- table

def _entry_id(path: str) -> str:
    return os.path.normcase(os.path.abspath(path))


def build_table(files: list[tuple[str, int]], prev_entries: dict | None = None, prev_seen: dict | None = None) -> tuple[dict, dict]:
    """(table, seen). `seen` maps every walked file to its mtime so the next
    rebuild reparses only files whose mtime moved: a memory write by any
    session invalidates the fingerprint, and reparsing all ~1,800 files each
    time costs ~0.5 s on the next tool call."""
    prev_entries = prev_entries or {}
    prev_seen = prev_seen or {}
    entries, seen = [], {}
    for path, mtime in files:
        eid = _entry_id(path)
        seen[eid] = mtime
        if prev_seen.get(eid) == mtime:
            if eid in prev_entries:
                entries.append(prev_entries[eid])
            continue
        meta = read_frontmatter(path)
        if not meta or meta.get("superseded_by"):
            continue
        t = meta["triggers"]
        if not (t["paths"] or t["skills"] or t["repos"]):
            continue
        if meta.get("once") and meta.get("fired"):
            continue
        entries.append({
            "id": eid,
            "path": path,
            "name": meta.get("name") or os.path.splitext(os.path.basename(path))[0],
            "once": bool(meta.get("once")),
            "paths": [glob_to_regex(g) for g in t["paths"]],
            "skills": [x.strip().lower() for x in t["skills"]],
            "repos": [r.strip().lower() for r in t["repos"]],
        })
    return {"version": 1, "fingerprint": fingerprint(files), "entries": entries}, seen


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def recheck_after_s() -> float:
    try:
        return float(os.environ.get(RECHECK_ENV, DEFAULT_RECHECK_S))
    except ValueError:
        return DEFAULT_RECHECK_S


def load_table(roots: list[str] | None = None, force: bool = False) -> dict:
    """The current trigger table. The corpus walk that validates it is
    skipped when the table was validated within recheck_after_s() (a busy
    session makes a covered call every few seconds; a memory edit is picked
    up on the first call after the window). Otherwise the walk's fingerprint
    is compared to the stored one and a mismatch triggers an incremental
    rebuild."""
    tp = table_path()
    window = recheck_after_s()
    if not force and window > 0:
        try:
            if time.time() - os.stat(tp).st_mtime < window:
                table = _read_json(tp)
                if table and table.get("version") == 1:
                    return table
        except OSError:
            pass
    roots = memory_roots() if roots is None else roots
    files = scan_memory_files(roots)
    fp = fingerprint(files)
    old = None if force else _read_json(tp)
    if old and old.get("version") == 1 and old.get("fingerprint") == fp:
        try:
            os.utime(tp)
        except OSError:
            pass
        return old
    prev_entries = {e["id"]: e for e in old.get("entries", [])} if old else {}
    prev_seen = _read_json(seen_path()) if old else None
    table, seen = build_table(files, prev_entries, prev_seen if isinstance(prev_seen, dict) else None)
    try:
        _atomic_write(seen_path(), json.dumps(seen))
        _atomic_write(tp, json.dumps(table))
        _prune_fired()
    except OSError:
        pass
    return table


def _prune_fired() -> None:
    d = os.path.join(state_dir(), "fired")
    cutoff = time.time() - FIRED_FILE_MAX_AGE_S
    try:
        for e in os.scandir(d):
            if e.stat().st_mtime < cutoff:
                os.remove(e.path)
    except OSError:
        pass


# ---------------------------------------------------------------- matching

def repo_name(cwd: str) -> str:
    """Basename of the nearest ancestor of cwd holding a .git entry, else ''."""
    p = os.path.abspath(cwd) if cwd else ""
    while p:
        if os.path.exists(os.path.join(p, ".git")):
            return os.path.basename(p).lower()
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    return ""


_PATH_TOKEN_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'`)>]+|(?:\./|/)?[\w.-]+(?:/[\w.-]+)+")


def tool_signals(tool_name: str, tool_input: dict) -> dict:
    """What a tool call exposes to match against: paths, a skill name, and
    free text (Agent only: its prompt can mention skills and paths)."""
    paths, skill, text = [], "", ""
    if tool_name == "Skill":
        skill = str(tool_input.get("skill") or "").strip().lower()
    elif tool_name == "Agent":
        text = " ".join(str(tool_input.get(k) or "") for k in ("prompt", "description"))
        paths = [_norm_path(m) for m in _PATH_TOKEN_RE.findall(text)]
    else:
        for k in ("file_path", "path", "notebook_path"):
            v = tool_input.get(k)
            if isinstance(v, str) and v:
                paths.append(_norm_path(v))
    return {"paths": paths, "skill": skill, "text": text.lower()}


def match_entries(table: dict, tool_name: str, tool_input: dict, cwd: str) -> list[dict]:
    sig = tool_signals(tool_name, tool_input)
    skill_names = {sig["skill"], sig["skill"].rsplit(":", 1)[-1]} if sig["skill"] else set()
    repo = repo_name(cwd)
    hits = []
    for entry in table.get("entries", []):
        matched = False
        if repo and repo in entry["repos"]:
            matched = True
        if not matched and skill_names and any(s in skill_names for s in entry["skills"]):
            matched = True
        if not matched and sig["text"] and any(
            re.search(r"(?<![\w-])" + re.escape(s) + r"(?![\w-])", sig["text"]) for s in entry["skills"]
        ):
            matched = True
        if not matched and sig["paths"] and any(
            re.match(rx, p) for rx in entry["paths"] for p in sig["paths"]
        ):
            matched = True
        if matched:
            hits.append(entry)
    return hits


# ------------------------------------------------------------ fired state

def load_fired(session_id: str) -> set[str]:
    p = fired_path(session_id)
    if not p:
        return set()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return {s for s in json.load(f) if isinstance(s, str)}
    except (OSError, ValueError, TypeError):
        return set()


def save_fired(session_id: str, ids: set[str]) -> None:
    p = fired_path(session_id)
    if p:
        try:
            _atomic_write(p, json.dumps(sorted(ids)))
        except OSError:
            pass


def retire_once(path: str, today: str) -> None:
    """Stamp `fired: <date>` into a once-memory's frontmatter. Re-reads the
    file right before writing (peers edit memory concurrently) and leaves it
    alone when it is already stamped."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            text = f.read()
        if not text.startswith("---"):
            return
        nl = "\r\n" if "\r\n" in text[:200] else "\n"
        lines = text.split(nl)
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is None or any(re.match(r"fired\s*:", l) for l in lines[1:end]):
            return
        lines.insert(end, f"fired: {today}")
        _atomic_write(path, nl.join(lines))
    except OSError:
        pass


# ----------------------------------------------------------------- render

def memory_body(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return ""
    parts = split_frontmatter(text)
    body = (parts[1] if parts else text).strip()
    return body if len(body) <= BODY_CHAR_CAP else body[:BODY_CHAR_CAP].rstrip() + " [...truncated, read the file for the rest]"


def render(entries: list[dict], tool_name: str) -> str:
    blocks, total = [], 0
    for e in entries:
        body = memory_body(e["path"])
        if not body:
            continue
        block = f"--- {e['name']} ({e['path']}) ---\n{body}"
        if total + len(block) > TOTAL_CHAR_CAP:
            break
        blocks.append(block)
        total += len(block)
    if not blocks:
        return ""
    head = f"[memory-trigger] {len(blocks)} memory file(s) matched this {tool_name} call; loaded now because their triggers fired:"
    if tool_name == "Agent":
        head += (
            "\nThis subagent dispatch was held once so you can pass the text below into the dispatch "
            "prompt (a subagent starts with none of this). Re-dispatch with it included."
        )
    return head + "\n" + "\n\n".join(blocks)


# ------------------------------------------------------------------- hook

def run_hook(payload: dict, roots: list[str] | None = None, today: str | None = None) -> tuple[int, str, str]:
    """(exit code, stdout, stderr) for one PreToolUse payload."""
    tool_name = payload.get("tool_name") or ""
    if tool_name not in COVERED_TOOLS:
        return 0, "", ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0, "", ""
    table = load_table(roots)
    if not table.get("entries"):
        return 0, "", ""
    session_id = payload.get("session_id") or ""
    hits = match_entries(table, tool_name, tool_input, payload.get("cwd") or "")
    if not hits:
        return 0, "", ""
    fired = load_fired(session_id)
    fresh = [e for e in hits if e["id"] not in fired]
    if not fresh:
        return 0, "", ""
    text = render(fresh, tool_name)
    if not text:
        return 0, "", ""
    save_fired(session_id, fired | {e["id"] for e in fresh})
    stamp = today or time.strftime("%Y-%m-%d")
    for e in fresh:
        if e["once"]:
            retire_once(e["path"], stamp)
    if tool_name == "Agent":
        return 2, "", text + "\n"
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}
    return 0, json.dumps(out), ""


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "compile":
        table = load_table(force=True)
        print(f"compiled {len(table['entries'])} triggered memories from {table['fingerprint']['count']} files -> {table_path()}")
        return 0
    print("usage: python _memory_triggers.py compile", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
