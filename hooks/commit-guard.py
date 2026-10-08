"""PreToolUse hook: block raw `git commit` outside the /commit skill flow.

Fires on every Bash/PowerShell call. Detects a `git commit` subcommand via
token-aware parsing (not string search) so it can't be fooled by "commit" in
a message/path or tripped by `commit-graph`.

Also gates `git commit-tree` and a `git update-ref` that moves a branch
pointer (HEAD or refs/heads/*), since that pair lands a commit without ever
using the literal word "commit" (todo 1085) - see `is_commit_landing_invocation`.
This only catches a raw shell command that spells those calls out directly;
`skills/commit/split-hunks.py commit` builds the same kind of commit via its
own `subprocess` calls, invisible to this hook (it only sees the
`python ... split-hunks.py commit ...` command string), so it runs
prefilter-gate.sh itself instead - see that script's module docstring.

Two marker styles are honoured:
- Session marker (`.session-markers/<session_id>`): written ONCE per
  session, never consumed, matched by exact session id from the hook
  payload - this is what `/commit` writes now, so only the first commit of a
  session pays for the marker-write call. Lives in its own subdirectory, out
  of the glob-matched `.commit-marker*` space, so an external cleanup that
  globs temp per-commit markers can never reach a live session's marker
  (todo 341, 2026-08-16). `legacy_session_marker_path()` is a read-only
  fallback to the pre-split location for markers written before this change.
- Legacy per-commit marker (`.commit-marker-<suffix>` or plain
  `.commit-marker`): fresh-window + oldest-consumed, kept for callers that
  still write one marker per commit (e.g. `/mega-todos` builder agents).

Fails open on any hook error so a bug here can never permanently wedge every
commit in every repo.

Override: set CLAUDE_COMMIT_HOOK_BYPASS=1 in this session's environment
(settings.json "env", or exported before launching claude) to bypass if
/commit is broken - an inline prefix on the command itself does not reach
this hook.

Prefilter re-check (todo 844): once a marker allows the commit, this hook
also re-runs `skills/commit/prefilter-gate.sh` itself over the commit's own
`-- <paths>` pathspec, so a `;` (which ignores exit status) between an
earlier gate call and `git commit` can no longer let a flagged diff land -
the gate's verdict is recomputed here, at commit time, independent of how
the caller chained the shell command. A pathspec-less commit or a gate that
can't be invoked at all fails open, same philosophy as the rest of this file.

Decided (todo 868): a pathspec-less commit stays fail-open, deliberately -
resolving it would mean reading the shared git index to guess a pathspec,
which can hold another concurrent session's staged work.

Marker pruning (todo 917): every attempted `git commit` is already the
moment this guard touches MARKER_DIR, so it is also the opportunistic point
where any legacy `.commit-marker-*` older than FRESHNESS_SECONDS gets swept
- see `_marker_pruning.py` for why that's provably safe (such a marker is
already permanently unreachable to `consume_fresh_marker`, not merely
stale). Session markers are pruned separately, at write time, in
`write-session-marker.ps1` - see that file for the liveness rule. A failure
in the pruning helper is swallowed locally so a bug there can never affect
this guard's own allow/deny decision.
"""

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker, FRESHNESS_SECONDS
except Exception as e:
    sys.stderr.write(f"[commit-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

try:
    from _marker_pruning import prune_expired_markers
except Exception:
    # Cleanup is best-effort and must never block a commit on its own account
    # (see the docstring paragraph above); a broken import just disables it.
    prune_expired_markers = None

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = ".commit-marker*"
SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
LEGACY_SESSION_MARKER_PREFIX = ".commit-marker-session-"
OVERRIDE_ENV = "CLAUDE_COMMIT_HOOK_BYPASS"
# Must be set in this session's environment (settings.json "env", or exported
# before launching claude); an inline `VAR=1 <cmd>` prefix never reaches this
# hook, since PreToolUse reads the command string before any shell parses it.

# Short flags that consume a separate following token as their value (so it
# doesn't get mistaken for the subcommand), e.g. `git -C <path> commit ...`.
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}

