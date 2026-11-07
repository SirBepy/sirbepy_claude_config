"""Verifies (and with --apply, re-applies) the local frontmatter tweaks on vendored skills.

skills/VENDORED.overrides.json lists, per vendored SKILL.md, the top-level frontmatter lines that
differ from upstream on purpose (the Cloudflare pack's `disable-model-invocation: true`, asd-ste100's
trimmed description). A vendor update (`npx impeccable update`, a fresh copy of a pack) silently
overwrites them, and nothing else notices: the always-on skill listing just grows back. Run as
`python ci/check_vendored_overrides.py` (exit 1 names every drifted file) and, after a vendor update,
`python ci/check_vendored_overrides.py --apply` to put the lines back.

The JSON shape is {"<repo-relative SKILL.md>": {"<frontmatter key>": "<raw value text>"}}; the value is
the exact text after `key:` on that line (so a quoted description keeps its quotes). A leading
"_comment" key at the top level is ignored.
"""

import argparse
import json
import sys
from pathlib import Path

OVERRIDES_FILE = Path("skills") / "VENDORED.overrides.json"


def split_frontmatter(text: str):
    """Returns (lines, close_index) for the `---` fenced block, or None when absent."""
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r") == "---":
            return lines, i
    return None


def find_key_line(lines: list, close_index: int, key: str):
    prefix = key + ":"
    for i in range(1, close_index):
        if lines[i].startswith(prefix):
            return i
    return None


def key_span_end(lines: list, idx: int, close_index: int) -> int:
    """Index one past the last line that belongs to the key at `idx`.

    A block scalar (`description: >`) or a folded plain scalar keeps its text on following
    indented lines, which must be replaced together with the `key:` line or they are left behind
    as orphaned, invalid YAML. Blank lines count only when an indented line follows them.
    """
    end = idx + 1
    while end < close_index and (lines[end].strip() == "" or lines[end][0] in (" ", "\t")):
        end += 1
    while end > idx + 1 and lines[end - 1].strip() == "":
        end -= 1
    return end


def current_value(lines: list, close_index: int, key: str):
    idx = find_key_line(lines, close_index, key)
    if idx is None:
        return None
    return lines[idx][len(key) + 1:].strip().rstrip("\r")


def drift_for(path: Path, wanted: dict) -> list:
    """One message per key whose frontmatter line is missing or differs."""
    if not path.is_file():
        return [f"{path.as_posix()}: file is missing"]
    # utf-8-sig: PowerShell 5.1 writes a BOM, which would otherwise hide the opening fence.
    parsed = split_frontmatter(path.read_text(encoding="utf-8-sig"))
    if parsed is None:
        return [f"{path.as_posix()}: no frontmatter block"]
    lines, close = parsed
    problems = []
    for key, value in wanted.items():
        have = current_value(lines, close, key)
        if have is None:
            problems.append(f"{path.as_posix()}: frontmatter key '{key}' is missing, override wants: {value}")
        elif have != value.strip():
            problems.append(f"{path.as_posix()}: '{key}' differs from the override (have: {have[:80]}; want: {value[:80]})")
    return problems


def apply_to(path: Path, wanted: dict) -> bool:
    """Rewrites or inserts the wanted lines. Returns True when the file changed."""
    raw = path.read_bytes().decode("utf-8")
    bom = "﻿" if raw.startswith("﻿") else ""
    raw = raw[len(bom):]
    parsed = split_frontmatter(raw)
    if parsed is None:
        raise ValueError(f"{path.as_posix()}: no frontmatter block to patch")
    lines, close = parsed
    changed = False
    for key, value in wanted.items():
        # split("\n") leaves each CRLF line's "\r" in place, so a new line must carry one too.
        suffix = "\r" if lines[0].endswith("\r") else ""
        new_line = f"{key}: {value.strip()}{suffix}"
        idx = find_key_line(lines, close, key)
        if idx is None:
            lines.insert(close, new_line)
            close += 1
            changed = True
        else:
            end = key_span_end(lines, idx, close)
            if lines[idx:end] != [new_line]:
                lines[idx:end] = [new_line]
                close -= end - idx - 1
                changed = True
    if changed:
        path.write_bytes((bom + "\n".join(lines)).encode("utf-8"))
    return changed


def load_overrides(root: Path) -> dict:
    data = json.loads((root / OVERRIDES_FILE).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--apply", action="store_true", help="re-apply every override instead of only checking")
    args = parser.parse_args()
    root = args.root.resolve()

    if not (root / OVERRIDES_FILE).is_file():
        print(f"FAIL: {OVERRIDES_FILE.as_posix()} is missing")
        return 1
    overrides = load_overrides(root)

    if args.apply:
        patched = [rel for rel, wanted in overrides.items() if apply_to(root / rel, wanted)]
        print(f"OK: re-applied overrides in {len(patched)} of {len(overrides)} file(s)")
        for rel in patched:
            print(f"  patched {rel}")
        return 0

    problems = []
    for rel, wanted in overrides.items():
        problems.extend(drift_for(root / rel, wanted))
    for line in problems:
        print(f"FAIL: {line}")
    if problems:
        print("FAIL: vendored overrides drifted - run `python ci/check_vendored_overrides.py --apply`")
        return 1
    print(f"OK: {len(overrides)} vendored override(s) in place")
    return 0


if __name__ == "__main__":
    sys.exit(main())
