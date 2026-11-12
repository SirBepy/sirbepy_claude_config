"""Data dump and mechanical checks for /grill (spec: the skill's SKILL.md and suspect.md).

Subcommands:
  dump            writes chats/clusters/complaints/git/phase0 JSONL plus summary.md into --out
  check-receipts  verifies every candidate's receipt quote is really on its file:line
  gate            checks the main chat's L2 rows before refuters run
  cost            prints one cost line for a session and its subagents, writes nothing

Stdlib only; run with `python -I`. `dump` writes only inside --out, the rest write nothing.
Every JSONL file holds one object per physical line, so any number in it is a citable
file:line receipt.
"""

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

# Short, common English words that would otherwise make unrelated decisions look alike.
STOP_WORDS = frozenset("""
the and for are but not you all any can was one our out has have this that with from they
will would should could what which when where who why how its into than then them there these
those about just also yes does did
""".split())

COMPLAINT_REGEXES = [re.compile(p, re.IGNORECASE) for p in (
    r"\b(wrong|broken|doesn'?t work|not working|still (fails|broken|wrong))\b",
    r"\b(revert|undo|roll ?back|scrap (that|it))\b",
    r"\b(why (did|is|are) (you|it)|i (told|said|asked) you)\b",
    r"\b(keeps? (doing|happening|breaking|failing|asking)|every (single )?time|already (said|told|asked)|yet again)\b",
    r"\b(too (much|many|slow|long|noisy)|annoying|useless|pointless)\b",
    r"\b(not what (i|we) (asked|meant|wanted)|that'?s not what|that is not what)\b",
    r"\bi (don'?t|do not) (need|want|use|read)\b",
)]

ARCHIVE_HEADER = "| slug | surface | tag | lane | verdict | joe | todo | declined |"
EXAMINE_CAP = 40
IDLE_GAP_S = 600
LATER_FIX_DAYS = 21
CAPS = {"chats": 20, "clusters": EXAMINE_CAP, "complaints": 20, "git": 15}
KINDS = ("main", "sub-with-card", "sub-without-card")


def _default_projects():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude-personal")
    return Path(base) / "projects"


def _default_decisions():
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "claude-conductor" / "subchats"


DEFAULT_DIGESTS = Path.home() / ".claude" / "memory-archive" / "digests"
DEFAULT_ARCHIVE = Path.home() / ".claude" / ".claude" / "grill"


# ---------------------------------------------------------------- small helpers

def iter_lines(path):
    """Physical lines split on \\n only (binary iteration), so a stray \\r stays inside its
    line and line numbers match what a receipt check counts."""
    with open(path, "rb") as fh:
        for raw in fh:
            yield raw.rstrip(b"\n").decode("utf-8", "replace")


def _norm(p):
    return str(p).replace("/", "\\").rstrip("\\").lower()


def _under(path, base):
    """Whole-segment containment: C:\\a\\.claude never matches C:\\a\\.claude-personal."""
    n, b = _norm(path), _norm(base)
    return n == b or n.startswith(b + "\\")


def match_scope(cwd, scopes):
    """The longest scope containing cwd, so nested scopes never double-count.

    Conductor sub worktrees sit under `<scope>\\.claude\\worktrees\\`, so plain containment covers
    them: on 2026-11-12 every worktree or subchat cwd across all transcripts was under a repo's
    own `.claude\\worktrees` (or a cargo-scratch test repo), none under a separate root like D:\\subchats-*.
    """
    best = None
    if not cwd:
        return None
    for s in scopes:
        if _under(cwd, s) and (best is None or len(_norm(s)) > len(_norm(best))):
            best = s
    return best


def _parse_ts(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _round(x):
    return int(math.floor(x + 0.5))


def _folder_name(path):
    return re.split(r"[\\/]", str(path).rstrip("\\/"))[-1]


def scope_slug(scope):
    name = _folder_name(scope).lower()
    return "claude-tooling" if name == ".claude" else name


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=True)


def _write_jsonl(path, rows):
    with open(path, "w", encoding="ascii", newline="") as fh:
        for r in rows:
            fh.write(_dumps(r) + "\n")