# Shell operators that can follow a `git commit` invocation in a chained
# command; a pathspec scan must stop at these, never swallow tokens from a
# following command as if they were commit paths.
_CHAIN_OPERATORS = {";", "&&", "||"}

PREFILTER_GATE_SCRIPT = _HOOKS_DIR.parent / "skills" / "commit" / "prefilter-gate.sh"


def _tokenize(command: str) -> list[str] | None:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. - can't safely tokenize; don't block on a guess.
        return None


def _subcommand_index(tokens: list[str], name: str, start: int = 0) -> int | None:
    """Index of the `name` token in a `git <name>` invocation at or after
    `start`, walking past global flags (skipping their values for flags like
    -C), or None."""
    for i, tok in enumerate(tokens):
        if i < start or tok != "git":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] in VALUE_FLAGS and "=" not in tokens[j]:
                j += 2
            else:
                j += 1
        if j < len(tokens) and tokens[j] == name:
            return j
    return None


def _commit_subcommand_index(tokens: list[str]) -> int | None:
    """Index of the `commit` token in a `git commit` invocation, walking past
    global flags (skipping their values for flags like -C), or None."""
    return _subcommand_index(tokens, "commit")


def is_git_commit_invocation(command: str) -> bool:
    """True if `command` contains a real `git commit` subcommand call.

    Token-based: walks past global flags (skipping their values for flags
    like -C) to find the actual subcommand word, so `commit-graph`,
    `--grep="commit"`, or a path/message containing "commit" never match.
    """
    tokens = _tokenize(command)
    if tokens is None:
        return False
    return _commit_subcommand_index(tokens) is not None


# update-ref flags that consume a following token as their value, so it
# isn't mistaken for the ref being updated (e.g. `-m <reason>`).
_UPDATE_REF_VALUE_FLAGS = {"-m"}


def _is_commit_tree_invocation(tokens: list[str]) -> bool:
    """True if `tokens` contains a `git commit-tree` call. This alone
    creates a new commit object (no ref moves yet), but it's the exact
    primitive split-hunks.py's design note (todo 1085) names as the one that
    slips past `is_git_commit_invocation`'s literal "commit" match."""
    return _subcommand_index(tokens, "commit-tree") is not None


def _is_branch_update_ref_invocation(tokens: list[str]) -> bool:
    """True if `tokens` contains a `git update-ref` call whose target ref is
    `HEAD` or `refs/heads/*` - the half of the commit-tree + update-ref pair
    that actually lands a commit by moving a branch pointer. An update-ref
    to any other ref (notes, tags-as-refs, etc.) or a `--stdin`-fed call
    with no positional ref argument is left alone - it's not a commit.

    Every update-ref in a chained command is checked, since a notes update
    first and a branch move second still lands a commit."""
    idx = _subcommand_index(tokens, "update-ref")
    while idx is not None:
        k = idx + 1
        while k < len(tokens) and tokens[k].startswith("-"):
            if tokens[k] in _UPDATE_REF_VALUE_FLAGS:
                k += 2
            else:
                k += 1
        if k < len(tokens):
            ref = tokens[k]
            if ref == "HEAD" or ref.startswith("refs/heads/"):
                return True
        idx = _subcommand_index(tokens, "update-ref", idx + 1)
    return False


