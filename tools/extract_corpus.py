"""Extract a reusable transcript corpus for hook/pattern measurement.

Walks `~/.claude/projects/**/*.jsonl` (or `--root`) and writes deduped JSONL
rows of `{tool, count, payload}` for a requested tool set, to a caller-named
`--out` path so two measurements never clobber each other. This is the
extractor half of the hook doctrine's "measure against a real corpus BEFORE
wiring anything" rule (PLAN.md); see .claude/todos/done/466 for why it exists
as a durable script instead of a per-session rebuild.

NOT a ci/run_all.py check: it reads the dev's whole transcript history and
takes minutes, neither of which belongs in the fast mechanical-check floor.

Streams every transcript line by line and never holds a whole file in memory,
and never prints transcript content to stdout - only file/line/row counts.

Usage:
    python tools/extract_corpus.py --tools Bash,PowerShell --out C:\\tmp\\corpus.jsonl
    python tools/extract_corpus.py --tools Write,Edit,MultiEdit --out C:\\tmp\\writes.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

# Tool name -> function extracting the one string a pattern should be
# measured against, or None if this tool_use block has nothing usable.
COMMAND_TOOLS = {"Bash", "PowerShell"}
CONTENT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def payload_for(tool: str, inp: dict):
    if tool in COMMAND_TOOLS:
        cmd = inp.get("command")
        return cmd if isinstance(cmd, str) and cmd.strip() else None
    if tool == "Write":
        text = inp.get("content")
        return text if isinstance(text, str) and text.strip() else None
    if tool == "Edit":
        text = inp.get("new_string")
        return text if isinstance(text, str) and text.strip() else None
    if tool == "MultiEdit":
        parts = [
            e.get("new_string") for e in (inp.get("edits") or [])
            if isinstance(e, dict) and isinstance(e.get("new_string"), str)
        ]
        joined = "\n".join(p for p in parts if p.strip())
        return joined if joined.strip() else None
    if tool == "NotebookEdit":
        text = inp.get("new_source")
        return text if isinstance(text, str) and text.strip() else None
    return None


def extract(root: Path, tools: set) -> tuple:
    seen = {}
    files = 0
    lines = 0
    for jf in root.rglob("*.jsonl"):
        files += 1
        try:
            fh = jf.open("r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for raw in fh:
                lines += 1
                if '"tool_use"' not in raw:
                    continue
                try:
                    rec = json.loads(raw)
                except Exception:
                    continue
                content = (rec.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    tool = block.get("name")
                    if tool not in tools:
                        continue
                    payload = payload_for(tool, block.get("input") or {})
                    if payload is None:
                        continue
                    key = (tool, payload)
                    seen[key] = seen.get(key, 0) + 1
    return seen, files, lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tools", required=True, help="comma-separated tool names, e.g. Bash,PowerShell")
    ap.add_argument("--out", required=True, help="output JSONL path (caller-named, never overwritten silently by another run)")
    ap.add_argument("--root", default=None, help="transcript root, default ~/.claude/projects")
    args = ap.parse_args()

    tools = {t.strip() for t in args.tools.split(",") if t.strip()}
    unknown = tools - COMMAND_TOOLS - CONTENT_TOOLS
    if unknown:
        print(f"ERROR: unsupported tool(s) {sorted(unknown)}; known: {sorted(COMMAND_TOOLS | CONTENT_TOOLS)}")
        return 2

    root = Path(args.root) if args.root else Path.home() / ".claude" / "projects"
    if not root.is_dir():
        print(f"ERROR: transcript root {root} is not a directory")
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen, files, lines = extract(root, tools)

    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        for (tool, payload), count in seen.items():
            fh.write(json.dumps({"tool": tool, "count": count, "payload": payload}, ensure_ascii=False) + "\n")

    total = sum(seen.values())
    print(f"root={root} files={files} jsonl_lines={lines}")
    print(f"unique_rows={len(seen)} total_invocations={total}")
    for tool in sorted(tools):
        n = sum(1 for (t, _) in seen if t == tool)
        print(f"  {tool}: unique={n}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