def _read_jsonl(path):
    p = Path(path)
    if not p.is_file():
        return []
    rows = []
    for n, line in enumerate(iter_lines(p), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError as e:
                raise ValueError(f"{p}:{n} is not valid JSON ({e})") from None
    return rows


def first_cwd(path):
    """The first record that HAS a cwd: Conductor transcripts open with owner/queue records without one."""
    for line in iter_lines(path):
        if '"cwd"' not in line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("cwd"):
            return r["cwd"]
    return None


# ---------------------------------------------------------------- decisions logs and digests

_HEADER = re.compile(r"^## D(\d+) - (\w+) - (\d{4}-\d{2}-\d{2}) - (.*)$")
_FIELD = re.compile(r"^(Sub|Question|Answer|Decided|Ruled out|Closed by): ?(.*)$")


def parse_decisions(text, path):
    entries = []
    cur = None
    field = None
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.rstrip("\r")
        m = _HEADER.match(line)
        if m:
            cur = {"n": int(m.group(1)), "kind": m.group(2), "date": m.group(3),
                   "label": m.group(4).strip(), "fields": {}}
            entries.append(cur)
            field = None
            continue
        if cur is None:
            continue
        m = _FIELD.match(line)
        if m:
            field = m.group(1)
            cur["fields"][field] = [m.group(2)]
            continue
        if field and (line.startswith("  ") or line.startswith("\t")):
            cur["fields"][field].append(line[2:] if line.startswith("  ") else line[1:])
            continue
        if not line.strip():
            field = None

    out = []
    for e in entries:
        f = {k: "\n".join(v).strip() for k, v in e["fields"].items()}
        out.append({
            "n": e["n"], "kind": e["kind"], "date": e["date"], "label": e["label"],
            "sub": f.get("Sub") or None, "question": f.get("Question", ""),
            "answer": f.get("Answer", ""), "decided": f.get("Decided", ""),
            "ruled_out": f.get("Ruled out", ""), "superseded": "Closed by" in f,
            "ref": f"{path}#D{e['n']}",
        })
    return out


def parse_digest(text):
    d = {"title": "", "date": None, "repo": "", "session": "", "decided": []}
    section = None
    for line in text.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        m = re.match(r"^# Digest:\s*(.*)$", s)
        if m and not d["title"]:
            d["title"] = m.group(1).strip()
            continue
        m = re.match(r"^- Date:\s*(\d{4}-\d{2}-\d{2})", s)
        if m and section is None:
            d["date"] = m.group(1)
            continue
        m = re.match(r"^- Repo:\s*(.*)$", s)
        if m and section is None:
            d["repo"] = m.group(1).strip()
            continue
        m = re.match(r"^- Session:\s*(\S+)", s)
        if m and section is None:
            d["session"] = m.group(1)
            continue
        if s.startswith("## "):
            section = s[3:].strip().lower()
            continue
        if section == "decided" and s:
            body = re.sub(r"^[-*]\s+", "", s)
            if body.lower().rstrip(".") == "none":
                continue
            for piece in re.split(r"(?=Joe:)", body):
                piece = piece.strip().lstrip("-* ").strip()
                if piece:
                    d["decided"].append(piece)
    return d


# ---------------------------------------------------------------- usage

def sum_usage(parent_lines, subagent_line_lists):
    usage = {}
    anon = 0
    stamps = []

    def eat(lines, is_parent):
        nonlocal anon
        for line in lines:
            # Subagent files only contribute usage, so their other records are never parsed.
            if '"usage"' not in line and (not is_parent or '"timestamp"' not in line):
                continue
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict):
                continue
            if is_parent:
                t = _parse_ts(r.get("timestamp"))
                if t is not None:
                    stamps.append((t, r["timestamp"]))
            msg = r.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("usage"), dict):
                # One API message is split over several records sharing message.id; the last one wins.
                key = msg.get("id")
                if not key:
                    anon += 1
                    key = f"__anon{anon}"
                usage[key] = msg["usage"]

    eat(parent_lines, True)
    for lines in subagent_line_lists:
        eat(lines, False)

    def total(k):
        return sum(int(u.get(k) or 0) for u in usage.values())

    inp, cw = total("input_tokens"), total("cache_creation_input_tokens")
    cr, out = total("cache_read_input_tokens"), total("output_tokens")
    stamps.sort(key=lambda x: x[0])
    wall = 0.0
    for (a, _), (b, _) in zip(stamps, stamps[1:]):
        gap = (b - a).total_seconds()
        if 0 < gap <= IDLE_GAP_S:
            wall += gap
    return {
        "input": inp, "cache_write": cw, "cache_read": cr, "output": out,
        "input_equiv": inp + 1.25 * cw + 0.1 * cr + 5 * out,
        "wall_s": wall,
        "first_ts": stamps[0][1] if stamps else None,
        "last_ts": stamps[-1][1] if stamps else None,
    }


def chat_kind(uuid, card_subs, finish_subs):
    if uuid in card_subs:
        return "sub-with-card"
    if uuid in finish_subs:
        return "sub-without-card"
    return "main"


# ---------------------------------------------------------------- clusters

def _tokens(text):
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3 and t not in STOP_WORDS}


def _norm_ref(ref):
    return str(ref).replace("/", "\\").lower()


def cluster(entries, include_refs=(), cap=EXAMINE_CAP):
    by_scope = {}
    for e in entries:
        by_scope.setdefault(e.get("scope"), []).append(e)

    built = []
    for scope, es in by_scope.items():
        groups = []
        for e in sorted(es, key=lambda x: x["date"]):
            toks = _tokens(f"{e.get('question', '')} {e.get('answer', '')}")
            for g in groups:
                union = len(toks | g["tokens"])
                if union and len(toks & g["tokens"]) / union >= 0.5:
                    g["entries"].append(e)
                    g["tokens"] |= toks
                    break
            else:
                groups.append({"entries": [e], "tokens": set(toks)})
        for g in groups:
            es2 = g["entries"]
            d0 = es2[0]["date"]
            built.append({
                "id": es2[0]["ref"], "scope": scope, "rank": 0, "size": len(es2),
                "revisits": sum(1 for x in es2 if x["date"] > d0 or x.get("superseded")),
                "reversed": any(x.get("superseded") for x in es2),
                "examined": False, "first_date": d0, "last_date": max(x["date"] for x in es2),
                "entries": [{"source": x.get("source", "card"), "ref": x["ref"], "date": x["date"],
                             "question": x.get("question", ""), "answer": x.get("answer", ""),
                             "superseded": bool(x.get("superseded"))} for x in es2],
            })

    built.sort(key=lambda c: (-c["revisits"], -c["size"],
                              -date.fromisoformat(c["last_date"]).toordinal(), c["id"]))
    for i, c in enumerate(built, 1):
        c["rank"] = i

    wanted = {_norm_ref(r) for r in include_refs}
    marked = 0
    for c in built:
        if marked < cap and any(_norm_ref(x["ref"]) in wanted for x in c["entries"]):
            c["examined"] = True
            marked += 1
    for c in built:
        if marked >= cap:
            break
        if not c["examined"] and not c["reversed"]:
            c["examined"] = True
            marked += 1
    return built


