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
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny as _lib_deny, ask as _lib_ask
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

HOME_TARGETS = r"(~|\$HOME|\$env:USERPROFILE|%USERPROFILE%|\$env:HOME)"
DRIVE_ROOT = r"[A-Za-z]:[\\/]?"

# Statement split (no pipe): used only where a pipe must stay intact, i.e.
# pipe_to_shell (the pipe IS the thing being matched) and the SQL rules
# (piping SQL output elsewhere doesn't change whether the SQL itself ran).
STATEMENT_SPLIT_RE = re.compile(r"&&|\|\||;")
# Segment split (pipe included): used by every verb-anchored rule below, so
# a verb after a pipe is still checked as its own command position. Newlines
# split too: a multi-line PowerShell script has no && between statements.
SEGMENT_SPLIT_RE = re.compile(r"\|\||&&|[;|\n]")
LEADING_SUDO_RE = re.compile(r"^sudo\s+", re.IGNORECASE)
LEADING_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+")
# Wrappers that run another command as their argument, so the real verb sits
# behind them: `xargs -I{} rm -rf ~` was ALLOWED before this list existed.
LEADING_WRAPPER_RE = re.compile(
    r"^(xargs(\s+-\S+)*|env|time|nohup|nice(\s+-n\s*-?\d+)?|command|(sh|bash|zsh|dash)\s+-c)\s+",
    re.IGNORECASE,
)
# SQL verbs are matched anywhere in a statement, never at command position, so
# a statement whose own command only EMITS or SEARCHES text is prose, not SQL:
# `git commit -m "REFACTOR: python helper, drop table alias"` was DENIED before
# this exclusion, because `python` satisfied the SQL-context rule.
TEXT_EMITTER_RE = re.compile(
    r"^(git|gh|echo|printf|cat|grep|rg|sed|awk|head|tail|less|more|type|write-host|write-output)\b",
    re.IGNORECASE,
)


def split_statements(command: str) -> list:
    return STATEMENT_SPLIT_RE.split(command)


def split_outside_quotes(command: str) -> list:
    """Split on ; && || | and newline, but only OUTSIDE quoted spans.

    A plain split chops a quoted alternation into fake command positions:
    `grep -E "^(a|mkfs|b)"` became a segment beginning `mkfs` and was denied.
    """
    parts, buf = [], []
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch in (";", "\n"):
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        if ch == "|":
            if command[i:i + 2] == "||":
                i += 2
            else:
                i += 1
            parts.append("".join(buf))
            buf = []
            continue
        if command[i:i + 2] == "&&":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def verb_segments(command: str):
    """Yield each command segment with a leading sudo/env-assignment prefix
    stripped and quote CHARACTERS deleted (not quoted spans masked), so a
    verb regex anchored with ^ matches only a real invocation position and
    `rm -rf "$HOME"` still exposes $HOME to the target pattern.
    """
    for segment in split_outside_quotes(command):
        s = segment.strip()
        while True:
            m = LEADING_SUDO_RE.match(s) or LEADING_ENV_RE.match(s) or LEADING_WRAPPER_RE.match(s)
            if not m:
                break
            s = s[m.end():]
        yield s.replace("'", "").replace('"', "")


def statement_is_prose(statement: str) -> bool:
    """True when the statement's own command position only emits or searches
    text, so SQL words inside it are a message rather than a query.
    """
    s = statement.strip()
    while True:
        m = LEADING_SUDO_RE.match(s) or LEADING_ENV_RE.match(s)
        if not m:
            break
        s = s[m.end():]
    return bool(TEXT_EMITTER_RE.match(s))


