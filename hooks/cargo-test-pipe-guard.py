"""PreToolUse hook: block piping cargo test/build/check/clippy output into
tail/head/grep/Select-Object, and piping commit-pathspec.sh output into the
same filters without pipefail.

The second case is a different mechanism with the same fix (run unpiped):
the filter's exit status replaces the script's, so a refused commit reads as
success (2026-10-22, skills/commit/SKILL.md step 8). `set -o pipefail` (or
`bash -o pipefail`) anywhere in the command lifts it. The script name only
counts when it is run, not named: the segment before it may hold just a shell
launcher and a path prefix, so `cat .../commit-pathspec.sh | head` and a name
inside a quoted -m message pass. A filter after a quoted `|` is not a pipe.

Cargo incidents, three, same shape:

- 2026-08-19 (`claude_usage_in_taskbar` todo 692): `cargo test --test
  daemon_user_todos_e2e ... 2>&1 | tail -40` produced 0 bytes for 2h17m. A
  spawned test child inherits the pipe's write end, so the filter never sees
  EOF even after cargo itself is done.
- 2026-08-25 (a `/mega-todos` verify barrier): `cargo test --manifest-path
  src-tauri/Cargo.toml --lib 2>&1 | tail -25` hung ~23 minutes, and killing it
  invalidated the build cache, so the retry rebuilt the whole dep tree.
- 2026-09-02 (`claude_usage_in_taskbar`, todo 877): `cargo build
  --manifest-path src-tauri/Cargo.toml 2>&1 | tail -5` gave zero output for
  ~30 minutes. `build`/`check`/`clippy` don't spawn a child that blocks EOF,
  but the filter still buffers everything until cargo exits, so a live build
  and a hung one look identical the whole time - the same "never buffer
  streaming output" break, different mechanism.

Two patterns must stay allowed or this guard gets switched off:
- reading an ALREADY-FINISHED output file (`tail -20 <path>`) is the fix this
  guard steers people toward, so a bare tail/head/grep with no cargo command
  feeding it through a pipe is never touched.
- `grep --line-buffered` flushes per line, so it never has the swallowing
  problem and is carved out even when it follows a matched cargo command.

Detection is regex-based on the raw command string, split on top-level
`&&`/`||`/`;`/newline into statements, then each statement on `|` into
pipeline segments in order - only a filter segment that comes AFTER a
matched cargo segment in the same pipeline counts. Fails open on error.

A `cargo test` match only counts when it sits in command position (start
of statement, or right after `|`/`;`/`&`/`(`/`{`/newline, mod whitespace) -
2026-09-02, the guard's own JSON-payload probe command quoted a piped
`cargo test | tail` inside a string literal and got blocked by its own
naive `|` split, same day 780 shipped (todo 881). No quote masking needed:
text living inside a JSON/shell string is never preceded by a delimiter.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny as _lib_deny, is_command_position
except Exception as e:
    sys.stderr.write(f"[cargo-test-pipe-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

try:
    # todo 934: reuse destructive-command-guard's own wrapper list (env/nohup/
    # nice/time/command/xargs/sh -c) rather than a second copy. Import only -
    # _destructive_guard_shared.py is owned by another lane right now.
    from _destructive_guard_shared import LEADING_WRAPPER_RE
except Exception as e:
    sys.stderr.write(f"[cargo-test-pipe-guard] FATAL: cannot import _destructive_guard_shared ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

# cargo subcommands long/hang-prone enough that a buffering filter hides a
# hung run from a live one (todo 877). Kept as a list, not an inline regex
# literal, so appending another subcommand later is a one-line change.
CARGO_SUBCOMMANDS = ("test", "build", "check", "clippy")

# Commands that block waiting for EOF on a still-open pipe, kept as its own
# named list for the same reason as CARGO_SUBCOMMANDS above.
PIPE_FILTERS = ("tail", "head", "grep", "Select-Object")

CARGO_SUBCOMMAND_RE = re.compile(
    r"\bcargo(?:\.exe)?\b(?:\s+\+\S+)?\s+(?P<subcmd>" + "|".join(CARGO_SUBCOMMANDS) + r")\b",
    re.IGNORECASE,
)
PIPE_FILTER_RE = re.compile(r"\b(" + "|".join(PIPE_FILTERS) + r")\b", re.IGNORECASE)

LINE_BUFFERED_RE = re.compile(r"--line-buffered\b", re.IGNORECASE)

# Splits top-level statements; "||" is matched before a lone "|" would be, so
# a pipeline's own "|" segments never get cut here.
STATEMENT_SPLIT_RE = re.compile(r"&&|\|\||;|\n")

# Same leading-prefix shapes destructive-command-guard.py's own
# verb_segments() strips: a filter still anchors on `sudo tail` /
# `FOO=bar tail` / `env FOO=bar tail` / `nohup tail` right after a pipe.
# LEADING_WRAPPER_RE (env/nohup/nice/time/command/xargs/sh -c) is imported
# from _destructive_guard_shared.py rather than re-defined (todo 934: a
# local-only sudo/env pair had let `env FOO=BAR tail`/`nohup tail` slip past).
LEADING_SUDO_RE = re.compile(r"^\s*sudo\s+", re.IGNORECASE)
LEADING_ENV_RE = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*=\S*\s+")


def _strip_leading_prefix(seg: str) -> str:
    s = seg.lstrip()
    while True:
        m = LEADING_SUDO_RE.match(s) or LEADING_ENV_RE.match(s) or LEADING_WRAPPER_RE.match(s)
        if not m:
            return s
        s = s[m.end():].lstrip()


def deny(filter_name: str, subcommand: str) -> None:
    _lib_deny(
        f"[cargo-test-pipe-guard] Blocked: piping `cargo {subcommand}` output through "
        f"`{filter_name}` hides a hang - the filter buffers everything until it sees EOF, and a "
        "spawned test child (for `test`) or a merely long run (for build/check/clippy) can make "
        "that take forever with zero visible output (2026-08-19: 2h17m silent hang; 2026-08-25: "
        "~23min hang that also invalidated the build cache on retry; 2026-09-02: cargo build | "
        "tail gave 0 bytes for ~30min).",
        suffix=(
            f" Run cargo {subcommand} bare with run_in_background: true, then once it finishes "
            f"grep the finished output file (`{'^test result' if subcommand == 'test' else 'error|warning'}` "
            "is a useful pattern). Reading an already-finished output file this way is fine; "
            "`grep --line-buffered` is also fine since it flushes per line instead of swallowing output."
        ),
    )


def find_violation(command: str, cwd: str | None = None) -> tuple[str, str] | None:
    # `cwd` is accepted but unused: this guard is deliberately global (todo 780
    # step 4's own lean), kept as a parameter so a future repo-scoped check
    # only needs to read it here, not re-plumb the call site.
    for statement in STATEMENT_SPLIT_RE.split(command):
        segments = statement.split("|")
        cargo_idx = None
        subcommand = None
        offset = 0
        for i, seg in enumerate(segments):
            seg_start = offset
            offset += len(seg) + 1  # +1 for the "|" this segment was split on
            if cargo_idx is None:
                m = CARGO_SUBCOMMAND_RE.search(seg)
                if m and is_command_position(statement, seg_start + m.start()):
                    cargo_idx = i
                    subcommand = m.group("subcmd").lower()
                continue
            # todo 908: anchored to the segment's own start (post prefix-strip), not
            # a bare search - `| xargs echo tail` merely names tail as an argument.
            m = PIPE_FILTER_RE.match(_strip_leading_prefix(seg))
            if not m:
                continue
            filter_name = m.group(1)
            if filter_name.lower() == "grep" and LINE_BUFFERED_RE.search(seg):
                continue
            return filter_name, subcommand
    return None


def deny_commit_pathspec(filter_name: str) -> None:
    _lib_deny(
        f"[cargo-test-pipe-guard] Blocked: piping commit-pathspec.sh output through `{filter_name}` "
        "swallows the script's own non-zero exit - the pipeline's status is the filter's, so a "
        "refused commit reads as success (2026-10-22: `... 2>&1 | tail -6` right after reading the "
        "rule against it). skills/commit/SKILL.md step 8: never pipe its output.",
        suffix=(
            " Run the script unpiped, or put `set -o pipefail;` before the pipeline so the "
            "script's exit code survives the filter."
        ),
    )


def _quote_mask(text: str) -> list[bool]:
    """True for every character inside a single- or double-quoted span (the
    quote characters themselves count as quoted). A backslash escapes the
    next character outside single quotes.
    """
    mask = [False] * len(text)
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and quote != "'":
            mask[i] = quote is not None
            if i + 1 < len(text):
                mask[i + 1] = quote is not None
            i += 2
            continue
        if quote is None and ch in "\"'":
            quote = ch
            mask[i] = True
        elif quote is not None:
            mask[i] = True
            if ch == quote:
                quote = None
        i += 1
    return mask


# What may precede `commit-pathspec.sh` inside its own pipeline segment for the
# script to be RUN rather than merely named: an optional shell launcher, then
# the (possibly quoted) path prefix. `cat`/`grep`/`echo` before the name fall
# outside this and are left alone.
COMMIT_PATHSPEC_RE = re.compile(r"commit-pathspec\.sh\b")
COMMIT_PATHSPEC_HEAD_RE = re.compile(
    r"""(?:&\s+)?(?:(?:bash|sh|zsh|source|\.)(?:\.exe)?\s+(?:-\S+\s+)*)?["']?[^\s"']*""",
    re.IGNORECASE,
)
PIPEFAIL_RE = re.compile(r"-o\s+pipefail\b")


