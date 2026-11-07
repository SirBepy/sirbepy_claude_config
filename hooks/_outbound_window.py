"""Night-window check for outbound tracker and PR writes, shared by
`outbound-verify-guard.py` and `shortcut-create-guard.py`.

Joe, 2026-10-22, at about 03:00: "i dont wanna create a ticket at 3am". The client
repos' 23:00-10:59 commit/push window (`commit-window-guard.py`) therefore also covers the
tickets and PR comments Claude itself posts: from a session whose cwd sits in a client repo
(`refs/client-repos.txt`), a create, a text edit or a comment is denied inside the window
unless Joe approved it in this session. Personal repos are never gated.

The window hours, the clock and the allow files are `commit-window-guard.py`'s own, loaded
from it so there is one definition. The allow is a separate SCOPE of those files: a yes to
a commit does not post a ticket. Joe's yes is recorded with, in its own tool call:
  python commit-window-guard.py allow <repo> --scope outbound --reason "<Joe's answer>"

Fails open on any error, like the commit window: a bug here must never block every ticket.
"""

import importlib.util
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _hooklib import git_repo_root
from _client_repo import client_slug

OUTBOUND_SCOPE = "outbound"

_commit_window = None


def commit_window():
    """The `commit-window-guard.py` module, loaded once (its filename has a hyphen)."""
    global _commit_window
    if _commit_window is None:
        spec = importlib.util.spec_from_file_location("_commit_window_guard", _HOOKS_DIR / "commit-window-guard.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _commit_window = mod
    return _commit_window


def window_denial(payload: dict, what: str) -> str | None:
    """The deny message when `what` (e.g. "Shortcut REST write") is an outbound write made
    from a client-repo session inside the night window without an approval, else None."""
    try:
        cw = commit_window()
        root = git_repo_root(payload.get("cwd") or "")
        if not root or not client_slug(root):
            return None
        now = cw.now_fn()
        if not cw.in_window(now):
            return None
        if cw.is_allowed(payload.get("session_id") or "", root, now, scope=OUTBOUND_SCOPE):
            return None
        wake = cw.window_end(now).strftime("%Y-%m-%dT%H:%M")
        allow_cmd = (
            f"python C:/Users/tecno/.claude/hooks/commit-window-guard.py allow \"{root}\" "
            "--scope outbound --reason \"<Joe's answer, quoted>\""
        )
        return (
            f"[outbound-window] {what} blocked: {Path(root).name} is a client repo and it is {now:%H:%M} "
            "local, inside Joe's 23:00-10:59 window for tickets, PR comments and other posts Claude "
            "makes; no part of this call ran. If Joe is around, ask him through the ask_user_question "
            "card whether to post now; only on a yes, run this in its OWN tool call (the hook reads the "
            f"whole command before any of it runs), then retry: {allow_cmd}. If he is not around, do "
            "not post: verify the text now, write the body file, and schedule a one-shot wake-up for "
            f"{wake} (Conductor schedule tool: action add, target this_chat, at {wake}; its prompt names "
            "the body file and the verified text). See skills/ticket/SKILL.md, section Night window."
        )
    except Exception as e:
        sys.stderr.write(f"[outbound-window] hook error, failing open: {e}\n")
        return None