RM_RF_ROOT_HOME_RE = re.compile(
    r"^rm\s+(?:-[a-zA-Z]+\s+)*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+"
    r"(?:/\s*$|/\s|/\*|" + HOME_TARGETS + r"|\.\./\.\.|" + DRIVE_ROOT + r"\s*$)"
)
# A bare $VAR target is only "unresolved" (and thus CORE) if no earlier
# segment in the SAME command assigns it - `S=safe/path && rm -rf "$S"` is a
# real, common chain, not an unresolved variable.
RM_RF_VAR_RE = re.compile(
    r"^rm\s+(?:-[a-zA-Z]+\s+)*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\$([A-Za-z_][A-Za-z0-9_]*)"
)
RM_RF_SYSDIR_RE = re.compile(
    r"^rm\s+(?:-[a-zA-Z]+\s+)*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(usr|etc|var|bin|sbin|lib|opt|root|boot)(?:[/\s]|$)"
)
# Anchors the verb and requires -Recurse/-Force somewhere in the segment;
# does NOT itself decide the target, see remove_item_targets() below.
REMOVE_ITEM_ANCHOR_RE = re.compile(
    r"^Remove-Item\b(?=[^\n]*-Recurse)(?=[^\n]*-Force)", re.IGNORECASE
)
REMOVE_ITEM_TARGET_RE = re.compile(r"^(?:" + DRIVE_ROOT + r"|" + HOME_TARGETS + r")$", re.IGNORECASE)
# Flags that consume the NEXT token as their own value, so that token is
# never mistaken for the positional -Path argument (position 0).
REMOVE_ITEM_VALUE_FLAG_RE = re.compile(
    r"^-(Filter|Include|Exclude|Stream|Credential|ErrorAction|ErrorVariable"
    r"|WarningAction|WarningVariable|InformationAction|InformationVariable"
    r"|OutVariable|OutBuffer|PipelineVariable)$",
    re.IGNORECASE,
)
REMOVE_ITEM_PATH_FLAG_RE = re.compile(r"^-(Path|LiteralPath)$", re.IGNORECASE)
DEVICE_WRITE_RE = re.compile(
    r"(?:\d|&)?>{1,2}\s*/dev/(?!null\b|stdout\b|stderr\b|tty\b|zero\b|random\b|urandom\b)\S+"
)
MKFS_DD_RE = re.compile(r"^(mkfs(\.[a-z0-9]+)?\b|dd\s+[^\n]*\b(if|of)=/dev/[a-zA-Z])")
DISK_WIPE_WIN_RE = re.compile(r"^(Clear-Disk|Format-Volume|format\s+[A-Za-z]:)\b", re.IGNORECASE)
CHMOD_777_RE = re.compile(r"^chmod\s+(?:-[a-zA-Z]+\s+)*(0?777|a\+rwx)\b")
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

GIT_PUSH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*push\b")
GIT_RESET_HARD_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*reset\b[^\n]*--hard\b")
GIT_CLEAN_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*clean\b")
PUBLISH_ANCHOR_RE = re.compile(r"^((npm|yarn|pnpm|bun)\s+publish|cargo\s+publish|gem\s+push|twine\s+upload|wally\s+publish)\b")

# todo 797: reset/rebase/checkout act on HEAD directly, so any positional ref
# is in scope; branch only moves an EXISTING branch (destructive) under -f.
GIT_RESET_REBASE_CHECKOUT_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*(reset|rebase|checkout)\b", re.IGNORECASE)
GIT_BRANCH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*branch\b", re.IGNORECASE)
POSITIONAL_REF_RE = re.compile(r"(?:^|[\s=])(?:HEAD|@)(?:~\d*|\^+\d*)")

# todo 775: bare `git stash` defaults to `push`, so only the read/replay
# subcommands are exempt from the shared-checkout sweep check.
GIT_STASH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*stash\b", re.IGNORECASE)
GIT_STASH_SAFE_SUBCMD_RE = re.compile(
    r"^git\s+(?:-[^\s]+\s+)*stash\s+(list|show|pop|apply|drop|clear|branch)\b", re.IGNORECASE)

FORCE_LEASE_RE = re.compile(r"--force-with-lease\b")
FORCE_LONG_RE = re.compile(r"--force\b")
FORCE_SHORT_BUNDLE_RE = re.compile(r"(?<![\w-])-[a-zA-Z]*f[a-zA-Z]*\b")
DRYRUN_RE = re.compile(r"--dry-run\b|(?<!\S)-n(?!\S)")

SQUOTE_RE = re.compile(r"'[^']*'")
DQUOTE_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
PIPE_TO_SHELL_RE = re.compile(
    r"\b(curl|wget|Invoke-WebRequest|iwr)\b[^\n]*\|\s*(?:sudo\s+)?(bash|sh|zsh|ksh|fish|dash)\b",
    re.IGNORECASE,
)

SQL_DROP_RE = re.compile(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", re.IGNORECASE)
SQL_TRUNCATE_RE = re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE)
DELETE_FROM_RE = re.compile(r"\bDELETE\s+FROM\s+[A-Za-z_\"`\[]", re.IGNORECASE)
WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)
# SQL verbs never sit at command position, so anchoring cannot discriminate
# them: require a real client/migration binary or a driver CALL shape in the
# same statement. A bare `-c` flag or the word `python` is NOT enough - that
# denied a `python -c` call whose only SQL was prose in a -Note argument.
SQL_CONTEXT_RE = re.compile(
    r"\b(psql|mysql|mariadb|sqlite3|sqlcmd|mongo|mongosh|clickhouse|cockroach|duckdb"
    r"|alembic|prisma|sequelize|knex|flyway|liquibase)\b"
    r"|\b(execute|executemany|execute_batch|text|query|raw)\s*\(",
    re.IGNORECASE,
)


def mask_quotes(command: str) -> str:
    return DQUOTE_RE.sub("Q", SQUOTE_RE.sub("Q", command))