def is_commit_landing_invocation(command: str) -> bool:
    """True if `command` contains any shell-visible git call that lands a
    commit: plain `git commit`, `git commit-tree` (todo 1085 - the same
    token-aware tokenize/walk `is_git_commit_invocation` uses, extended to
    the commit-tree + update-ref route `split-hunks.py commit` documents as
    bypassing the literal "commit" match), or a `git update-ref` that moves
    a branch pointer (HEAD or refs/heads/*). This is the gate `main()` acts
    on; `is_git_commit_invocation` itself stays `git commit`-only since
    `extract_commit_pathspec`'s `--`-pathspec resolution only makes sense
    for that form - commit-tree/update-ref have no equivalent pathspec, so
    callers landing a commit that way still get the marker gate but not the
    prefilter re-check (split-hunks.py runs that gate itself; see its
    module docstring).
    """
    tokens = _tokenize(command)
    if tokens is None:
        return False
    return (
        _commit_subcommand_index(tokens) is not None
        or _is_commit_tree_invocation(tokens)
        or _is_branch_update_ref_invocation(tokens)
    )


def extract_commit_pathspec(tokens: list[str]) -> list[str] | None:
    """Paths named after a `--` separator in the `git commit` invocation
    found in `tokens`, or None if there's no such separator to resolve
    (e.g. no explicit pathspec). Stops at a chain operator so a command
    riding after the commit is never read as more paths.
    """
    idx = _commit_subcommand_index(tokens)
    if idx is None:
        return None
    k = idx + 1
    while k < len(tokens) and tokens[k] not in _CHAIN_OPERATORS:
        if tokens[k] == "--":
            paths = []
            m = k + 1
            while m < len(tokens) and tokens[m] not in _CHAIN_OPERATORS:
                paths.append(tokens[m])
                m += 1
            return paths
        k += 1
    return None


def resolve_bash() -> str | None:
    """Locate a POSIX-capable bash for running prefilter-gate.sh.

    On Windows, `bash` on PATH can resolve to the System32 WSL launcher
    instead of Git for Windows' bash - proven here to silently fail on a
    `C:/...` script path (WSL treats it as a Linux-side relative path that
    doesn't exist). Prefer the bash co-located with the resolved `git.exe`.
    """
    if os.name != "nt":
        return shutil.which("bash")
    git_exe = shutil.which("git")
    if git_exe:
        candidate = Path(git_exe).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def run_prefilter_gate(paths: list[str], cwd: str) -> int | None:
    """Re-run prefilter-gate.sh over `paths`, independent of the caller's own
    shell chaining (todo 844). Returns the gate's exit code, or None if it
    could not be invoked at all - fails open rather than wedging every commit
    on an infra problem (missing bash, missing script, timeout).
    """
    if not PREFILTER_GATE_SCRIPT.exists():
        return None
    bash = resolve_bash()
    if not bash:
        return None
    try:
        result = subprocess.run(
            [bash, str(PREFILTER_GATE_SCRIPT), *paths],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode


def session_marker_path(session_id: str) -> Path:
    return SESSION_MARKER_DIR / session_id


def legacy_session_marker_path(session_id: str) -> Path:
    """Pre-split location - read-only fallback for a marker written before
    the `.session-markers/` move (todo 341)."""
    return MARKER_DIR / f"{LEGACY_SESSION_MARKER_PREFIX}{session_id}"


def _prune_expired_legacy_markers() -> None:
    """Best-effort sweep of `.commit-marker-*` files already too old for
    `consume_fresh_marker` to ever pick up (todo 917). Never allowed to
    affect this guard's allow/deny outcome - see module docstring.
    """
    if prune_expired_markers is None:
        return
    try:
        prune_expired_markers(
            MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS,
            exclude_prefix=LEGACY_SESSION_MARKER_PREFIX,
        )
    except Exception:
        pass


def _deny_prefilter_failure() -> None:
    deny(
        "[commit-guard] This commit's own prefilter-gate re-check just failed "
        "(em-dash/comment-tense/secret-scan); no part of this call "
        "ran, including any command chained before it. A `;` between an earlier "
        "gate run and `git commit` does not skip this - the gate is re-run here, "
        "at commit time, over the exact pathspec being committed. Run `bash "
        "~/.claude/skills/commit/prefilter-gate.sh <files>` to see the full "
        "flagged output, fix it, then retry."
    )


# Same two patterns commit-pathspec.sh refuses, for the by-hand `git commit -m` fallback.
_AI_TRAILER_RE = re.compile(r"^co-authored-by:.*(claude|anthropic)", re.IGNORECASE)
_AI_GENERATED_RE = re.compile(r"generated with \[?claude code", re.IGNORECASE)
# -m, or -m bundled after git commit's boolean short flags (`-am`, `-avm`), with the
# value either attached or in the next token.
_SHORT_MESSAGE_RE = re.compile(r"^-[aenqsv]*m(.*)$", re.DOTALL)


def _read_message_file(name: str, cwd: str) -> str | None:
    if not name or name == "-":
        return None
    path = Path(name) if Path(name).is_absolute() else Path(cwd or ".") / name
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:65536]
    except OSError:
        return None