# ---------------------------------------------------------------- complaints

def complaint_hits(path, scope, window_start, window_end, is_stem):
    hits = []
    seen_first = False
    session = Path(path).stem
    for lineno, line in enumerate(iter_lines(path), 1):
        if '"user"' not in line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if not isinstance(r, dict) or r.get("type") != "user":
            continue
        msg = r.get("message")
        text = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(text, str):
            continue
        if r.get("isMeta") is True or r.get("isSidechain") is True:
            continue
        if r.get("turnOrigin") in ("peer", "system") or r.get("promptSource") in ("peer", "system"):
            continue
        if text.lstrip().startswith("<"):
            continue
        if not seen_first:
            seen_first = True
            # Outside a decisions-log stem the first turn may be an unlogged sub's brief, written
            # by a main chat rather than Joe.
            if not is_stem:
                continue
        t = _parse_ts(r.get("timestamp"))
        if t is None or not (window_start <= t <= window_end):
            continue
        for idx, rx in enumerate(COMPLAINT_REGEXES, 1):
            if rx.search(text):
                hits.append({"session": session, "scope": scope, "file": str(path), "line": lineno,
                             "category": idx, "text": text[:200], "ts": r.get("timestamp")})
    return hits


# ---------------------------------------------------------------- git

def _group(path):
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else parts[0]


def _commit_class(subject):
    if subject.startswith("Revert") or subject.startswith("REVERT:"):
        return "revert"
    if subject.startswith("FEAT:"):
        return "feat"
    if subject.startswith("FIX:"):
        return "fix"
    if re.match(r"^[A-Z]+:", subject):
        return "ignored"
    return "unclassified"