def match_rm_rf(command: str):
    for seg in verb_segments(command):
        if RM_RF_ROOT_HOME_RE.match(seg):
            return "rm -rf targeting / or a home reference is unrecoverable; scope the path narrowly"
        if RM_RF_SYSDIR_RE.match(seg):
            return "rm -rf targeting a system directory is unrecoverable"
        m = RM_RF_VAR_RE.match(seg)
        if m and not re.search(rf"\b{re.escape(m.group(1))}\s*=", command):
            return "rm -rf targeting an unresolved $VAR is unrecoverable; the hook cannot verify what it expands to"
    return None


def remove_item_targets(segment: str):
    """Tokens actually bound to -Path/-LiteralPath or the positional first
    argument, so a drive-root/home token elsewhere in the segment (a note in
    -ErrorAction's value, a trailing comment) is never mistaken for a target.
    """
    tokens = segment.split()[1:]  # drop the leading Remove-Item verb
    targets = []
    positional_claimed = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if REMOVE_ITEM_PATH_FLAG_RE.match(tok):
            i += 1
            if i < len(tokens):
                targets.extend(tokens[i].split(","))
            positional_claimed = True
        elif REMOVE_ITEM_VALUE_FLAG_RE.match(tok):
            i += 1  # skip this flag's own value
        elif not tok.startswith("-") and not positional_claimed:
            targets.extend(tok.split(","))
            positional_claimed = True
        i += 1
    return targets


def match_remove_item(command: str):
    for seg in verb_segments(command):
        if not REMOVE_ITEM_ANCHOR_RE.match(seg):
            continue
        if any(REMOVE_ITEM_TARGET_RE.match(t) for t in remove_item_targets(seg)):
            return "Remove-Item -Recurse -Force targeting a drive root or home reference is unrecoverable; scope the path narrowly"
    return None


def match_device_write(command: str):
    return "redirecting into a raw /dev device node is unrecoverable" if DEVICE_WRITE_RE.search(command) else None


def match_mkfs_dd(command: str):
    for seg in verb_segments(command):
        if MKFS_DD_RE.match(seg):
            return "mkfs/dd against a raw device node is unrecoverable"
    return None


def match_disk_wipe_win(command: str):
    for seg in verb_segments(command):
        if DISK_WIPE_WIN_RE.match(seg):
            return "Clear-Disk/Format-Volume/format wipes a disk irrecoverably"
    return None


def match_chmod_777(command: str):
    for seg in verb_segments(command):
        if CHMOD_777_RE.match(seg):
            return "chmod 777/a+rwx opens the path to every user; scope permissions narrowly instead"
    return None


def match_sql_drop(command: str):
    for stmt in split_statements(command):
        if SQL_DROP_RE.search(stmt) and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt):
            return "DROP TABLE/DATABASE/SCHEMA is unrecoverable without a separate backup"
    return None


def match_sql_truncate(command: str):
    for stmt in split_statements(command):
        if SQL_TRUNCATE_RE.search(stmt) and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt):
            return "TRUNCATE TABLE is unrecoverable without a separate backup"
    return None


def match_publish_no_dryrun(command: str):
    for seg in verb_segments(command):
        if PUBLISH_ANCHOR_RE.match(seg) and not DRYRUN_RE.search(seg):
            return "package publish with no --dry-run/-n ships to a public registry irreversibly; add --dry-run/-n first"
    return None


def match_pipe_to_shell(command: str):
    if PIPE_TO_SHELL_RE.search(mask_quotes(command)):
        return "piping curl/wget/iwr output straight into a shell interpreter runs unreviewed remote code; download and inspect it first"
    return None


def match_git_push_force(command: str):
    for seg in verb_segments(command):
        m = GIT_PUSH_ANCHOR_RE.match(seg)
        if not m:
            continue
        rest = seg[m.end():]
        if FORCE_LEASE_RE.search(rest):
            continue
        if FORCE_LONG_RE.search(rest) or FORCE_SHORT_BUNDLE_RE.search(rest):
            return "git push --force without --force-with-lease can overwrite remote history irrecoverably if the tip moved; use --force-with-lease instead"
    return None


def match_git_reset_hard(command: str):
    for seg in verb_segments(command):
        if GIT_RESET_HARD_RE.match(seg):
            return "git reset --hard discards uncommitted work irreversibly"
    return None


def match_git_clean_force(command: str):
    for seg in verb_segments(command):
        m = GIT_CLEAN_ANCHOR_RE.match(seg)
        if not m:
            continue
        rest = seg[m.end():]
        if FORCE_SHORT_BUNDLE_RE.search(rest) or FORCE_LONG_RE.search(rest):
            return "git clean -f permanently deletes untracked files"
    return None


