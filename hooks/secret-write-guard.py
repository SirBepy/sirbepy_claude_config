"""PreToolUse hook: ask before Write/Edit/MultiEdit/NotebookEdit writes text
that looks like a secret literal (AWS/GitHub/Slack/OpenAI-shaped tokens, a
PEM block, a credentialed connection string, or a generic password/token
assignment). Patterns come from hooks/secret-patterns.txt, the single
source shared with skills/commit/secret-scan.sh, so the two never drift.

`process.env`/`os.environ`/`${...}`-style references are excluded from the
generic-assignment rule only; a literal AKIA... key is still a hit next to
process.env. Always `ask`, never `deny` - todo 420 measured 22 legitimate
.env.local writes and 3 lockfile writes that a hard block would have eaten.
Fails open on any hook error; fails LOUD (exit 2) if the shared pattern
file is missing or unparsable, since a secret guard with silently zero
patterns is the exact silent-pass failure this repo keeps getting bitten by.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, ask
except Exception as e:
    sys.stderr.write(f"[secret-write-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

PATTERNS_PATH = _HOOKS_DIR / "secret-patterns.txt"

ENV_MARKERS = ("process.env", "os.environ", "getenv", "${", "env[", "env(", "$env:", "deno.env")

VALUE_RE = re.compile(r"['\"]([^'\"\t ,)]{6,})['\"]")


def has_env_marker(lowered_line: str) -> bool:
    return any(marker in lowered_line for marker in ENV_MARKERS)


def load_patterns(path: Path):
    """Parse the shared pattern file into (patterns, allows) lists of
    (name, compiled_regex). Any structural problem is FATAL (exit 2), not
    fail-open: a broken pattern file must block hard, matching the
    _hooklib import convention every guard already follows.
    """
    if not path.is_file():
        sys.stderr.write(f"[secret-write-guard] FATAL: pattern file missing: {path}\n")
        sys.exit(2)

    patterns, allows = [], []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) != 3:
            sys.stderr.write(f"[secret-write-guard] FATAL: {path}:{lineno} expected 3 tab-separated fields, got {len(parts)}\n")
            sys.exit(2)
        kind, name, ere = parts
        try:
            compiled = re.compile(ere)
        except re.error as e:
            sys.stderr.write(f"[secret-write-guard] FATAL: {path}:{lineno} bad regex for {name!r}: {e}\n")
            sys.exit(2)
        if kind == "pattern":
            patterns.append((name, compiled))
        elif kind == "allow":
            allows.append((name, compiled))
        else:
            sys.stderr.write(f"[secret-write-guard] FATAL: {path}:{lineno} unknown kind {kind!r}\n")
            sys.exit(2)

    if not patterns:
        sys.stderr.write(f"[secret-write-guard] FATAL: {path} has zero pattern rows\n")
        sys.exit(2)
    return patterns, allows


def gather_texts(tool_input: dict) -> list:
    texts = []
    if isinstance(tool_input.get("content"), str):
        texts.append(tool_input["content"])
    if isinstance(tool_input.get("new_string"), str):
        texts.append(tool_input["new_string"])
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
            texts.append(edit["new_string"])
    if isinstance(tool_input.get("new_source"), str):
        texts.append(tool_input["new_source"])
    return texts


def scan_text(text: str, patterns, allows) -> list:
    """Return the distinct pattern names tripped anywhere in text, checked
    line by line so an env-marker or placeholder elsewhere in a large file
    can't mask a real hit on a different line.
    """
    names = []
    for raw_line in text.split("\n"):
        lo = raw_line.lower()
        for name, rx in patterns:
            m = rx.search(lo)
            if not m:
                continue
            if name == "generic_assignment":
                if has_env_marker(lo):
                    continue
                seg = lo[m.start():m.end()]
                vm = VALUE_RE.search(seg)
                if vm:
                    val = vm.group(1)
                    # "$VAR"/'$VAR' - bash-style dereference, not a literal.
                    if val.startswith("$") or any(a.search(val) for _, a in allows):
                        continue
            if name not in names:
                names.append(name)
    return names


def main() -> None:
    payload = read_payload()
    tool_input = payload.get("tool_input") or {}
    texts = gather_texts(tool_input)
    if not texts:
        sys.exit(0)

    patterns, allows = load_patterns(PATTERNS_PATH)

    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or "(unknown path)"
    hit_names = []
    for text in texts:
        for name in scan_text(text, patterns, allows):
            if name not in hit_names:
                hit_names.append(name)

    if hit_names:
        ask(
            f"[secret-write-guard] {file_path} looks like it contains a secret "
            f"matching: {', '.join(hit_names)}. If this is a false positive "
            "(a placeholder, a test fixture, an interpolated template), "
            "approve the write; otherwise remove the literal value and "
            "source it from an env var or secret store instead."
        )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[secret-write-guard] hook error, failing open: {e}\n")
        sys.exit(0)