def git_groups(repo, since):
    """Every path group's outcome row, best first; None when `git log` cannot run there."""
    # core.quotepath=off keeps non-ASCII paths readable instead of octal-escaped.
    cmd = ["git", "-c", "core.quotepath=off", "-C", str(repo), "log", f"--since={since}",
           "--no-merges", "--no-renames", "--name-status", "--format=%H%x09%aI%x09%s"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    if proc.returncode != 0:
        return None

    commits = []
    for line in proc.stdout.split("\n"):
        line = line.rstrip("\r")
        if not line.strip():
            continue
        m = re.match(r"^([0-9a-f]{40})\t([^\t]*)\t(.*)$", line)
        if m:
            commits.append({"sha": m.group(1), "date": _parse_ts(m.group(2)), "subject": m.group(3),
                            "changes": []})
            continue
        parts = line.split("\t")
        if commits and len(parts) >= 2:
            commits[-1]["changes"].append((parts[0][:1], parts[-1]))
    commits.reverse()  # oldest first

    stats = {}

    def g(name):
        return stats.setdefault(name, {"total": 0, "feat": 0, "fix": 0, "revert": 0, "ignored": 0,
                                       "unclassified": 0, "links": set(), "atd": set(), "never": set()})

    for c in commits:
        c["class"] = _commit_class(c["subject"])
        c["files"] = {p for _, p in c["changes"]}
        for name in {_group(p) for p in c["files"]}:
            s = g(name)
            s["total"] += 1
            s[c["class"]] += 1

    last_touch = {}
    for i, c in enumerate(commits):
        for p in c["files"]:
            last_touch[p] = i

    added = set()
    for i, c in enumerate(commits):
        for status, p in c["changes"]:
            if status == "A":
                added.add(p)
            elif status == "D" and p in added:
                g(_group(p))["atd"].add(p)
        if c["class"] == "feat":
            for status, p in c["changes"]:
                if status == "A" and last_touch[p] == i:
                    g(_group(p))["never"].add(p)
            for later in commits[i + 1:]:
                if later["class"] != "fix" or c["date"] is None or later["date"] is None:
                    continue
                gap = later["date"] - c["date"]
                if timedelta(0) < gap <= timedelta(days=LATER_FIX_DAYS):
                    for p in c["files"] & later["files"]:
                        g(_group(p))["links"].add(f"{c['sha'][:7]}->{later['sha'][:7]}")

    rows = []
    for name, s in stats.items():
        rows.append({"repo": str(repo), "group": name, "total": s["total"], "feat": s["feat"],
                     "fix": s["fix"], "revert": s["revert"], "ignored": s["ignored"],
                     "unclassified": s["unclassified"],
                     "later_fix_links": sorted(s["links"])[:10],
                     "added_then_deleted": sorted(s["atd"])[:10],
                     "never_touched": sorted(s["never"])[:10]})
    rows.sort(key=lambda r: (-r["total"], r["group"]))
    return rows


def git_outcome(repo, since):
    return (git_groups(repo, since) or [])[:CAPS["git"]]


# ---------------------------------------------------------------- phase 0

def newest_archive(archive_dir, scope):
    d = Path(archive_dir) / scope_slug(scope)
    if not d.is_dir():
        return None
    files = sorted(p for p in d.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", p.name))
    return files[-1] if files else None


ARCHIVE_COLUMNS = ("slug", "surface", "tag", "lane", "verdict", "joe", "todo", "declined")


def _table_cells(line):
    """Cells of one markdown table row; an escaped `\\|` stays inside its cell."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def parse_archive_table(text, skipped=None):
    """Rows of the first table whose header is the archive header (cell padding ignored).
    A row with the wrong cell count is appended to `skipped` instead of vanishing."""
    lines = text.replace("\r\n", "\n").split("\n")
    rows = []
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and tuple(_table_cells(line)) == ARCHIVE_COLUMNS:
            for row in lines[i + 2:]:
                if not row.strip().startswith("|"):
                    break
                cells = _table_cells(row)
                if len(cells) == len(ARCHIVE_COLUMNS):
                    rows.append(dict(zip(ARCHIVE_COLUMNS, cells)))
                elif skipped is not None:
                    skipped.append(row.strip())
            break
    return rows


def _todo_state(todo):
    if not todo:
        return "not-picked"
    repo, _, tid = todo.rpartition(":")
    if not repo or not tid or not Path(repo).is_dir():
        return "missing"
    todos = Path(repo) / ".claude" / "todos"
    # Ids are <label>-<number> (pc-0450); a bare prefix like "pc" would glob every todo.
    if not re.fullmatch(r"[A-Za-z0-9]+-[0-9]+", tid):
        return "missing"
    pattern = f"{glob.escape(tid)}-*.md"
    if list(todos.glob(pattern)):
        return "open"
    # done/ also holds todos archived as dead, so "closed" is not proof of a fix.
    if list((todos / "done").glob(pattern)):
        return "closed"
    return "missing"


def phase0(archive_dir, scopes, warnings=None):
    """Last run's rows per scope. Problems that would silently empty Phase 0 (no archive table,
    unparsable rows, two scopes sharing one archive slug) go to `warnings` when given."""
    out = []
    warn = warnings if warnings is not None else []
    slugs = [scope_slug(s) for s in scopes]
    for s in sorted({x for x in slugs if slugs.count(x) > 1}):
        warn.append(f"two scopes share the archive slug {s!r}; their archives collide")
    for scope in scopes:
        path = newest_archive(archive_dir, scope)
        if path is None:
            continue
        seen = set()
        skipped = []
        rows = parse_archive_table(path.read_text(encoding="utf-8", errors="replace"), skipped)
        if not rows:
            warn.append(f"{path} has no archive table rows (header must be: {ARCHIVE_HEADER})")
        for bad in skipped:
            warn.append(f"{path}: skipped a row without 8 cells: {bad[:120]}")
        for row in rows:
            if row["slug"] in seen or not row["slug"]:
                continue
            seen.add(row["slug"])
            if re.fullmatch(r"[0-9]*", row["declined"]):
                declined = int(row["declined"] or 0)
            else:
                declined = 0
                warn.append(f"{path}: slug {row['slug']} has a non-numeric declined cell "
                            f"{row['declined']!r}, read as 0")
            out.append({"scope": scope, "slug": row["slug"], "surface": row["surface"],
                        "todo": row["todo"], "state": _todo_state(row["todo"]),
                        "declined": declined, "never_raise": declined >= 2})
    return out


# ---------------------------------------------------------------- receipts and gate

def _receipt_shape(r, allow_none):
    if not isinstance(r, dict):
        return "receipt is not an object"
    if "none_searched" in r:
        if not allow_none:
            return "none_searched is not allowed here"
        v = r.get("none_searched")
        if not isinstance(v, str) or len(v.strip()) < 8:
            return "none_searched under 8 chars"
        return None
    f, line, quote = r.get("file"), r.get("line"), r.get("quote")
    if not isinstance(f, str) or not f:
        return "missing file"
    if not os.path.isabs(f):
        return f"file is not absolute: {f}"
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        return "line is not a positive integer"
    if not isinstance(quote, str) or len(quote) < 8:
        return "quote under 8 chars"
    return None


def _receipt_content(r):
    f, n, quote = r["file"], r["line"], r["quote"]
    if not Path(f).is_file():
        return f"no such file: {f}"
    try:
        for i, text in enumerate(iter_lines(f), 1):
            if i == n:
                return None if quote in text else f"quote not on line {n}"
    except OSError as e:
        return f"cannot read {f}: {e}"
    return f"line {n} is past the end of the file"


def verify_receipt(r):
    err = _receipt_shape(r, allow_none=True)
    if err or "none_searched" in r:
        return err
    return _receipt_content(r)


def _alnum(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _real(path):
    """Canonical form for path comparison: `..`, 8.3 short names (TEMP on CI) and junctions
    otherwise make one file look like two."""
    return os.path.realpath(str(path))


def _change_file_ok(f, rundir, scopes, projects_dir, cluster_rec):
    real = _real(f)
    name = Path(real).name.lower()
    if name == "clusters.jsonl" and _norm(Path(real).parent) == _norm(_real(rundir)):
        return False
    if _norm(Path(real).parent) == _norm(_real(rundir)):
        return True
    if any(_under(real, _real(s)) for s in scopes):
        return True
    if projects_dir and _under(real, _real(projects_dir)) and name.endswith(".jsonl"):
        return True
    for e in (cluster_rec or {}).get("entries", []):
        if _norm(_real(str(e.get("ref", "")).rsplit("#", 1)[0])) == _norm(real):
            return True
    return False


REQUIRED_ROW_KEYS = ("slug", "cluster", "scope", "surface", "decision", "alternative", "receipt", "verdict")


def gate(rows, clusters, rundir, scopes, projects_dir, allow_all_keep):
    clusters = [c for c in clusters if isinstance(c, dict) and isinstance(c.get("id"), str)]
    examined = [c["id"] for c in clusters if c.get("examined")]
    if not examined and not rows:
        return 0, "KEEP=0 CHANGE=0 (no decisions in window)"
    by_id = {c["id"]: c for c in clusters}
    fails = []
    for n, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            fails.append((2, f"row{n}", "row is not a JSON object"))
    rows = [r for r in rows if isinstance(r, dict)]

    ids = [r.get("cluster") if isinstance(r.get("cluster"), str) else repr(r.get("cluster")) for r in rows]
    for cid in sorted({i for i in ids if ids.count(i) > 1}, key=str):
        fails.append((1, cid, "cluster has more than one row"))
    for cid in sorted(set(examined) - set(ids)):
        fails.append((1, cid, "examined cluster has no row"))
    for cid in sorted({i for i in ids if i not in set(examined)}, key=str):
        fails.append((1, cid, "row names a cluster that is not examined"))

    reasons = {}
    for r in rows:
        slug = r.get("slug") or "?"
        verdict = r.get("verdict")
        missing = [k for k in REQUIRED_ROW_KEYS if k not in r]
        if missing:
            fails.append((2, slug, f"missing {', '.join(missing)}"))
        for k in ("slug", "cluster", "scope", "surface", "decision", "alternative"):
            if k in r and (not isinstance(r[k], str) or not r[k].strip()):
                fails.append((2, slug, f"empty or non-text {k}"))
        if (isinstance(r.get("decision"), str) and isinstance(r.get("alternative"), str)
                and r["decision"].strip() and _alnum(r["decision"]) == _alnum(r["alternative"])):
            fails.append((2, slug, "alternative repeats the decision"))
        if "verdict" in r and verdict not in ("KEEP", "CHANGE-CANDIDATE"):
            fails.append((3, slug, f"verdict {verdict!r}"))
        for key in ("receipt", "alt_receipt"):
            # An optional alt_receipt sent as JSON null means "none", same as check-receipts.
            if key not in r or (key == "alt_receipt" and r[key] is None):
                continue
            rec = r[key]
            err = _receipt_shape(rec, allow_none=(key == "receipt" and verdict == "KEEP"))
            if err:
                fails.append((4, slug, f"{key}: {err}"))
                continue
            if "none_searched" in rec:
                continue
            err = _receipt_content(rec)
            if err:
                fails.append((5, slug, f"{key}: {err}"))
            elif key == "receipt" and verdict == "CHANGE-CANDIDATE" and not _change_file_ok(
                    rec["file"], rundir, scopes, projects_dir,
                    by_id.get(r["cluster"]) if isinstance(r.get("cluster"), str) else None):
                fails.append((5, slug, f"receipt file is not outcome evidence for this cluster: {rec['file']}"))
        if verdict == "KEEP":
            wf = r.get("why_fails")
            if not isinstance(wf, str) or len(wf.strip()) < 20:
                fails.append((6, slug, "why_fails missing or under 20 chars"))
            else:
                reasons.setdefault(" ".join(wf.lower().split()), []).append(slug)
    for slugs in reasons.values():
        if len(slugs) > 1:
            for slug in slugs:
                fails.append((6, slug, "why_fails repeats another row"))

    keep = sum(1 for r in rows if r.get("verdict") == "KEEP")
    change = sum(1 for r in rows if r.get("verdict") == "CHANGE-CANDIDATE")
    need = max(1, math.ceil(0.1 * len(rows)))
    if change < need and not allow_all_keep:
        fails.append((7, "-", f"{change} CHANGE-CANDIDATE rows, need at least {need} (or --allow-all-keep)"))

    lines = [f"FAIL rule {rule} {slug}: {msg}" for rule, slug, msg in fails]
    last = f"KEEP={keep} CHANGE={change}"
    if allow_all_keep:
        last += f" (all-keep allowed: {allow_all_keep})"
    lines.append(last)
    return (1 if fails else 0), "\n".join(lines)


# ---------------------------------------------------------------- dump

def _window(now_arg, days):
    now = _parse_now(now_arg)
    start_day = (now - timedelta(days=days)).date()
    return now, datetime.combine(start_day, time(0), tzinfo=now.tzinfo)


def _parse_now(now_arg):
    if not now_arg:
        return datetime.now().astimezone()
    t = datetime.fromisoformat(now_arg.replace("Z", "+00:00"))
    return t if t.tzinfo else t.astimezone()


def _cell(s, limit=160):
    s = " ".join(str(s).split())
    if len(s) > limit:
        s = s[:limit - 3] + "..."
    return s.replace("|", "\\|")


def _subagent_files(transcript):
    d = transcript.parent / transcript.stem / "subagents"
    return sorted(d.glob("agent-*.jsonl")) if d.is_dir() else []


def cmd_dump(args):
    scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
    now, start = _window(args.now, args.days)
    projects = Path(args.projects_dir) if args.projects_dir else _default_projects()
    decisions_dir = Path(args.decisions_dir) if args.decisions_dir else _default_decisions()
    digests_dir = Path(args.digests_dir) if args.digests_dir else DEFAULT_DIGESTS
    archive_dir = Path(args.archive_dir) if args.archive_dir else DEFAULT_ARCHIVE
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    def in_window(day):
        try:
            return start.date() <= date.fromisoformat(day) <= now.date()
        except (TypeError, ValueError):
            return False

    top = {p.stem: p for p in sorted(projects.glob("*/*.jsonl"))} if projects.is_dir() else {}
    scope_cache = {}

    def scope_of(uuid):
        if uuid not in scope_cache:
            scope_cache[uuid] = match_scope(first_cwd(top[uuid]), scopes)
        return scope_cache[uuid]

    # Decisions logs: kinds come from every entry, clusters only from in-window card entries.
    stems, card_subs, finish_subs, all_entries = set(), set(), set(), []
    if decisions_dir.is_dir():
        for f in sorted(decisions_dir.glob("*.decisions.md")):
            stem = f.name[:-len(".decisions.md")]
            stems.add(stem)
            for e in parse_decisions(f.read_text(encoding="utf-8", errors="replace"), str(f)):
                e["owner"] = e["sub"] or stem
                if e["sub"]:
                    (card_subs if e["kind"] == "card" else finish_subs).add(e["sub"])
                all_entries.append(e)

    unresolved_chats = 0
    missing_subs = set()
    gone_logs = set()
    warnings = []
    entries = []
    for e in all_entries:
        if not in_window(e["date"]):
            continue
        if e["owner"] not in top:
            if e["sub"]:
                missing_subs.add(e["sub"])
            elif e["kind"] == "card":
                gone_logs.add(e["owner"])
            continue
        if e["kind"] != "card":
            continue
        sc = scope_of(e["owner"])
        if sc is None:
            continue
        entries.append({"source": "card", "ref": e["ref"], "date": e["date"], "question": e["question"],
                        "answer": e["answer"], "superseded": e["superseded"], "scope": sc})

    if digests_dir.is_dir():
        for f in sorted(digests_dir.glob("*.md")):
            d = parse_digest(f.read_text(encoding="utf-8", errors="replace"))
            if not in_window(d["date"]) or not d["decided"]:
                continue
            if d["session"] in top:
                sc = scope_of(d["session"])
                if sc is None:
                    continue
            else:
                names = [s for s in scopes if _folder_name(s).lower() == d["repo"].lower()]
                if not names:
                    unresolved_chats += 1
                    continue
                sc = names[0]
            for i, piece in enumerate(d["decided"]):
                entries.append({"source": "digest", "ref": f"{f}#{i}", "date": d["date"],
                                "question": d["title"], "answer": piece, "superseded": False, "scope": sc})

    include = []
    for item in [x.strip() for x in (args.include_refs or "").split(",") if x.strip()]:
        stem, _, dn = item.partition("#")
        include.append(f"{decisions_dir / (stem + '.decisions.md')}#{dn}")
    clusters = cluster(entries, include, EXAMINE_CAP)
    found_refs = {_norm_ref(x["ref"]) for c in clusters for x in c["entries"]}
    for r in include:
        if _norm_ref(r) not in found_refs:
            warnings.append(f"--include-refs {r} matched no in-window, in-scope card entry")
    if gone_logs:
        warnings.append(f"{len(gone_logs)} decisions log(s) whose main chat transcript is gone; their "
                        f"in-window card entries were dropped: {', '.join(sorted(gone_logs))}")

    chats, complaints = [], []
    for uuid, path in top.items():
        try:
            if path.stat().st_mtime < start.timestamp():
                continue
        except OSError:
            continue
        sc = scope_of(uuid)
        if sc is None:
            unresolved_chats += 1
            continue
        kind = chat_kind(uuid, card_subs, finish_subs)
        u = sum_usage(iter_lines(path), [iter_lines(s) for s in _subagent_files(path)])
        chats.append({"session": uuid, "scope": sc, "kind": kind, "first_ts": u["first_ts"],
                      "last_ts": u["last_ts"], "wall_s": _round(u["wall_s"]), "input": u["input"],
                      "cache_write": u["cache_write"], "cache_read": u["cache_read"], "output": u["output"],
                      "input_equiv": _round(u["input_equiv"])})
        if kind == "main":
            complaints.extend(complaint_hits(str(path), sc, start, now, uuid in stems))

    chats.sort(key=lambda c: (-c["input_equiv"], c["session"]))
    per_session = {}
    for h in complaints:
        s = per_session.setdefault(h["session"], {"n": 0, "newest": ""})
        s["n"] += 1
        s["newest"] = max(s["newest"], h.get("ts") or "")
    complaints.sort(key=lambda h: (-per_session[h["session"]]["n"], _neg_str(per_session[h["session"]]["newest"]),
                                   h["session"], h["line"], h["category"]))
    git_rows = []
    git_cut = 0
    since = start.strftime("%Y-%m-%dT00:00:00")
    for sc in scopes:
        groups = git_groups(sc, since)
        if groups is None:
            warnings.append(f"git log failed for {sc}; L4 has no rows for it")
            continue
        git_rows.extend(groups[:CAPS["git"]])
        git_cut += max(0, len(groups) - CAPS["git"])
    p0 = phase0(archive_dir, scopes, warnings)
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    files = {"chats": chats, "clusters": clusters, "complaints": complaints, "git": git_rows, "phase0": p0}
    for name, rows in files.items():
        _write_jsonl(out / f"{name}.jsonl", rows)

    summary = _summary(out, args, scopes, now, start, files, archive_dir, unresolved_chats,
                       len(missing_subs), warnings, git_cut)
    with open(out / "summary.md", "w", encoding="utf-8", newline="") as fh:
        fh.write(summary)
    return 0


def _neg_str(s):
    """Sort key that orders ISO timestamps newest first inside an ascending sort."""
    return tuple(-ord(ch) for ch in s)


def _summary(out, args, scopes, now, start, files, archive_dir, unresolved_chats, missing_subs, warnings, git_cut):
    chats, clusters, complaints = files["chats"], files["clusters"], files["complaints"]
    git_rows, p0 = files["git"], files["phase0"]
    L = [f"# /grill dump", "",
         f"Window: {start:%Y-%m-%d} to {now:%Y-%m-%d} ({args.days} days). Run dir: {out}", "",
         "Scopes:"] + [f"- {s}" for s in scopes] + [""]
    L += ["Every row cites its run-dir `file:line`; cite that as the receipt. Cells are cut to fit:",
          "read the full text from the cited JSONL line, never from this table.", ""]
    if warnings:
        L += ["## Warnings", ""] + [f"- {w}" for w in warnings] + [""]

    L += ["## Totals (all chats in scope)", "", "| scope | kind | chats | input-equiv | wall min |",
          "|---|---|---|---|---|"]
    for s in scopes:
        for k in KINDS:
            mine = [c for c in chats if c["scope"] == s and c["kind"] == k]
            L.append(f"| {s} | {k} | {len(mine)} | {sum(c['input_equiv'] for c in mine)} | "
                     f"{_round(sum(c['wall_s'] for c in mine) / 60)} |")
    L.append("")

    L += ["## Phase 0", ""]
    for s in scopes:
        a = newest_archive(archive_dir, s)
        L.append(f"- {s}: newest archive {a} ({a.stem})" if a else f"- {s}: no archive yet")
    L += ["", "| receipt | scope | slug | surface | todo | state | declined | never raise |",
          "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(p0, 1):
        L.append(f"| `{out / 'phase0.jsonl'}:{i}` | {r['scope']} | {r['slug']} | {_cell(r['surface'])} | "
                 f"{_cell(r['todo'])} | {r['state']} | {r['declined']} | {'yes' if r['never_raise'] else 'no'} |")
    never = [r["slug"] for r in p0 if r["never_raise"]]
    L += ["", f"Never raise again: {', '.join(never) if never else 'none'}", ""]

    L += [f"## L1 chats (top {CAPS['chats']} by input-equiv)", "",
          "| receipt | session | scope | kind | input-equiv | wall min |", "|---|---|---|---|---|---|"]
    for i, c in enumerate(chats[:CAPS["chats"]], 1):
        L.append(f"| `{out / 'chats.jsonl'}:{i}` | {c['session']} | {c['scope']} | {c['kind']} | "
                 f"{c['input_equiv']} | {_round(c['wall_s'] / 60)} |")
    if len(chats) > CAPS["chats"]:
        L.append(f"\n{len(chats) - CAPS['chats']} more not shown")
    L.append("")

    examined = [(i, c) for i, c in enumerate(clusters, 1) if c["examined"]]
    L += ["## L2 clusters (examined)", "",
          "| receipt | rank | scope | size | revisits | first | last | first entry: question -> answer |",
          "|---|---|---|---|---|---|---|---|"]
    for i, c in examined:
        e = c["entries"][0]
        L.append(f"| `{out / 'clusters.jsonl'}:{i}` | {c['rank']} | {c['scope']} | {c['size']} | "
                 f"{c['revisits']} | {c['first_date']} | {c['last_date']} | "
                 f"{_cell(e['question'] + ' -> ' + e['answer'])} |")
    not_examined = len(clusters) - len(examined)
    if not_examined:
        L.append(f"\n{not_examined} more not shown (not examined)")
    L +=["", "### Reversed, not examined (patterns, no verdict)", ""]
    rev = [(i, c) for i, c in enumerate(clusters, 1) if c["reversed"] and not c["examined"]]
    for i, c in rev:
        L.append(f"- `{out / 'clusters.jsonl'}:{i}` revisits {c['revisits']}: {_cell(c['entries'][0]['question'])}")
    if not rev:
        L.append("none")
    L.append("")

    L += ["## L4 git (commit outcomes per path group)", "",
          "| receipt | repo | group | total | feat | fix | revert | later fixes | added then deleted | never touched |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    # git.jsonl already holds at most CAPS["git"] groups per scope; git_cut counts the rest.
    for i, g in enumerate(git_rows, 1):
        L.append(f"| `{out / 'git.jsonl'}:{i}` | {g['repo']} | {g['group']} | {g['total']} | {g['feat']} | "
                 f"{g['fix']} | {g['revert']} | {len(g['later_fix_links'])} | {len(g['added_then_deleted'])} | "
                 f"{len(g['never_touched'])} |")
    if git_cut:
        L.append(f"\n{git_cut} more not shown (path groups)")
    L.append("")

    L += [f"## L5 complaints (top {CAPS['complaints']}, sessions by hit count)", "",
          "| receipt | session | date | category | text |", "|---|---|---|---|---|"]
    for i, h in enumerate(complaints[:CAPS["complaints"]], 1):
        L.append(f"| `{out / 'complaints.jsonl'}:{i}` | {h['session']} | {(h.get('ts') or '')[:10]} | "
                 f"{h['category']} | {_cell(h['text'], 120)} |")
    if len(complaints) > CAPS["complaints"]:
        L.append(f"\n{len(complaints) - CAPS['complaints']} more not shown")
    L.append("")

    L += ["## Unresolved (counted only, never rows)", "",
          f"- in-window chats outside the scope (or unmatched): {unresolved_chats}",
          f"- `Sub:` uuids with no transcript: {missing_subs}", ""]
    return "\n".join(L)


# ---------------------------------------------------------------- other commands

def cmd_check_receipts(args):
    path = Path(args.rows)
    if not path.is_file():
        print(f"no such rows file: {path}")
        return 1
    bad = 0
    for n, line in enumerate(iter_lines(path), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            print(f"BAD line{n} not JSON")
            bad += 1
            continue
        if not isinstance(r, dict):
            print(f"BAD line{n} not a JSON object")
            bad += 1
            continue
        slug = r.get("slug") or f"line{n}"
        err = None
        if "receipt" not in r:
            err = "missing receipt"
        elif isinstance(r["receipt"], dict) and "none_searched" in r["receipt"]:
            err = "receipt: a candidate needs a real {file, line, quote}, not none_searched"
        else:
            e = verify_receipt(r["receipt"])
            err = f"receipt: {e}" if e else None
        if err is None and r.get("alt_receipt") is not None:
            alt = r["alt_receipt"]
            e = _receipt_shape(alt, allow_none=False) or _receipt_content(alt)
            err = f"alt_receipt: {e}" if e else None
        if err:
            print(f"BAD {slug} {err}")
            bad += 1
        else:
            print(f"OK {slug}")
    return 1 if bad else 0


def cmd_gate(args):
    clusters_path = Path(args.clusters)
    # A mistyped --clusters path must not read as "no decisions in window" and pass.
    if not clusters_path.is_file():
        print(f"FAIL rule 1 -: no clusters file at {clusters_path}")
        return 1
    try:
        rows = _read_jsonl(args.rows)
        clusters = _read_jsonl(clusters_path)
    except ValueError as e:
        print(f"FAIL rule 2 -: {e}")
        return 1
    scopes = [s.strip() for s in args.scope.split(",") if s.strip()]
    projects = Path(args.projects_dir) if args.projects_dir else _default_projects()
    code, text = gate(rows, clusters, str(clusters_path.resolve().parent), scopes, str(projects),
                      args.allow_all_keep)
    print(text)
    return code


def cmd_cost(args):
    projects = Path(args.projects_dir) if args.projects_dir else _default_projects()
    hits = sorted(projects.glob(f"*/{glob.escape(args.session)}.jsonl")) if projects.is_dir() else []
    if not hits:
        print(f"no transcript named {args.session}.jsonl under {projects}")
        return 1
    path = hits[0]
    subs = _subagent_files(path)
    u = sum_usage(iter_lines(path), [iter_lines(s) for s in subs])
    print(f"Cost: main {_round(u['input_equiv'])} input-equiv tokens, {len(subs)} agents, "
          f"{_round(u['wall_s'] / 60)} min")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="grill_dump.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--scope", required=True)
    d.add_argument("--days", type=int, default=30)
    d.add_argument("--now")
    d.add_argument("--include-refs", default="")
    d.add_argument("--projects-dir")
    d.add_argument("--decisions-dir")
    d.add_argument("--digests-dir")
    d.add_argument("--archive-dir")
    d.add_argument("--out", required=True)
    c = sub.add_parser("check-receipts")
    c.add_argument("rows")
    g = sub.add_parser("gate")
    g.add_argument("rows")
    g.add_argument("--clusters", required=True)
    g.add_argument("--scope", required=True)
    g.add_argument("--projects-dir")
    g.add_argument("--allow-all-keep")
    k = sub.add_parser("cost")
    k.add_argument("--session", required=True)
    k.add_argument("--projects-dir")
    args = parser.parse_args(argv)
    return {"dump": cmd_dump, "check-receipts": cmd_check_receipts, "gate": cmd_gate,
            "cost": cmd_cost}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