def match_sql_delete_no_where(command: str):
    for stmt in split_statements(command):
        if (DELETE_FROM_RE.search(stmt) and not WHERE_RE.search(stmt)
                and SQL_CONTEXT_RE.search(stmt) and not statement_is_prose(stmt)):
            return "DELETE FROM with no WHERE in this statement deletes every row"
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


def match_git_positional_ref(command: str):
    """Pure pattern hit, independent of shared-checkout status - the SHARED
    tier's caller (main()) is what gates this on is_main_checkout()/peer
    count, so this alone is never enough to ask or deny.
    """
    for seg in verb_segments(command):
        if GIT_RESET_REBASE_CHECKOUT_RE.match(seg) and POSITIONAL_REF_RE.search(seg):
            return ("a positional ref (HEAD~n/HEAD^/@~n) is relative and can resolve to a peer "
                    "session's commit the instant they commit here; use the explicit sha from "
                    "`git log -1 --format=%H` instead")
        m = GIT_BRANCH_ANCHOR_RE.match(seg)
        if m:
            rest = seg[m.end():]
            if (FORCE_LONG_RE.search(rest) or FORCE_SHORT_BUNDLE_RE.search(rest)) and POSITIONAL_REF_RE.search(rest):
                return ("git branch -f against a positional ref (HEAD~n/HEAD^/@~n) can move the "
                        "branch onto a peer session's commit here; use the explicit sha from "
                        "`git log -1 --format=%H` instead")
    return None


def match_git_stash_push(command: str):
    """Pure pattern hit, independent of shared-checkout status - same
    contract as match_git_positional_ref, gated by main() below.
    """
    for seg in verb_segments(command):
        if GIT_STASH_SAFE_SUBCMD_RE.match(seg):
            continue
        if GIT_STASH_ANCHOR_RE.match(seg):
            return ("git stash push/save reads the whole working tree by pathspec and can "
                    "sweep a peer session's uncommitted work off disk in a shared checkout")
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


def is_main_checkout(cwd: str) -> bool:
    """True only for a repo's primary worktree. A linked worktree's --git-dir
    sits under <common-dir>/worktrees/<name>, so it never equals --git-common-
    dir the way the main checkout's does; any git failure returns False.
    """
    try:
        common = subprocess.run(["git", "-C", cwd, "rev-parse", "--git-common-dir"],
                                 capture_output=True, text=True, timeout=10)
        gitdir = subprocess.run(["git", "-C", cwd, "rev-parse", "--git-dir"],
                                 capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if common.returncode != 0 or gitdir.returncode != 0:
        return False
    base = Path(cwd)
    try:
        return (base / common.stdout.strip()).resolve() == (base / gitdir.stdout.strip()).resolve()
    except OSError:
        return False


def fetch_peer_count(session_id: str) -> int:
    """Live peers sharing this session's project, via the same Conductor
    daemon endpoint list-peers-pre-edit-guard.py already proved reachable
    (todo 458). Any failure reports 0, matching this file's fail-open
    convention - a false negative here costs one warning, never a block.
    """
    if not session_id:
        return 0
    body = json.dumps({"session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:27182/channel/list-peers",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return 0
    if data.get("ok") is False:
        return 0
    peers = data.get("peers")
    return len(peers) if isinstance(peers, list) else 0


def stash_pathspec_args(seg: str) -> list:
    """Positional args after `git stash [push|save]`, following a literal
    `--` if present. No `--` means "whole tree" (bare stash, or push/save
    with no pathspec restriction) - the conservative reading for a sweep.
    """
    rest = GIT_STASH_ANCHOR_RE.sub("", seg, count=1)
    rest = re.sub(r"^\s*(push|save)\b", "", rest, flags=re.IGNORECASE)
    if "--" not in rest:
        return []
    return [t for t in rest.split("--", 1)[1].split() if t]


def stash_swept_files(command: str, cwd: str) -> list:
    """`git status` scoped to the stash's own pathspec (whole tree if none),
    so the prompt names what a peer's uncommitted edits would look like at
    risk - best-effort, empty on any git failure (todo 775).
    """
    pathspecs = []
    for seg in verb_segments(command):
        if GIT_STASH_SAFE_SUBCMD_RE.match(seg):
            continue
        if GIT_STASH_ANCHOR_RE.match(seg):
            pathspecs = stash_pathspec_args(seg)
            break
    cmd = ["git", "-C", cwd, "status", "--porcelain", "--no-renames"]
    if pathspecs:
        cmd += ["--"] + pathspecs
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [line[3:].strip() for line in proc.stdout.splitlines() if len(line) > 3]


def match_shared_checkout_hit(command: str, cwd: str, session_id: str):
    """Compound SHARED-tier signal: a positional-ref or stash-push pattern
    hit, in the MAIN checkout, with at least one live peer. Any one absent
    means no hit, which is what keeps a worktree or a solo session
    prompt-free (todo 797). A stash hit gets the at-risk file list appended.
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