def commit_messages(tokens: list[str], cwd: str = "") -> list[str]:
    """Every -m / --message value in the command, however it is spelled, plus
    the content of a -F / --file message file that exists."""
    messages = []
    for i, tok in enumerate(tokens):
        short = _SHORT_MESSAGE_RE.match(tok)
        file_name = None
        if tok in ("-F", "--file") and i + 1 < len(tokens):
            file_name = tokens[i + 1]
        elif tok.startswith("--file="):
            file_name = tok[len("--file="):]
        if file_name is not None:
            content = _read_message_file(file_name, cwd)
            if content is not None:
                messages.append(content)
        elif tok == "--message" and i + 1 < len(tokens):
            messages.append(tokens[i + 1])
        elif tok.startswith("--message="):
            messages.append(tok[len("--message="):])
        elif short and short.group(1):
            messages.append(short.group(1))
        elif short and i + 1 < len(tokens):
            messages.append(tokens[i + 1])
    return messages


def ai_attribution_line(tokens: list[str], cwd: str = "") -> str | None:
    for message in commit_messages(tokens, cwd):
        for line in message.splitlines():
            if _AI_TRAILER_RE.search(line.strip()) or _AI_GENERATED_RE.search(line):
                return line.strip()
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    if not is_commit_landing_invocation(command):
        sys.exit(0)

    _prune_expired_legacy_markers()

    tokens = _tokenize(command) or []

    # Before the bypass: /commit's Rules allow no AI attribution, ever.
    attribution = ai_attribution_line(tokens, payload.get("cwd") or "")
    if attribution:
        deny(
            "[commit-guard] This commit message carries AI attribution, which /commit's "
            f"Rules never allow: `{attribution}`. Drop that line and retry; no part of "
            "this call ran."
        )

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    session_id = payload.get("session_id") or ""
    if session_id and (
        session_marker_path(session_id).exists()
        or legacy_session_marker_path(session_id).exists()
    ):
        paths = extract_commit_pathspec(tokens)
        if paths and run_prefilter_gate(paths, payload.get("cwd") or "") == 1:
            _deny_prefilter_failure()
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS, exclude_prefix=LEGACY_SESSION_MARKER_PREFIX):
        paths = extract_commit_pathspec(tokens)
        if paths and run_prefilter_gate(paths, payload.get("cwd") or "") == 1:
            _deny_prefilter_failure()
        sys.exit(0)

    reason = (
        "[commit-guard] Raw `git commit` (or a commit-tree/update-ref landing) is blocked; no part of this call ran, "
        "including any command chained before it. Use the /commit skill instead "
        f"- it writes the session marker this hook checks. If /commit itself is "
        f"broken, set {OVERRIDE_ENV}=1 in this session's environment (settings.json "
        f"\"env\", or exported before launching claude) - an inline prefix on the "
        f"command itself does not reach this hook."
    )
    if ".commit-marker" in command or ".session-markers" in command:
        reason += (
            " This command already tries to write the marker itself: the hook "
            "reads the whole command string before any of it executes, so a "
            "marker chained with `;`/`&&` is never visible in time - write it in "
            "its own tool call first."
        )
    deny(reason)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[commit-guard] hook error, failing open: {e}\n")
        sys.exit(0)
