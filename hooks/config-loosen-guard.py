"""PreToolUse hook: ask before Write/Edit/MultiEdit weakens a lint/typecheck
config (todo 440) - loosening the check instead of fixing the code it flags.

Matches a curated file set (tsconfig*.json, .eslintrc*/eslint.config.*,
biome.json(c), analysis_options.yaml, pyproject.toml, Cargo.toml,
pubspec.yaml, vitest/jest config) and, where a signal exists, tries to tell
an actual WEAKENING edit apart from an ordinary one (a dependency add, a new
script, an unrelated key) so this never fires on the common case.

Two generic, format-agnostic detectors, both line-diff based (real diff via
difflib, not a naive line-set compare, so a line that just moved position
isn't mistaken for a change):

1. Boolean strictness flip/removal - a curated KNOWN_STRICT_KEYS vocabulary
   (tsconfig's strict family, Dart's strict-casts/-inference/-raw-types,
   mypy's disallow_*/warn_* family). Fires when a `key: true` line for a
   known key disappears from the diff and no `key: true` (or stronger)
   replacement shows up - covers both an explicit flip to false and a bare
   deletion, since either removes the enforcement.
2. Severity downgrade/removal - restricted per file kind to that kind's own
   severity vocabulary (eslint: off/warn/error/0/1/2, biome: off/warn/error,
   Cargo lints: allow/warn/deny/forbid) so it can key off ANY rule name
   without a curated list, while staying narrow enough that an unrelated
   value (a Cargo profile's `opt-level = 2`, say) can't collide - digit
   severities are eslint-only, and Cargo/biome never match bare digits.

What this catches: an explicit `"strict": true` -> `false` edit, or that
line simply vanishing; a lint rule's severity dropping from error to
warn/off, or the rule's line disappearing outright; the Cargo-lints
equivalent (deny/forbid -> warn/allow, or vanishing).

What this misses (documented, not silently assumed covered): list-shaped
loosening (a growing `ignore`/`exclude`/`ignorePatterns` array, ruff's
`select`/`ignore` lists), numeric threshold decreases in vitest/jest
coverage config, and anything in pubspec.yaml - none of pubspec's real
content (dependency versions, SDK constraints) fits either vocabulary, so
it is matched for future extension but never actually asks today. A
brand-new file (nothing to diff against) never asks, since there is no
prior state to weaken.

Always `ask`, never `deny` - see the message text for why and for the
literal escape route, since in a headless run `ask` is enforced as deny.
Fails open on any hook error.
"""

