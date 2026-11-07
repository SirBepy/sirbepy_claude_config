"""PreToolUse hook (todo 1252): a Conductor MCP tool is not called before its
schema was loaded with ToolSearch.

Canary, 2026-11-07: the harness does NOT reject a blind call to a deferred
tool. `browser_find` called with an invented `foo` param, no ToolSearch first,
reached the tool itself and came back with the tool's own "Provide either
text or regex" error, not an InputValidationError. So the model can guess
params, read the tool's one-gap-at-a-time error, and retry; on 2026-10-27 that
loop made four `write_draft` calls and Joe saw four draft windows.

This gate denies the first call to an `mcp__cc_conductor__*` tool until this
session's transcript shows the tool was loaded: a ToolSearch call whose
`select:` list names it, or a ToolSearch result carrying a `tool_reference`
for it. A ToolSearch that named the tool counts even when it returned nothing
(a tool that was never deferred), so the gate cannot deadlock. Plain text that
merely lists tool names (the deferred-tools reminder) proves nothing and is
ignored: only structured tool_use / tool_result blocks count.

Names proven loaded are cached per session in the temp dir so the transcript
(megabytes) is scanned at most once per tool, not on every call.

Fails open on any internal error: this runs on every Conductor tool call.
"""

import json
import re
import sys
import tempfile
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[deferred-tool-blind-call-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

TOOL_PREFIX = "mcp__cc_conductor__"
CACHE_DIR = Path(tempfile.gettempdir()) / "claude-deferred-tool-guard"


def matches_tool(name: str) -> bool:
    return name.startswith(TOOL_PREFIX) and len(name) > len(TOOL_PREFIX)


def _names_in_select_query(query: str) -> set[str]:
    m = re.match(r"\s*select:(.*)", query, re.IGNORECASE | re.DOTALL)
    if not m:
        return set()
    return {part.strip() for part in m.group(1).split(",") if part.strip()}


def _walk_tool_references(node, found: set[str]) -> None:
    if isinstance(node, dict):
        if node.get("type") == "tool_reference" and isinstance(node.get("tool_name"), str):
            found.add(node["tool_name"])
        for value in node.values():
            _walk_tool_references(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_tool_references(item, found)


def loaded_tool_names(transcript_path: str) -> set[str]:
    """Names (as ToolSearch spelled them, or full tool_reference names) that
    the transcript proves were loaded."""
    found: set[str] = set()
    if not transcript_path:
        return found
    p = Path(transcript_path)
    if not p.is_file():
        return found
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"ToolSearch"' not in line and "tool_reference" not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") == "ToolSearch":
                    query = (block.get("input") or {}).get("query")
                    if isinstance(query, str):
                        found |= _names_in_select_query(query)
                elif block.get("type") == "tool_result":
                    _walk_tool_references(block.get("content"), found)
    return found


def is_loaded(tool_name: str, loaded: set[str]) -> bool:
    suffix = tool_name[len(TOOL_PREFIX):]
    return tool_name in loaded or suffix in loaded


def _cache_path(session_id: str) -> Path | None:
    safe = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")
    return CACHE_DIR / f"{safe}.json" if safe else None


def _read_cache(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {s for s in data if isinstance(s, str)}
    except (OSError, ValueError, TypeError):
        return set()


def _write_cache(path: Path | None, names: set[str]) -> None:
    if path is None:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(names)), encoding="utf-8")
    except OSError:
        pass


def build_reason(tool_name: str) -> str:
    return (
        f"{tool_name} has not been loaded in this session, so its params would be guessed. "
        f"Load the schema first, in one call for every Conductor tool you will need: "
        f"ToolSearch with query \"select:{tool_name}\" (comma-separate several). Then call it once with the real params.\n"
        "Rules this gate exists for: do not retry a failing tool more than once without re-reading its error; "
        "write_draft is only for text addressed to a person or platform (it needs a recipient), a prompt for "
        "another chat goes inline or through spawn_chat; deliver a piece of text once, as a draft or inline, never both."
    )


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name") or ""
    if not matches_tool(tool_name):
        sys.exit(0)
    if payload.get("agent_id"):
        # A dispatched subagent loads its own schemas in its own transcript,
        # which this payload's transcript_path may not be.
        sys.exit(0)
    # With no readable transcript nothing can be proven loaded, and a denial could never be
    # cleared (no ToolSearch would ever show up), so the gate would lock the tool for good.
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript or not Path(transcript).is_file():
        sys.exit(0)

    cache_file = _cache_path(payload.get("session_id") or "")
    cached = _read_cache(cache_file)
    if is_loaded(tool_name, cached):
        sys.exit(0)

    loaded = loaded_tool_names(payload.get("transcript_path") or "")
    if is_loaded(tool_name, loaded):
        _write_cache(cache_file, cached | loaded)
        sys.exit(0)
    deny(build_reason(tool_name))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[deferred-tool-blind-call-guard] hook error, failing open: {e}\n")
        sys.exit(0)
