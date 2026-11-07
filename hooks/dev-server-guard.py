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
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, deny, tokenize_command as tokenize, basename, is_command_position, split_command_segments
except Exception as e:
    sys.stderr.write(f"[dev-server-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

INFO_FLAGS = {"--version", "-v", "-V", "--help", "-h"}


def invokes_supervisor(tokens) -> bool:
    return any(basename(t) == "sv.ps1" for t in tokens)


# Commands whose arguments are text or paths, never a program to launch:
# `grep -n "vite" f` tokenizes to a bare `vite` token that is only a search term.
TEXT_COMMANDS = {
    "grep", "egrep", "fgrep", "rg", "ag", "findstr", "select-string", "sls",
    "echo", "write-output", "write-host", "printf", "cat", "type", "get-content",
    "git", "ls", "dir", "get-childitem", "which", "where", "get-command",
}

# Package managers followed by a verb that names a package as its argument
# (`npm install fastify`, `pip install uvicorn`, `pnpm add -D vite`,
# `npm view vite version`): the server name there is the thing being
# installed or inspected, never a program being launched.
PACKAGE_TOOLS = {
    "npm", "pnpm", "yarn", "bun", "pip", "pip3", "pipx", "uv", "poetry", "cargo", "gem",
}
PACKAGE_VERBS = {
    "install", "i", "add", "remove", "rm", "uninstall", "un", "update", "upgrade",
    "view", "info", "show", "ls", "list", "outdated", "why", "explain", "search",
    "audit", "download", "freeze", "pack",
}

_SEPARATOR_END = (";", "|", "&")


def _norm(token: str) -> str:
    # A PowerShell/shell statement separator glued to the last word (`build;`)
    # is not part of the word: `vite build; cargo ...` must read as `vite build`.
    return token.lower().rstrip("".join(_SEPARATOR_END))


def _is_argument_of_text_command(tokens, i) -> bool:
    """True when tokens[i] sits in the argument list of a TEXT_COMMANDS word
    in the same statement (walking back until a separator token)."""
    for j in range(i - 1, -1, -1):
        t = tokens[j]
        if t.endswith(_SEPARATOR_END) or t in ("&&", "||"):
            return False
        if basename(t) in TEXT_COMMANDS:
            return True
    return False


def _is_argument_of_package_verb(tokens, i) -> bool:
    """True when tokens[i] sits after `<package manager> <install/inspect verb>`
    in the same statement (walking back until a separator token)."""
    for j in range(i - 1, -1, -1):
        t = tokens[j]
        if t.endswith(_SEPARATOR_END) or t in ("&&", "||"):
            return False
        if (
            basename(t) in PACKAGE_TOOLS
            and j + 1 < i
            and tokens[j + 1].lower() in PACKAGE_VERBS
        ):
            return True
    return False


def is_dev_server_command(tokens):
    """Return a short label naming the matched dev-server shape, or None."""
    lc = [_norm(t) for t in tokens]
    bases = [basename(t).rstrip("".join(_SEPARATOR_END)) for t in tokens]
    n = len(lc)

    for i in range(n):
        base = bases[i]
        nxt = lc[i + 1] if i + 1 < n else None
        if nxt in INFO_FLAGS:
            continue
        if _is_argument_of_text_command(tokens, i) or _is_argument_of_package_verb(tokens, i):
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

    # Per statement: a newline is not a token separator, so `npm install\nvite`
    # would otherwise read as one install statement with `vite` as its argument.
    matched = None
    # A backslash or backtick before the newline continues the statement.
    joined = re.sub(r"[\\`]\r?\n", " ", command)
    for segment in split_command_segments(joined) or [joined]:
        matched = is_dev_server_command(tokenize(segment))
        if matched:
            break
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