import difflib
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, ask
except Exception as e:
    sys.stderr.write(f"[config-loosen-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

# (kind, basename regex). First match wins. Kind drives which detector (if
# any) runs in KIND_DETECTORS below.
FILE_PATTERNS = [
    ("tsconfig", re.compile(r"^tsconfig(\..+)?\.json$", re.IGNORECASE)),
    ("eslintrc", re.compile(r"^\.eslintrc(\..+)?$", re.IGNORECASE)),
    ("eslintrc", re.compile(r"^eslint\.config\.(js|mjs|cjs|ts|mts|cts)$", re.IGNORECASE)),
    ("biome", re.compile(r"^biome\.jsonc?$", re.IGNORECASE)),
    ("analysis_options", re.compile(r"^analysis_options\.ya?ml$", re.IGNORECASE)),
    ("pyproject", re.compile(r"^pyproject\.toml$", re.IGNORECASE)),
    ("cargo", re.compile(r"^Cargo\.toml$", re.IGNORECASE)),
    ("pubspec", re.compile(r"^pubspec\.yaml$", re.IGNORECASE)),
    ("vitest", re.compile(r"^vitest\.config\.(js|mjs|cjs|ts|mts|cts)$", re.IGNORECASE)),
    ("jest", re.compile(r"^jest\.config\.(js|mjs|cjs|ts|json)$", re.IGNORECASE)),
]

# Normalized (alnum-only, lowercased) key names where `true` is the STRICTER
# value and `false`/absent is looser - every entry here must have that
# polarity, which is why skipLibCheck/implicit-casts/implicit-dynamic are
# deliberately excluded (their `true` is the LOOSER setting; including them
# would flag a tightening edit as a loosening one).
KNOWN_STRICT_KEYS = {
    # tsconfig
    "strict", "strictnullchecks", "strictfunctiontypes", "strictbindcallapply",
    "strictpropertyinitialization", "noimplicitany", "noimplicitthis", "alwaysstrict",
    "noimplicitreturns", "nofallthroughcasesinswitch", "nounusedlocals", "nounusedparameters",
    "noimplicitoverride", "exactoptionalpropertytypes", "usedefineforclassfields",
    "nouncheckedindexedaccess", "forceconsistentcasinginfilenames", "checkjs",
    # analysis_options.yaml (Dart)
    "strictcasts", "strictinference", "strictrawtypes",
    # pyproject.toml [tool.mypy]
    "disallowuntypeddefs", "disallowincompletedefs", "disallowuntypedcalls",
    "disallowuntypeddecorators", "disallowanygenerics", "disallowsubclassingany",
    "checkuntypeddefs", "warnreturnany", "warnunusedignores", "warnredundantcasts",
    "warnunreachable", "noimplicitoptional", "strictequality", "disallowuntypedglobals",
}

# Severity vocabularies are file-kind-scoped on purpose: bare digits 0/1/2
# are eslint-idiomatic only, so keeping them out of the biome/cargo vocabs
# stops an unrelated numeric value (a Cargo profile's opt-level, a biome
# indent width) from being misread as a severity.
SEV_VOCAB_ESLINT = {"off": 0, "warn": 1, "warning": 1, "error": 2, "0": 0, "1": 1, "2": 2}
SEV_VOCAB_BIOME = {"off": 0, "warn": 1, "error": 2}
SEV_VOCAB_CARGO = {"allow": 0, "warn": 1, "deny": 2, "forbid": 3}

BOOL_LINE_RE = re.compile(r"""["']?(?P<key>[A-Za-z][A-Za-z0-9_\-]*)["']?\s*[:=]\s*(?P<val>true|false)\b""", re.IGNORECASE)
SEV_LINE_RE = re.compile(r"""["']?(?P<key>[\w@/.\-]+)["']?\s*[:=]\s*\[?\s*["']?(?P<val>[A-Za-z0-9_\-]+)["']?""")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")


def _normalize_key(key: str) -> str:
    return _NON_ALNUM_RE.sub("", key.lower())


def bool_signals(lines: list) -> dict:
    """Map known-strictness-key -> highest rank seen (true=1, false=0)."""
    out = {}
    for line in lines:
        for m in BOOL_LINE_RE.finditer(line):
            key = _normalize_key(m.group("key"))
            if key not in KNOWN_STRICT_KEYS:
                continue
            rank = 1 if m.group("val").lower() == "true" else 0
            out[key] = max(out.get(key, -1), rank)
    return out


def sev_signals(lines: list, vocab: dict) -> dict:
    """Map rule/lint key (lowercased, not normalized - names are meaningful
    verbatim, e.g. 'no-console' vs 'noconsole' are different rules) ->
    highest severity rank seen, restricted to `vocab`'s own value words.
    """
    out = {}
    for line in lines:
        for m in SEV_LINE_RE.finditer(line):
            val = m.group("val").lower()
            if val not in vocab:
                continue
            key = m.group("key").lower()
            out[key] = max(out.get(key, -1), vocab[val])
    return out


KIND_DETECTORS = {
    "tsconfig": lambda lines: bool_signals(lines),
    "analysis_options": lambda lines: bool_signals(lines),
    "pyproject": lambda lines: bool_signals(lines),
    "eslintrc": lambda lines: sev_signals(lines, SEV_VOCAB_ESLINT),
    "biome": lambda lines: sev_signals(lines, SEV_VOCAB_BIOME),
    "cargo": lambda lines: sev_signals(lines, SEV_VOCAB_CARGO),
    # No signal exists for these file kinds today - see module docstring.
    "pubspec": None,
    "vitest": None,
    "jest": None,
}


def classify_file(basename: str) -> str | None:
    for kind, pattern in FILE_PATTERNS:
        if pattern.match(basename):
            return kind
    return None


def diff_removed_added(old_lines: list, new_lines: list) -> tuple:
    """Real diff (difflib), not a set difference - a line that only moved
    position must not read as removed-then-added.
    """
    removed, added = [], []
    for line in difflib.unified_diff(old_lines, new_lines, n=0, lineterm=""):
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    return removed, added


def read_disk_lines(file_path: str):
    """Lines currently on disk, or None if unreadable/new - a brand-new
    file has nothing prior to weaken, so callers must skip detection on
    None rather than treating it as "everything was removed".
    """
    if not file_path:
        return None
    try:
        return Path(file_path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None


def gather_diff_pairs(tool_input: dict) -> list:
    """(old_lines, new_lines) pairs from whichever shape the payload has -
    Edit's old_string/new_string, MultiEdit's edits list, or Write's content
    diffed against disk. MultiEdit's edits are compared independently
    against each other (not chained through an intermediate applied state),
    matching how the existing secret-write-guard treats multi-edit texts.
    """
    pairs = []
    if isinstance(tool_input.get("old_string"), str) and isinstance(tool_input.get("new_string"), str):
        pairs.append((tool_input["old_string"].splitlines(), tool_input["new_string"].splitlines()))
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("old_string"), str) and isinstance(edit.get("new_string"), str):
            pairs.append((edit["old_string"].splitlines(), edit["new_string"].splitlines()))
    if isinstance(tool_input.get("content"), str):
        old_lines = read_disk_lines(tool_input.get("file_path") or "")
        if old_lines is not None:
            pairs.append((old_lines, tool_input["content"].splitlines()))
    return pairs


def detect_loosening(kind: str, tool_input: dict) -> list:
    """Descriptions of every key whose rank dropped (or vanished) across any
    diff pair, or [] if this kind has no detector or nothing weakened.
    """
    detector = KIND_DETECTORS.get(kind)
    if detector is None:
        return []
    findings = []
    for old_lines, new_lines in gather_diff_pairs(tool_input):
        removed, added = diff_removed_added(old_lines, new_lines)
        removed_sig = detector(removed)
        if not removed_sig:
            continue
        added_sig = detector(added)
        for key, old_rank in removed_sig.items():
            new_rank = added_sig.get(key, -1)
            if new_rank < old_rank:
                where = "removed" if key not in added_sig else f"weakened to rank {new_rank}"
                findings.append(f"{key} ({where}, was rank {old_rank})")
    return findings


def main() -> None:
    payload = read_payload()
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        sys.exit(0)

    base = file_path.replace("\\", "/").rsplit("/", 1)[-1]
    kind = classify_file(base)
    if kind is None:
        sys.exit(0)

    findings = detect_loosening(kind, tool_input)
    if findings:
        ask(
            f"[config-loosen-guard] {file_path} appears to WEAKEN a strictness/lint check: "
            + "; ".join(findings)
            + ". Is this fixing the config, or avoiding a failing check? If a check is "
            "currently failing, fix the code instead of loosening the config. If this "
            "loosening is genuinely intended (a documented false positive, a deliberate "
            "policy change), approve this prompt to proceed. Escape route for a headless/"
            "unattended run, where this ask is enforced as a deny: make this specific edit "
            "in an interactive session where the prompt can be answered, or land it as its "
            "own explicit, human-reviewed commit instead of inside this run."
        )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[config-loosen-guard] hook error, failing open: {e}\n")
        sys.exit(0)
