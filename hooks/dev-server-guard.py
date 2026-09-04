"""PreToolUse hook: block a long-lived dev server started raw in Bash/PowerShell.

Fires on every Bash/PowerShell call. Tokenizes the command (same shlex
convention as package-manager-guard.py) and matches a fixed list of
dev-server launch shapes: bare `vite` (including `vite preview`), `next dev`,
`next start`, `npm|pnpm|yarn run dev`, `pnpm|yarn dev`, `flutter run`,
`uvicorn`, `fastify [start]`, and `tauri dev` (any prefix: cargo/npm
run/pnpm/yarn). One-off commands (`npm test`, `npm run build`, `vite build`)
are deliberately not matched - CLAUDE.md's Process Hygiene rule exempts them.

`dart run` is deliberately NOT matched (see todo 883): unlike the shapes
above, `dart run <script>` is a script-name distinction, not a command-shape
one - the same ambiguity `npm run` has for `dev` vs `build`, but with no
fixed script name to key on across projects.

Escape condition: `skills/supervised-run/sv.ps1` never execs the dev command
in the calling shell, it POSTs it to the server_supervisor daemon (sv.ps1:147,
`Invoke-Api $cfg 'POST' '/run' $body`). So any command invoking that script
(any subcommand) is a supervisor management call, never a raw launch, and is
allowed unconditionally before the pattern scan runs.

Incident: 90+ orphan vitest processes once pegged the CPU at 100% and 90C.
`/supervised-run` (SKILL.md) already exists to prevent this; it was prose
only. Fails open on any hook error so a bug here can never block shell work.

todo 908: tokenize_command's ValueError fallback (naive `command.split()`,
no quote awareness) let a quoted `-Note` prose mentioning "next start" read
as two adjacent real tokens once an unrelated apostrophe broke shlex. A
clean shlex parse never needs the second pass below.
"""

import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, tokenize_command as tokenize, basename, is_command_position
except Exception as e:
    sys.stderr.write(f"[dev-server-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

INFO_FLAGS = {"--version", "-v", "-V", "--help", "-h"}


def invokes_supervisor(tokens) -> bool:
    return any(basename(t) == "sv.ps1" for t in tokens)


def is_dev_server_command(tokens):
    """Return a short label naming the matched dev-server shape, or None."""
    lc = [t.lower() for t in tokens]
    bases = [basename(t) for t in tokens]
    n = len(lc)

    for i in range(n):
        base = bases[i]
        nxt = lc[i + 1] if i + 1 < n else None
        if nxt in INFO_FLAGS:
            continue

        if base in ("vite", "vite.cmd") and nxt != "build":
            return "vite"
        if base == "uvicorn":
            return "uvicorn"
        if base == "flutter" and nxt == "run":
            return "flutter run"
        if base == "next" and nxt in ("dev", "start"):
            return f"next {nxt}"
        if base == "fastify" and nxt in (None, "start"):
            return "fastify"
        if base == "tauri" and nxt == "dev":
            return "tauri dev"
        if base in ("npm", "pnpm", "yarn") and nxt == "run" and lc[i + 2:i + 3] == ["dev"]:
            return f"{base} run dev"
        if base in ("pnpm", "yarn") and nxt == "dev":
            return f"{base} dev"

    return None


def _shlex_clean(command: str) -> bool:
    try:
        shlex.split(command, posix=False)
        return True
    except ValueError:
        return False


def _confirmed_at_command_position(command: str, label: str) -> bool:
    """Second pass, only trusted when `_shlex_clean` is False (todo 908):
    does `label`'s own words ("next start", "vite", ...) appear anywhere in
    the RAW command text at command position - start of a statement/pipe
    segment, not deep inside quoted prose?
    """
    pattern = re.compile(r"\b" + r"\s+".join(re.escape(w) for w in label.split()) + r"\b", re.IGNORECASE)
    return any(is_command_position(command, m.start()) for m in pattern.finditer(command))


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    tokens = tokenize(command)
    if not tokens:
        sys.exit(0)

    if invokes_supervisor(tokens):
        sys.exit(0)

    matched = is_dev_server_command(tokens)
    if matched and not _shlex_clean(command) and not _confirmed_at_command_position(command, matched):
        matched = None
    if matched:
        deny(
            "[dev-server-guard] \"%s\" looks like a long-lived dev server started "
            "directly in the shell (matched: %s). Route it through /supervised-run "
            "instead of running it raw - a raw launch has no supervisor tracking it "
            "and can leak an orphan process."
            % (command.strip(), matched)
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[dev-server-guard] hook error, failing open: {e}\n")
        sys.exit(0)
