"""PreToolUse hook: block piping `cargo test` output into tail/head/grep/Select-Object.

Two incidents, same shape, roughly a week apart:

- 2026-08-19 (`claude_usage_in_taskbar` todo 692): `cargo test --test
  daemon_user_todos_e2e ... 2>&1 | tail -40` produced 0 bytes for 2h17m.
- 2026-08-25 (a `/mega-todos` verify barrier): `cargo test --manifest-path
  src-tauri/Cargo.toml --lib 2>&1 | tail -25` hung ~23 minutes, and killing it
  invalidated the build cache, so the retry rebuilt the whole dep tree.

Root cause in both: a test spawns a child process that inherits the pipe's
write end, so the filter command never sees EOF even after cargo itself is
done. `cargo build`/`cargo check`/`cargo clippy` don't spawn that kind of
child and are left alone (todo 780 step 2) - piping those is fine and common.

Two patterns must stay allowed or this guard gets switched off:
- reading an ALREADY-FINISHED output file (`tail -20 <path>`) is the fix this
  guard steers people toward, so a bare tail/head/grep with no `cargo test`
  feeding it through a pipe is never touched.
- `grep --line-buffered` flushes per line, so it never has the swallowing
  problem and is carved out even when it follows `cargo test`.

Detection is regex-based on the raw command string, split on top-level
`&&`/`||`/`;`/newline into statements, then each statement on `|` into
pipeline segments in order - only a filter segment that comes AFTER a
`cargo test` segment in the same pipeline counts. Fails open on error.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny as _lib_deny
except Exception as e:
    sys.stderr.write(f"[cargo-test-pipe-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

# cargo subcommands that spawn a child inheriting the pipe. Todo 877 (a sibling
# todo, not this one) wants "build"/"check"/"clippy" appended here - keeping
# this a list, not an inline regex literal, makes that a one-line append later
# instead of a rewrite. This todo's own step 2 says stay at "test" only.
CARGO_SUBCOMMANDS = ("test",)

# Commands that block waiting for EOF on a still-open pipe, kept as its own
# named list for the same reason as CARGO_SUBCOMMANDS above.
PIPE_FILTERS = ("tail", "head", "grep", "Select-Object")

CARGO_SUBCOMMAND_RE = re.compile(
    r"\bcargo(?:\.exe)?\b(?:\s+\+\S+)?\s+(?:" + "|".join(CARGO_SUBCOMMANDS) + r")\b",
    re.IGNORECASE,
)
PIPE_FILTER_RE = re.compile(r"\b(" + "|".join(PIPE_FILTERS) + r")\b", re.IGNORECASE)

LINE_BUFFERED_RE = re.compile(r"--line-buffered\b", re.IGNORECASE)

# Splits top-level statements; "||" is matched before a lone "|" would be, so
# a pipeline's own "|" segments never get cut here.
STATEMENT_SPLIT_RE = re.compile(r"&&|\|\||;|\n")


def deny(filter_name: str) -> None:
    _lib_deny(
        f"[cargo-test-pipe-guard] Blocked: piping `cargo test` output through `{filter_name}` "
        "can hang forever - a spawned test child inherits the pipe's write end, so the filter "
        "never sees EOF even after cargo itself finishes (2026-08-19: 2h17m silent hang; "
        "2026-08-25: ~23min hang that also invalidated the build cache on retry).",
        suffix=(
            " Run cargo test bare with run_in_background: true, then once it finishes run "
            '`grep -E "^test result" <output-file>` against the finished file. Reading an '
            "already-finished output file this way is fine; `grep --line-buffered` is also fine "
            "since it flushes per line instead of swallowing output."
        ),
    )


def find_violation(command: str, cwd: str | None = None) -> str | None:
    # `cwd` is accepted but unused: this guard is deliberately global (todo 780
    # step 4's own lean), kept as a parameter so a future repo-scoped check
    # only needs to read it here, not re-plumb the call site.
    for statement in STATEMENT_SPLIT_RE.split(command):
        segments = statement.split("|")
        cargo_idx = None
        for i, seg in enumerate(segments):
            if cargo_idx is None and CARGO_SUBCOMMAND_RE.search(seg):
                cargo_idx = i
                continue
            if cargo_idx is None:
                continue
            m = PIPE_FILTER_RE.search(seg)
            if not m:
                continue
            filter_name = m.group(1)
            if filter_name.lower() == "grep" and LINE_BUFFERED_RE.search(seg):
                continue
            return filter_name
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    filter_name = find_violation(command, payload.get("cwd"))
    if filter_name:
        deny(filter_name)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[cargo-test-pipe-guard] hook error, failing open: {e}\n")
        sys.exit(0)