def find_commit_pathspec_violation(command: str) -> str | None:
    """Returns the filter name when `command` runs commit-pathspec.sh into a
    PIPE_FILTERS segment without pipefail anywhere in the command, else None.
    """
    if PIPEFAIL_RE.search(command):
        return None
    for statement in STATEMENT_SPLIT_RE.split(command):
        if not COMMIT_PATHSPEC_RE.search(statement):
            continue
        mask = _quote_mask(statement)
        pipes = [i for i, ch in enumerate(statement) if ch == "|" and not mask[i]]
        bounds = [-1] + pipes + [len(statement)]
        segments = [(bounds[i] + 1, bounds[i + 1]) for i in range(len(bounds) - 1)]
        for idx, (start, end) in enumerate(segments):
            seg = statement[start:end]
            m = COMMIT_PATHSPEC_RE.search(seg)
            if not m or not COMMIT_PATHSPEC_HEAD_RE.fullmatch(_strip_leading_prefix(seg[:m.start()])):
                continue
            for f_start, f_end in segments[idx + 1:]:
                fm = PIPE_FILTER_RE.match(_strip_leading_prefix(statement[f_start:f_end]))
                if fm:
                    return fm.group(1)
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    violation = find_violation(command, payload.get("cwd"))
    if violation:
        deny(*violation)
    filter_name = find_commit_pathspec_violation(command)
    if filter_name:
        deny_commit_pathspec(filter_name)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[cargo-test-pipe-guard] hook error, failing open: {e}\n")
        sys.exit(0)
