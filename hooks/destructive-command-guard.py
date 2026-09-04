"""PreToolUse hook: block or gate the class of catastrophic shell commands
that no purpose-built guard here covers (todo 419).

Severity dial via env var CLAUDE_HOOK_PROFILE, values minimal/standard/strict,
default standard. An unrecognised value falls back to standard and says so on
stderr. Tiers were set by measuring 62,270 unique real Bash/PowerShell
commands harvested from this machine's own transcripts (C:\\tmp\\p2-corpus):

CORE tier (deny at every profile, including minimal): 0 hits measured across
all of them, so there is no plausible legitimate use. rm -rf on /, ~, $HOME,
an unresolved $VAR, ../.. or a drive root; rm -rf on a system directory;
Remove-Item -Recurse -Force on a drive root/home; a raw write to /dev/<x>;
mkfs/dd of=|if=/dev/<x>; Clear-Disk/Format-Volume/format <drive>:; DROP
TABLE/DATABASE/SCHEMA and TRUNCATE TABLE run through a real SQL client/ORM/
inline-script driver; chmod 777/a+rwx; package publish with no --dry-run/-n;
git push --force (or a short flag bundle containing f) without
--force-with-lease. Pipe-to-shell (curl/wget/iwr piped into a shell) also
measured 0 hits once quoted spans are masked before matching; its one raw
hit was a shell name inside a quoted grep alternation.

MIDDLE tier (ask at standard, silently allowed at minimal, deny at strict):
measured a handful of genuine uses, so an outright ban would train everyone
to disable the guard. git reset --hard (3 hits, all genuine resets); git
clean -f* (1 hit, path-scoped); DELETE FROM with no WHERE in the SAME SQL
statement, run through a real SQL client/ORM/inline-script driver (4 hits,
all deliberate local-dev clears); bare diskpart (1 hit, compacting a Docker
vhdx); disk-doctor's own delete/uninstall verbs - Clear-RecycleBin, cleanmgr,
docker system/image/container/volume/builder prune, winget/choco uninstall,
Uninstall-Package, msiexec /X|/uninstall (todo 835, re-measured against a
re-harvested 86,430-command corpus: 9 hits total, 1 docker prune and 8
msiexec /X uninstalls via Start-Process, all genuine disk-doctor runs, 0 for
every other verb in the list). A scoped Remove-Item stays OUT of this tier on
purpose: the same corpus has 562 unique Remove-Item invocations, nearly all
ordinary project cleanup (screenshot dirs, .claims files, .git/index.lock),
so a target-based rule for it would ask on routine work far more than it
would catch a real disk-doctor delete. Hand-probing after the measurement
found one more false positive the corpus alone missed: a bare substring
search for msiexec+/uninstall hit this file's OWN measurement script, which
held both words as regex source text in a Python string, never invoked;
match_msiexec_uninstall() now also requires the bare verb at command
position or a co-occurring -ArgumentList flag.

A dangerous verb only fires when it sits at the START of a command segment
(split on ; && || |, after stripping a leading `sudo` and any `VAR=value`
env-assignment prefix, and after deleting quote characters so `rm -rf
"$HOME"` still exposes $HOME). This is what stops `git commit -m "chmod 777
was the wrong fix"` or `grep -rn mkfs docs/` from tripping a CORE rule for
merely mentioning the word: the corpus can prove a pattern never fired on a
past command, but it cannot prove the pattern can't fire on a mention, since
mentions of these verbs in commit messages/docs were never sampled. SQL verbs
never sit at command position, so DROP/TRUNCATE/DELETE-no-WHERE instead
require an execution-context signal (a SQL client, an ORM/migration tool, an
execute flag, or an inline-script driver) in the SAME statement.

Deliberately NOT covered, each already decided elsewhere:
- non-force git push to master/main/develop: this repo pushes directly to
  master by design, blocking that would break the primary workflow here.
- shell chaining (&&/;/|): retired outright, see done/07 and done/64.
- bare eval / Invoke-Expression / iex: measured false positives only, and
  iex is already handled by shell-content-write-guard.py; not duplicated.
- git stash outside a shared checkout: read-mostly (108 hits, mostly
  list/show/pop); todo 391 wants a sanctioned baseline mechanism, not a ban.
  The shared-checkout case is covered under SHARED tier below (todo 775).
- bare diskpart alone is never denied, only asked/gated per the dial above:
  its one measured use was a legitimate vhdx compaction.

SHARED tier (todo 797, ask/deny like MIDDLE, but gated on an extra signal):
git reset/rebase/checkout/branch -f against a positional ref (HEAD~n, HEAD^,
@~n) in the repo's MAIN checkout, while the Conductor daemon reports live
peers for this session. HEAD~n is relative, so its meaning changes the
instant a peer commits - the near-miss was a `reset --soft HEAD~1` that
would have resolved to a peer's commit had it landed a second later. A
worktree is exempt outright (its own HEAD/index can't collide this way);
a genuinely solo session stays prompt-free even on a hit, since peer count
comes back 0.

Also SHARED tier (todo 775): `git stash push`/`save` (bare `git stash`
defaults to push) under the same main-checkout-plus-live-peer gate - it
reads the WHOLE working tree by pathspec and is the one common command that
can sweep a peer's uncommitted edits off disk. `list`/`show`/`pop`/`apply`/
`drop`/`clear`/`branch` never touch another session's files this way and
stay exempt. The hit message runs `git status` scoped to the command's own
pathspec (or the whole tree for a bare/no-pathspec stash) and names the
files currently at risk, so the prompt shows exactly what a peer would lose.

rm/mkfs/dd/chmod are POSIX-only syntax; Remove-Item/Clear-Disk/Format-Volume/
diskpart are PowerShell-only; the SQL, publish, and git rules apply to
whichever shell carries them. Fails open on any unexpected exception.

Override: set CLAUDE_DESTRUCTIVE_HOOK_BYPASS=1 in the SESSION's environment
(settings.json "env", or exported before launching claude) to skip this guard
entirely, matching commit-guard.py's CLAUDE_COMMIT_HOOK_BYPASS precedent -
checked first thing in main(), and named in every deny/ask reason. An inline
`VAR=1 <cmd>` prefix does not work and cannot: PreToolUse sees the command
string before any shell parses it, so the hook process never gets that var.
Verified by a nested `claude -p` run on 2026-08-21.

Module layout (todo 911): this file stays the entry point and the
CORE/MIDDLE/SHARED tier dispatcher. The four concerns the file used to carry
inline now live in sibling modules - _destructive_guard_shared.py (tokenizing
primitives), _destructive_guard_fs.py (filesystem/device), _destructive_guard_
sql.py (SQL), _destructive_guard_git.py (git force/reset, plus the two SHARED
pattern matchers) and _destructive_guard_peers.py (shared-checkout peer
probing) - imported below. match_shared_checkout_hit() itself and the
publish/pipe-to-shell/diskpart/disk-doctor matchers, which don't belong to any
of the four named concerns, stay here with the dispatcher.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny as _lib_deny, ask as _lib_ask
    from _destructive_guard_shared import verb_segments
    from _destructive_guard_fs import (
        match_chmod_777,
        match_device_write,
        match_disk_wipe_win,
        match_mkfs_dd,
        match_remove_item,
        match_rm_rf,
    )
    from _destructive_guard_sql import match_sql_drop, match_sql_delete_no_where, match_sql_truncate
    from _destructive_guard_git import (
        match_git_clean_force,
        match_git_positional_ref,
        match_git_push_force,
        match_git_reset_hard,
        match_git_stash_push,
    )
    from _destructive_guard_peers import fetch_peer_count, is_main_checkout, stash_swept_files
except Exception as e:
    sys.stderr.write(f"[destructive-command-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

PROFILES = ("minimal", "standard", "strict")
OVERRIDE_ENV = "CLAUDE_DESTRUCTIVE_HOOK_BYPASS"
# Proven by a nested `claude -p` run: an inline `VAR=1 <cmd>` prefix does NOT
# reach this hook, because PreToolUse reads the command string before any shell
# parses it. So the reason text has to name where the variable actually goes.
OVERRIDE_HINT = (
    f" To bypass a false positive, set {OVERRIDE_ENV}=1 in this session's environment"
    " (settings.json \"env\", or exported before launching claude) - an inline"
    " prefix on the command itself does not reach this hook."
)

DISKPART_RE = re.compile(r"^diskpart\b", re.IGNORECASE)
# disk-doctor's own delete/uninstall verbs (skills/disk-doctor/gate.md, todo 835):
# each has no legitimate non-uninstall use, so the verb alone is the target -
# unlike Remove-Item, which measured 562 unique ordinary-work hits and stays
# out of this list on purpose (see module docstring).
DISK_DOCTOR_VERB_RE = re.compile(
    r"^(Clear-RecycleBin|cleanmgr|winget\s+uninstall|choco(?:latey)?\s+uninstall|Uninstall-Package)\b",
    re.IGNORECASE,
)
DOCKER_PRUNE_RE = re.compile(r"^docker\s+(?:system|image|container|volume|builder)\s+prune\b", re.IGNORECASE)
# msiexec is always wrapped (Start-Process ... -ArgumentList), so it can't
# anchor at command position. A bare substring match was a false positive on
# this file's own measurement script (msiexec+/uninstall as unrun regex text
# in a Python string); require the bare verb or -ArgumentList alongside it.
MSIEXEC_VERB_RE = re.compile(r"\bmsiexec(?:\.exe)?\b", re.IGNORECASE)
MSIEXEC_BARE_ANCHOR_RE = re.compile(r"^msiexec(?:\.exe)?\b", re.IGNORECASE)
MSIEXEC_ARGLIST_RE = re.compile(r"-ArgumentList\b", re.IGNORECASE)
MSIEXEC_UNINSTALL_FLAG_RE = re.compile(r"/x\{|/uninstall\b", re.IGNORECASE)

PUBLISH_ANCHOR_RE = re.compile(r"^((npm|yarn|pnpm|bun)\s+publish|cargo\s+publish|gem\s+push|twine\s+upload|wally\s+publish)\b")
DRYRUN_RE = re.compile(r"--dry-run\b|(?<!\S)-n(?!\S)")

SQUOTE_RE = re.compile(r"'[^']*'")
DQUOTE_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
PIPE_TO_SHELL_RE = re.compile(
    r"\b(curl|wget|Invoke-WebRequest|iwr)\b[^\n]*\|\s*(?:sudo\s+)?(bash|sh|zsh|ksh|fish|dash)\b",
    re.IGNORECASE,
)


def mask_quotes(command: str) -> str:
    return DQUOTE_RE.sub("Q", SQUOTE_RE.sub("Q", command))


def match_publish_no_dryrun(command: str):
    for seg in verb_segments(command):
        if PUBLISH_ANCHOR_RE.match(seg) and not DRYRUN_RE.search(seg):
            return "package publish with no --dry-run/-n ships to a public registry irreversibly; add --dry-run/-n first"
    return None


def match_pipe_to_shell(command: str):
    if PIPE_TO_SHELL_RE.search(mask_quotes(command)):
        return "piping curl/wget/iwr output straight into a shell interpreter runs unreviewed remote code; download and inspect it first"
    return None


def match_diskpart(command: str):
    for seg in verb_segments(command):
        if DISKPART_RE.match(seg):
            return "diskpart can repartition or format a disk irreversibly"
    return None


def match_msiexec_uninstall(seg: str) -> bool:
    if not MSIEXEC_VERB_RE.search(seg) or not MSIEXEC_UNINSTALL_FLAG_RE.search(seg):
        return False
    return bool(MSIEXEC_BARE_ANCHOR_RE.match(seg) or MSIEXEC_ARGLIST_RE.search(seg))


def match_disk_doctor_delete(command: str):
    for seg in verb_segments(command):
        if DISK_DOCTOR_VERB_RE.match(seg) or DOCKER_PRUNE_RE.match(seg) or match_msiexec_uninstall(seg):
            return "disk-doctor delete/uninstall verb; confirm this exact command per skills/disk-doctor/gate.md first"
    return None


SHARED_CHECKS = (
    match_git_positional_ref,
    match_git_stash_push,
)


def check_shared(command: str):
    for check in SHARED_CHECKS:
        result = check(command)
        if result:
            return result
    return None


def match_shared_checkout_hit(command: str, cwd: str, session_id: str):
    """Compound SHARED-tier signal: a positional-ref or stash-push pattern
    hit, in the MAIN checkout, with at least one live peer. Any one absent
    means no hit, which is what keeps a worktree or a solo session
    prompt-free (todo 797). A stash hit gets the at-risk file list appended.

    is_main_checkout/fetch_peer_count are called here by bare name (not
    module-qualified) on purpose: hooks/test_destructive_command_guard.py
    monkeypatches them as attributes of this loaded module, and a bare-name
    lookup at call time is what makes that monkeypatch visible here (see
    _destructive_guard_peers.py's own docstring for the failure mode this
    avoids).
    """
    hit = check_shared(command)
    if not hit:
        return None
    if not is_main_checkout(cwd):
        return None
    if fetch_peer_count(session_id) <= 0:
        return None
    if hit.startswith("git stash"):
        swept = stash_swept_files(command, cwd)
        if swept:
            shown = ", ".join(swept[:10])
            more = f" (+{len(swept) - 10} more)" if len(swept) > 10 else ""
            return f"{hit} - files currently at risk: {shown}{more}"
    return hit


CORE_CHECKS = (
    match_rm_rf,
    match_remove_item,
    match_device_write,
    match_mkfs_dd,
    match_disk_wipe_win,
    match_sql_drop,
    match_sql_truncate,
    match_chmod_777,
    match_publish_no_dryrun,
    match_pipe_to_shell,
    match_git_push_force,
)

MIDDLE_CHECKS = (
    match_git_reset_hard,
    match_git_clean_force,
    match_sql_delete_no_where,
    match_diskpart,
    match_disk_doctor_delete,
)


def check_core(command: str):
    for check in CORE_CHECKS:
        result = check(command)
        if result:
            return result
    return None


def check_middle(command: str):
    for check in MIDDLE_CHECKS:
        result = check(command)
        if result:
            return result
    return None


def resolve_profile() -> str:
    raw = os.environ.get("CLAUDE_HOOK_PROFILE", "standard")
    if raw not in PROFILES:
        sys.stderr.write(f"[destructive-command-guard] unrecognised CLAUDE_HOOK_PROFILE={raw!r}, defaulting to standard\n")
        return "standard"
    return raw


def deny(reason: str) -> None:
    _lib_deny(f"[destructive-command-guard] {reason}.{OVERRIDE_HINT}")


def main() -> None:
    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    payload = read_payload()
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        sys.exit(0)

    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    core_hit = check_core(command)
    if core_hit:
        deny(core_hit)

    middle_hit = check_middle(command)
    if middle_hit:
        profile = resolve_profile()
        if profile == "strict":
            deny(middle_hit)
        elif profile == "standard":
            _lib_ask(f"[destructive-command-guard] {middle_hit}.{OVERRIDE_HINT}")

    shared_hit = match_shared_checkout_hit(command, payload.get("cwd") or "", payload.get("session_id") or "")
    if shared_hit:
        profile = resolve_profile()
        if profile == "strict":
            deny(shared_hit)
        elif profile == "standard":
            _lib_ask(f"[destructive-command-guard] {shared_hit}.{OVERRIDE_HINT}")

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[destructive-command-guard] hook error, failing open: {e}\n")
        sys.exit(0)
