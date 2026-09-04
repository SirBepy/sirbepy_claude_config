"""Filesystem and device destructive matching (todo 911 split): rm -rf,
Remove-Item, raw /dev writes, mkfs/dd, Windows disk wipe, chmod 777.
"""

import re

from _destructive_guard_shared import verb_segments

HOME_TARGETS = r"(~|\$HOME|\$env:USERPROFILE|%USERPROFILE%|\$env:HOME)"
DRIVE_ROOT = r"[A-Za-z]:[\\/]?"

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
