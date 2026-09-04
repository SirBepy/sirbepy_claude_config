"""Mechanical validator for the YAML frontmatter of every skills/**/SKILL.md.

An unquoted ": " or " #" inside a name/description value makes YAML read it
as a nested mapping or truncate at a comment - the skill then silently drops
out of installation with no error (observed in citypaul/.dotfiles). No third
party YAML lib is used: frontmatter is hand-parsed line by line so this runs
identically on stock Python, Windows or Linux, with no install step.
"""

import argparse
import re
import sys
from pathlib import Path

# Census of every top-level key across all 83 SKILL.md files, taken 2026-08-20.
# Counts: name(83) description(83) disable-model-invocation(50) argument-hint(38)
# references(2) license(1) allowed-tools(1) version(1) user-invocable(1).
# context/agent/background are not from that census: they were read out of the
# claude binary's own frontmatter schema on 2026-08-20 (todo 418).
ALLOWED_KEYS = {
    "name",
    "description",
    "disable-model-invocation",
    "argument-hint",
    "references",
    "license",
    "allowed-tools",
    "version",
    "user-invocable",
    "context",
    "agent",
    "background",
}

REQUIRED_KEYS = ("name", "description")

TOP_LEVEL_KEY = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$")

# Matches body prose like "Requires the `respawn` MCP tool" (skills/respawn/SKILL.md:17).
REQUIRED_MCP_TOOL = re.compile(r"[Rr]equires the `([A-Za-z0-9_.-]+)` MCP tool")


def is_quoted(value: str) -> bool:
    v = value.strip()
    if len(v) < 2:
        return False
    return (v[0] == v[-1]) and v[0] in ("'", '"')


def hazard_in(value: str):
    """Return (label, offending substring) for the first quoting hazard, or None.

    Only checked on values NOT already wrapped in matching quotes - a quoted
    value is safe regardless of what it contains.
    """
    for label, needle in (("colon-space ': '", ": "), ("space-hash ' #'", " #")):
        idx = value.find(needle)
        if idx != -1:
            start = max(0, idx - 12)
            end = min(len(value), idx + len(needle) + 12)
            return label, value[start:end]
    return None


def parse_frontmatter_keys(lines: list[str]):
    """Yield (key, raw_value, line_number) for each top-level `key: value`
    line inside the frontmatter body. Any indented line is a continuation
    (block scalar body, block sequence item, folded text) and is skipped
    outright rather than mis-parsed as a new key.
    """
    for i, line in enumerate(lines, start=1):
        if line != line.lstrip():
            continue
        m = TOP_LEVEL_KEY.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        yield key, value, i


def check_skill(root: Path, path: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    problems = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0] != "---":
        found = lines[0] if lines else "(empty file)"
        problems.append(f"{rel}:1: frontmatter must start with a line that is exactly '---', found {found!r}")
        return problems

    close_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            close_idx = i
            break
    if close_idx is None:
        problems.append(f"{rel}:1: no closing '---' frontmatter delimiter found")
        return problems

    body = lines[1:close_idx]
    seen = {}
    for key, value, lineno in parse_frontmatter_keys(body):
        seen[key] = (value, lineno)

        if key not in ALLOWED_KEYS:
            problems.append(f"{rel}:{lineno}: unknown frontmatter key '{key}' (not in the allowlist)")
            continue

        if value and not is_quoted(value):
            hazard = hazard_in(value)
            if hazard:
                label, snippet = hazard
                problems.append(
                    f"{rel}:{lineno}: unquoted value for '{key}' contains {label} near {snippet!r}; wrap the value in quotes"
                )

    for key in REQUIRED_KEYS:
        if key not in seen:
            problems.append(f"{rel}:1: missing required frontmatter key '{key}'")
        elif not seen[key][0]:
            problems.append(f"{rel}:{seen[key][1]}: frontmatter key '{key}' has an empty value")

    if "name" in seen and seen["name"][0]:
        nameval = seen["name"][0].strip('"\'')
        dirname = path.parent.name
        if nameval != dirname:
            problems.append(
                f"{rel}:{seen['name'][1]}: name '{nameval}' does not match containing directory '{dirname}'"
            )

    return problems


def find_required_mcp_tools(root: Path, path: Path) -> list[str]:
    """Return one info line per "Requires the `X` MCP tool" sentence in a
    skill's body.

    Informational only, never a FAIL: MCP tools attach at session start (todo
    497), so whether one is actually registered is a per-session runtime fact
    this offline script has no way to observe - it only surfaces the
    declaration for a human to cross-check.
    """
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    close_idx = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            close_idx = i
            break
    body_start = close_idx + 1 if close_idx is not None else 0

    info = []
    for i, line in enumerate(lines[body_start:], start=body_start + 1):
        m = REQUIRED_MCP_TOOL.search(line)
        if m:
            info.append(f"{rel}:{i}: declares required MCP tool '{m.group(1)}' (registration unverifiable offline)")
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--root", type=Path, default=default_root)
    args = parser.parse_args()
    root = args.root

    files = sorted(root.glob("skills/**/SKILL.md"), key=lambda p: p.relative_to(root).as_posix())

    if not files:
        print(f"FAIL: no skills/**/SKILL.md files found under {root}")
        return 1

    all_problems = []
    skills_with_problems = 0
    all_info = []
    for path in files:
        problems = check_skill(root, path)
        if problems:
            skills_with_problems += 1
            all_problems.extend(problems)
        all_info.extend(find_required_mcp_tools(root, path))

    for problem in all_problems:
        print(problem)

    for info in all_info:
        print(f"INFO: {info}")

    if all_problems:
        print(f"FAIL: {len(all_problems)} problem(s) across {skills_with_problems} skill(s)")
        return 1

    print(f"OK: {len(files)} skills checked, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
