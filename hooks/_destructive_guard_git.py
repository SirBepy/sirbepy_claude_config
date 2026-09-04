"""Git force/reset/stash matching (todo 911 split): push --force, reset
--hard, clean -f, plus the two SHARED-tier pattern matchers (todo 797/775)
whose peer gating (is_main_checkout/fetch_peer_count) lives in
_destructive_guard_peers.py and whose dispatch (match_shared_checkout_hit)
stays in the entry file - see that file's own note on why.
"""

import re

from _destructive_guard_shared import GIT_STASH_ANCHOR_RE, GIT_STASH_SAFE_SUBCMD_RE, verb_segments

GIT_PUSH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*push\b")
GIT_RESET_HARD_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*reset\b[^\n]*--hard\b")
GIT_CLEAN_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*clean\b")

# todo 797: reset/rebase/checkout act on HEAD directly, so any positional ref
# is in scope; branch only moves an EXISTING branch (destructive) under -f.
GIT_RESET_REBASE_CHECKOUT_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*(reset|rebase|checkout)\b", re.IGNORECASE)
GIT_BRANCH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*branch\b", re.IGNORECASE)
POSITIONAL_REF_RE = re.compile(r"(?:^|[\s=])(?:HEAD|@)(?:~\d*|\^+\d*)")

FORCE_LEASE_RE = re.compile(r"--force-with-lease\b")
FORCE_LONG_RE = re.compile(r"--force\b")
FORCE_SHORT_BUNDLE_RE = re.compile(r"(?<![\w-])-[a-zA-Z]*f[a-zA-Z]*\b")


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


def match_git_positional_ref(command: str):
    """Pure pattern hit, independent of shared-checkout status - the entry
    file's match_shared_checkout_hit() is what gates this on
    is_main_checkout()/peer count, so this alone is never enough to ask or deny.
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
    contract as match_git_positional_ref, gated in the entry file.
    """
    for seg in verb_segments(command):
        if GIT_STASH_SAFE_SUBCMD_RE.match(seg):
            continue
        if GIT_STASH_ANCHOR_RE.match(seg):
            return ("git stash push/save reads the whole working tree by pathspec and can "
                    "sweep a peer session's uncommitted work off disk in a shared checkout")
    return None
