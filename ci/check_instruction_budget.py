"""Hard ceiling on the always-loaded instruction weight of this repo.

Gates CLAUDE.md alone against CEILING_TOKENS. The four snippets/refs files
CLAUDE.md tells sessions to read once per session are measured and printed
for visibility but never compared against a threshold: gating them would
fail the build on an edit to e.g. snippets/auto-commit.md, which is not
what this ceiling is for.
"""

import argparse
import sys
from pathlib import Path

# This is a RATCHET, not a target: lower it whenever CLAUDE.md shrinks, never
# raise it without the dev's explicit say-so. Raised from 6558 on the dev's
# explicit say-so, 2026-09-04, because headroom had reached 1 token and was
# blocking queued rules; todo 921 is the paired commitment to cut it back down.
CEILING_TOKENS = 7000

GATED_FILE = "CLAUDE.md"

# Files CLAUDE.md orders read once per session; reported, never gated (see module docstring).
INFO_FILES = (
    "snippets/terse-replies.md",
    "snippets/auto-commit.md",
    "refs/copy-paste-format.md",
    "refs/memory-rubric.md",
)


def char_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8"))


def to_tokens(chars: int) -> int:
    return -(-chars // 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--root", type=Path, default=default_root)
    args = parser.parse_args()
    root = args.root

    claude_md = root / GATED_FILE
    if not claude_md.is_file():
        print(f"MISSING: {claude_md} (gated file, cannot measure)")
        return 1

    gated_chars = char_count(claude_md)
    gated_tokens = to_tokens(gated_chars)

    missing_info = []
    total_chars = gated_chars
    for rel in INFO_FILES:
        info_path = root / rel
        if not info_path.is_file():
            missing_info.append(str(info_path))
            continue
        total_chars += char_count(info_path)

    if missing_info:
        for path_str in missing_info:
            print(f"MISSING: {path_str} (informational file, cannot measure)")
        return 1

    # Chars summed across all 5 files before one ceil (matches the 10,981 baseline;
    # summing per-file ceil'd tokens lands one higher). Reported only, never gated.
    grand_total_tokens = to_tokens(total_chars)
    print(f"informational (not gated): {grand_total_tokens} tokens across CLAUDE.md + {len(INFO_FILES)} once-per-session files")

    if gated_tokens > CEILING_TOKENS:
        overage = gated_tokens - CEILING_TOKENS
        print(f"FAIL: {GATED_FILE} is {gated_tokens} tokens, ceiling is {CEILING_TOKENS}, over by {overage}")
        print(f"      fix: cut {overage} tokens ({overage * 4} chars) from {GATED_FILE}, or raise")
        print("      CEILING_TOKENS in this file with the dev's explicit say-so, never silently")
        return 1

    headroom = CEILING_TOKENS - gated_tokens
    print(f"PASS: {GATED_FILE} is {gated_tokens} tokens, ceiling is {CEILING_TOKENS}, headroom {headroom}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
