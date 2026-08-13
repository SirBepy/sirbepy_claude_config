"""SPIKE, not installed. Not wired into settings.json. Do not enable.

Prototype for todo 311 (no-command-chaining-hook). Reads a Bash/PowerShell
PreToolUse-shaped payload from stdin, masks quoted/here-string regions the
same way shell-content-write-guard.py does, then flags top-level `&&`, `;`,
`||` in command position (never `|` alone - a pipe feeds a filter, it is
not a command chain). Never blocks, exit code is always 0. Measurement
tool, not a working guard.

Measured 2026-08-13 against 30047 unique real Bash/PowerShell commands
pulled from this machine's own session transcripts (1331 most-recent
.jsonl files under ~/.claude/projects, across ~50 projects). Raw flag
rate: 16525/30047 (55.0%). A manual classification of 60 randomly sampled
flagged commands against the rule's actual protective intent (independent
side-effecting steps chained so a mid-chain failure is invisible) found
roughly 80% false positives - overwhelmingly the `cd X && <command>` /
`cd X; <command>` directory-scoping idiom (the only way to scope a command
to a repo when cwd does not persist across tool calls), PowerShell
variable-sharing one-liners state cannot survive a second call, and bash
for-loop / hashtable-literal `;` that is compound-statement syntax, not
chaining. NOT WIRED - see the todo 311 report for the full breakdown and
the count-independent reason this rule was already retired from CLAUDE.md.

Reuses shell-content-write-guard's masking helpers directly (import, not
copy) rather than reimplementing quote/here-string handling a second time.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _hooklib import read_payload
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "shell_content_write_guard", _HOOKS_DIR / "shell-content-write-guard.py"
)
_scwg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scwg)

# Top-level `&&`, `;`, `||` in command position. `|` alone is never flagged:
# a filter pipeline is one logical command, not a chain of independent ones.
CHAIN_OP_RE = re.compile(r"&&|\|\||;")


def find_chain_ops(command: str) -> list[str]:
    """Union of both dialects' masked scans (fail closed), matching
    shell-content-write-guard's own bash-vs-pwsh masking approach.
    """
    masked_bash = _scwg.mask_quoted(command, _scwg.DQUOTE_RE_BASH)
    masked_pwsh = _scwg.mask_quoted(command, _scwg.DQUOTE_RE_PWSH)
    hits = [m.group(0) for m in CHAIN_OP_RE.finditer(masked_bash)]
    hits += [m.group(0) for m in CHAIN_OP_RE.finditer(masked_pwsh)]
    return hits


def main() -> int:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    hits = find_chain_ops(command) if command.strip() else []
    if hits:
        print(f"FLAG ops={hits} command={command!r}")
    else:
        print("CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
