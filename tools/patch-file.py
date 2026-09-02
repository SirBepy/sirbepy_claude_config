"""CRLF-safe exact-string file patcher.

Preserves a file's existing line-ending style (CRLF, LF, or old-Mac CR) and
its UTF-8 BOM if present. Refuses a file with mixed line endings rather than
silently normalising it, and refuses any replacement whose `old` string does
not match the target file exactly once - a wrong-match edit fails loud
instead of applying somewhere unintended.

Usage:
    python patch-file.py <path> --replace <old-file> <new-file> [--replace <old-file> <new-file> ...]
    python patch-file.py --stdin-json
        # JSON on stdin: {"path": "...", "replacements": [{"old": "...", "new": "..."}, ...]}

--replace pairs are files (not argv) so multi-line and quote-heavy content
survives shell quoting. Pairs apply in order; a later pair sees the result
of earlier pairs. `old`/`new` content is matched line-ending-agnostically
(CRLF and LF in the snippet both match), and the file's original ending is
restored on write.
"""

import argparse
import json
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"


class PatchError(Exception):
    """Raised for any condition that must abort without writing the file."""


def detect_line_ending(text: str) -> str | None:
    """Return the file's single line-ending style, or None if it has none.

    Raises PatchError on a genuine mix (e.g. CRLF and bare LF both present) -
    that is the case a caller must resolve by hand, not have guessed for them.
    """
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    cr_only = text.count("\r") - crlf
    if (crlf and (lf_only or cr_only)) or (lf_only and cr_only):
        raise PatchError("file has mixed line endings; refusing to guess and silently normalise")
    if crlf:
        return "\r\n"
    if lf_only:
        return "\n"
    if cr_only:
        return "\r"
    return None


def normalize_to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def apply_replacements(norm_text: str, replacements: list[tuple[str, str, str]]) -> str:
    """replacements: (label, old, new) triples, old/new already LF-normalised."""
    for label, old, new in replacements:
        if not old:
            raise PatchError(f"{label}: empty 'old' string is not allowed")
        count = norm_text.count(old)
        if count == 0:
            raise PatchError(f"{label}: old string not found (0 matches)")
        if count > 1:
            raise PatchError(f"{label}: old string matches {count} times, must be exactly 1")
        norm_text = norm_text.replace(old, new, 1)
    return norm_text


def load_cli_replacements(pairs: list[list[str]]) -> list[tuple[str, str, str]]:
    out = []
    for old_file, new_file in pairs:
        old = normalize_to_lf(Path(old_file).read_text(encoding="utf-8"))
        new = normalize_to_lf(Path(new_file).read_text(encoding="utf-8"))
        out.append((old_file, old, new))
    return out


def load_json_payload(raw: str) -> tuple[str, list[tuple[str, str, str]]]:
    payload = json.loads(raw)
    target = payload["path"]
    out = []
    for i, item in enumerate(payload["replacements"]):
        old = normalize_to_lf(item["old"])
        new = normalize_to_lf(item["new"])
        out.append((f"replacements[{i}]", old, new))
    return target, out


def patch_file(path: Path, replacements: list[tuple[str, str, str]]) -> None:
    raw = path.read_bytes()
    has_bom = raw.startswith(BOM)
    text = raw[len(BOM):].decode("utf-8") if has_bom else raw.decode("utf-8")

    ending = detect_line_ending(text)
    norm_result = apply_replacements(normalize_to_lf(text), replacements)

    if ending in ("\r\n", "\r"):
        result = norm_result.replace("\n", ending)
    else:
        result = norm_result

    path.write_bytes((BOM if has_bom else b"") + result.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", help="file to patch")
    parser.add_argument("--replace", nargs=2, action="append", metavar=("OLD_FILE", "NEW_FILE"),
                         help="a pair of files holding the exact old/new content; repeatable")
    parser.add_argument("--stdin-json", action="store_true",
                         help="read {path, replacements:[{old,new}]} JSON from stdin instead")
    args = parser.parse_args()

    try:
        if args.stdin_json:
            if args.path or args.replace:
                raise PatchError("--stdin-json cannot be combined with a path or --replace")
            target, replacements = load_json_payload(sys.stdin.read())
        else:
            if not args.path or not args.replace:
                raise PatchError("need <path> and at least one --replace OLD_FILE NEW_FILE, or --stdin-json")
            target = args.path
            replacements = load_cli_replacements(args.replace)

        patch_file(Path(target), replacements)
    except PatchError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(f"OK: patched {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
