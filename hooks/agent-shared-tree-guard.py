"""PreToolUse hook (todo 990): denies a dispatched subagent running `git
stash`, `git reset`, or `git checkout -- <path>` in a Bash/PowerShell call.

Real incident, 2026-09-11 (`countoff`): a builder subagent ran `git stash
push -u` / `pop` to take a refactor "before" baseline while two peer
builders' uncommitted work shared the same tree. Nothing was lost that time,
but only by luck - the dispatch preamble already told the subagent not to do
this and named `git worktree add` plus `git show HEAD:<file>` as the
alternative, and it ran the command anyway. A sentence a subagent can read
and ignore needed to become something it cannot.

Whether a PreToolUse hook can tell a subagent's call from the orchestrator's
own is already settled, not re-probed here: `agent-todo-write-guard.py`
(todo 404) proved `agent_id` is present on the payload if, and only if, the
call comes from a dispatched agent, re-verified live 2026-09-11. `is_agent_call`
below is the same test, copied rather than imported - importing it from that
guard would couple two independently-owned hooks over a one-line predicate,
for a function small enough that drift risk is lower than the coupling cost.

Scoping call (stated, not left implicit): this hook does NOT carve out a
subagent's own linked worktree the way `git-workdir-guard.py` carves out a
pinned `-C <path>`. The builder preamble's own baseline advice already
replaces every legitimate use of reset/stash/checkout-path with
`git worktree add` for the copy plus `git show HEAD:<file>` for the
comparison - neither of which this hook touches - so a subagent should never
need git reset/stash/checkout-path at all, in the main tree or in a worktree
it created. Adding a cwd carve-out here would re-open exactly the gap this
hook exists to close, for a case the preamble already has a non-destructive
answer to. If a genuine exception surfaces later, it belongs in the preamble
text and this hook's docstring together, not as a silent pass-through.

`git checkout` is overloaded: `git checkout <branch>` (switching branches) is
left alone, only the path-restore form `git checkout -- <path>` (or any
positional after the `--` separator) is denied - matched on the literal `--`
separator, the one unambiguous signal git itself uses to distinguish the two
(todo 990's own approach note: "match the path form, not the word").

`/commit fold`'s `git reset --soft <sha>` and any orchestrator-run
`git stash` are unaffected by construction: both run with no `agent_id` on
the payload, so `is_agent_call` is false and this hook exits 0 before any
command matching happens.
"""

import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, basename, strip_quotes
except Exception as e:
    sys.stderr.write(f"[agent-shared-tree-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

GIT_BASENAMES = {"git", "git.exe"}
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")
# Global git flags that consume a following value token, so the subcommand
# scan never mistakes a flag's value for the subcommand itself - same table
# git-workdir-guard.py uses for the same reason.
VALUE_FLAGS = {"-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
DANGEROUS_SUBCOMMANDS = {"stash", "reset"}


def is_agent_call(payload: dict) -> bool:
    """True when this PreToolUse call came from a dispatched agent, not the
    top-level orchestrator session (see module docstring)."""
    return bool(payload.get("agent_id"))


def tokenize(segment: str) -> list[str]:
    try:
        return [strip_quotes(t) for t in shlex.split(segment, posix=False)]
    except ValueError:
        return segment.split()


def git_subcommand(tokens: list[str]) -> tuple[str | None, list[str]]:
    """Return (subcommand, rest_tokens) for a `git ...` token list, skipping
    global flags the same way git-workdir-guard.py's git_write_subcommand
    does. (None, []) when `tokens` isn't a git invocation at all.
    """
    if not tokens or basename(tokens[0]) not in GIT_BASENAMES:
        return None, []
    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-C":
            i += 2
            continue
        low = tok.lower()
        if low == "-c" or low.split("=", 1)[0] in VALUE_FLAGS:
            i += 1 if "=" in tok else 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    if i >= len(tokens):
        return None, []
    return tokens[i].lower(), tokens[i + 1:]


def is_checkout_path_form(rest: list[str]) -> bool:
    """True for the path-restore form (`git checkout -- <path>`), false for a
    branch switch (`git checkout <branch>`) - see module docstring."""
    return "--" in rest


def match_hit(command: str) -> str | None:
    for segment in CHAIN_SPLIT_RE.split(command):
        tokens = tokenize(segment)
        if not tokens:
            continue
        sub, rest = git_subcommand(tokens)
        if sub in DANGEROUS_SUBCOMMANDS:
            return f"git {sub}"
        if sub == "checkout" and is_checkout_path_form(rest):
            return "git checkout --"
    return None


def main() -> None:
    payload = read_payload()
    if (payload.get("tool_name") or "") not in ("Bash", "PowerShell"):
        sys.exit(0)
    if not is_agent_call(payload):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    hit = match_hit(command)
    if not hit:
        sys.exit(0)

    deny(
        f"[agent-shared-tree-guard] Blocked: {hit} can destroy another agent's "
        "uncommitted work on this shared tree (incident: 2026-09-11, countoff). "
        "Take a baseline with `git worktree add` instead, compare against clean "
        "state with `git show HEAD:<file>`, and remove the worktree afterward "
        "with `~/.claude/skills/close/safe-remove-worktree.ps1`. If you "
        "genuinely need this exact command, report the need in your dispatch "
        "report-back instead of running it yourself."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[agent-shared-tree-guard] hook error, failing open: {e}\n")
        sys.exit(0)
