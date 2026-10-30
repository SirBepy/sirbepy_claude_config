"""Counts how often each skill was invoked across past Claude Code transcripts.

Run: python skills/global-claude-folder-audit/count_invocations.py [--json]

Two invocation shapes are counted, because they are the two ways a skill fires:
- the model calling the Skill tool (an assistant `tool_use` named `Skill`), and
- the dev typing `/name` (a user turn carrying `<command-name>/name</command-name>`).
A typed slash command that then loads its skill can show up as both; that double count is
accepted, since the audit only needs "used a lot / rarely / never", not exact totals.

Raw transcripts only reach back as far as the harness keeps them (older ones are compressed into
memory-archive digests and carry no tool calls), so the output states the window it covers and
each skill's creation date: zero uses for a skill added last week is not evidence it is dead.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HOME_CLAUDE = Path.home() / ".claude"
COMMAND_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")


def _texts(content):
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                yield item.get("text") or ""


def invocations_in_line(record):
    """Return the set of skill names this one transcript record invokes."""
    found = set()
    message = record.get("message")
    if not isinstance(message, dict):
        return found
    content = message.get("content")
    if record.get("type") == "assistant" and isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_use" and item.get("name") == "Skill":
                name = (item.get("input") or {}).get("skill")
                if name:
                    found.add(name.lstrip("/"))
    elif record.get("type") == "user":
        for text in _texts(content):
            found.update(m.lstrip("/") for m in COMMAND_RE.findall(text))
    return found


def session_id(path: Path, projects: Path) -> str:
    # A subagent transcript lives at <project>/<session>/subagents/<agent>.jsonl and belongs
    # to its parent session, so it must not inflate the distinct-session count.
    rel = path.relative_to(projects).parts
    return rel[1] if len(rel) > 2 else path.stem


def scan(projects: Path):
    stats = {}
    window = [None, None]
    for path in projects.rglob("*.jsonl"):
        sid = session_id(path, projects)
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with handle:
            for line in handle:
                # Cheap substring prefilter: json.loads on every line of ~7 GB is the slow part.
                if '"Skill"' not in line and "<command-name>" not in line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                names = invocations_in_line(record)
                if not names:
                    continue
                ts = record.get("timestamp") or ""
                if ts:
                    window[0] = ts if window[0] is None or ts < window[0] else window[0]
                    window[1] = ts if window[1] is None or ts > window[1] else window[1]
                for name in names:
                    entry = stats.setdefault(name, {"invocations": 0, "sessions": set(), "last_used": ""})
                    entry["invocations"] += 1
                    entry["sessions"].add(sid)
                    if ts > entry["last_used"]:
                        entry["last_used"] = ts
    return stats, window


def local_skills(skills_dir: Path, repo: Path):
    out = {}
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        name = skill_md.parent.name
        rel = skill_md.relative_to(repo).as_posix() if skill_md.is_relative_to(repo) else str(skill_md)
        created = subprocess.run(
            ["git", "-C", str(repo), "log", "--diff-filter=A", "--format=%aI", "-1", "--", rel],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        out[name] = created[:10]
    return out


def build_report(stats, window, skills):
    rows = []
    for name, created in skills.items():
        entry = stats.get(name, {"invocations": 0, "sessions": set(), "last_used": ""})
        rows.append({
            "skill": name,
            "invocations": entry["invocations"],
            "sessions": len(entry["sessions"]),
            "last_used": entry["last_used"][:10],
            "created": created,
        })
    rows.sort(key=lambda r: (r["sessions"], r["invocations"], r["skill"]))
    external = sorted(
        ({"skill": n, "invocations": e["invocations"], "sessions": len(e["sessions"])}
         for n, e in stats.items() if n not in skills),
        key=lambda r: -r["sessions"],
    )
    return {"window": {"from": (window[0] or "")[:10], "to": (window[1] or "")[:10]},
            "local": rows, "external": external}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", type=Path, default=HOME_CLAUDE / "projects")
    parser.add_argument("--skills", type=Path, default=HOME_CLAUDE / "skills")
    parser.add_argument("--repo", type=Path, default=HOME_CLAUDE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    stats, window = scan(args.projects)
    report = build_report(stats, window, local_skills(args.skills, args.repo))
    if args.json:
        print(json.dumps(report, indent=1))
        return 0
    w = report["window"]
    print(f"window: {w['from']} .. {w['to']} (raw transcripts only)")
    print(f"{'skill':32} {'sessions':>8} {'calls':>6}  {'last used':10}  created")
    for r in report["local"]:
        print(f"{r['skill']:32} {r['sessions']:>8} {r['invocations']:>6}  {r['last_used'] or '-':10}  {r['created'] or '?'}")
    print("\nnot a local skill dir (plugins, built-ins, aliases):")
    for r in report["external"]:
        print(f"  {r['skill']:30} {r['sessions']:>8} {r['invocations']:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
