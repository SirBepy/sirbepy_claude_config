"""PreToolUse gate: no commit and no push in a client repo between 23:00 and
10:59 local machine time, unless Joe approved it in this session.

Joe, 2026-10-06: "unless you got my permission, dont commit or push anything
between 11PM and 11AM, it doesnt look good on me if i work around midnight".
Client repos are exactly refs/client-repos.txt (hooks/_client_repo.py);
personal repos, ~/.claude included, are never gated here.

What counts as landing, per shell-visible invocation (Bash and PowerShell):
- `git <sub>` for every sub in LANDING_SUBCOMMANDS, walking past global
  flags the way push-gate.py does, so `git -C <repo> commit` is gated
  against <repo>, not the payload cwd. `--abort`/`--quit` never land a
  commit and always pass, so a half-done rebase can still be backed out.
- `/commit`'s commit-pathspec.sh (its -C/--repo) and `split-hunks.py commit`
  (its --repo), whose own git calls run in a child process this hook never
  sees.
- A `cd`/Set-Location earlier in the same command pins the cwd for every
  later segment, same rule as push-gate.py.

Timestamps stay real. In a client repo, `--date` and GIT_AUTHOR_DATE /
GIT_COMMITTER_DATE are refused outright inside the window (an approved
night commit still carries its real time), and outside it whenever the
value lands inside the window or has no readable HH:MM - unless an allow
marker exists, which is how a `/commit fold` replaying a commit that really
was made at night gets through. The hour is read off the value literally,
in whatever offset it was written.

Override, only after Joe says yes through the ask_user_question card, in
its own tool call (the hook reads the whole command before any of it runs,
so a chained allow never exists in time):
  python commit-window-guard.py allow <repo> --reason "<Joe's answer, quoted>"
An allow covers that repo for that session for ALLOW_TTL_SECONDS, never past
the end of the current window. Session id comes from $CLAUDE_CODE_SESSION_ID
(or --session).

Fails open on any hook error, same as push-gate.py: a bug here must never
block every commit everywhere.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import sys
from datetime import datetime, timedelta
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, git_repo_root, strip_quotes, basename
    from _client_repo import client_slug
except Exception as e:
    sys.stderr.write(f"[commit-window] hook error, failing open: cannot import helpers ({e})\n")
    sys.exit(0)

WINDOW_START_HOUR = 23
WINDOW_END_HOUR = 11
ALLOW_TTL_SECONDS = 2 * 60 * 60
ALLOW_DIR = _HOOKS_DIR / ".commit-window-ok"

LANDING_SUBCOMMANDS = {"commit", "commit-tree", "merge", "cherry-pick", "revert", "rebase", "am", "push"}
NON_LANDING_FLAGS = {"--abort", "--quit"}
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
GIT_NAMES = {"git", "git.exe"}
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")
ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/)")
ENV_DATE_RE = re.compile(r"GIT_(?:AUTHOR|COMMITTER)_DATE\s*=\s*(\"[^\"]*\"|'[^']*'|[^\s;&|]+)")
DATE_FLAG_RE = re.compile(r"(?<![\w-])--date(?:=|\s+)(\"[^\"]*\"|'[^']*'|[^\s;&|]+)")
HHMM_RE =re.compile(r"(?<!\d)(\d{1,2}):(\d{2})")
EPOCH_RE = re.compile(r"^@(\d+)")
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
# A token after one of these is itself a command line (`bash -c "git commit
# ..."`), so it gets scanned too; a quoted commit message or PR body never does.
INLINE_COMMAND_FLAGS = {"-c", "-lc", "-command", "/c"}

# Swapped out by the tests to pin the clock.
now_fn = datetime.now


def _load_pinned_cd():
    spec = importlib.util.spec_from_file_location("push_gate", _HOOKS_DIR / "push-gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._pinned_cd


_pinned_cd = _load_pinned_cd()


def in_window_hour(hour: int) -> bool:
    return hour >= WINDOW_START_HOUR or hour < WINDOW_END_HOUR


def in_window(now: datetime) -> bool:
    return in_window_hour(now.hour)


def window_end(now: datetime) -> datetime:
    """The 11:00 that ends the window `now` sits in (or the next one, from
    outside the window)."""
    end = now.replace(hour=WINDOW_END_HOUR, minute=0, second=0, microsecond=0)
    return end if now < end else end + timedelta(days=1)


def _tokenize(segment: str) -> list[str]:
    # Never an empty list on unbalanced quotes: that would let a commit slip
    # past unseen (same reasoning as _hooklib.tokenize_segment).
    try:
        return [strip_quotes(t) for t in shlex.split(segment, posix=False)]
    except ValueError:
        return segment.split()


def _value_after(tokens: list[str], names: set[str]) -> str | None:
    for i, tok in enumerate(tokens):
        if tok in names and i + 1 < len(tokens):
            return tokens[i + 1]
        for name in names:
            if name.startswith("--") and tok.startswith(name + "="):
                return tok.split("=", 1)[1]
    return None


def _segment_landings(tokens: list[str]) -> list[tuple[str, str | None, list[str]]]:
    """(kind, explicit_repo_or_None, args) for each landing invocation in one
    segment's tokens."""
    found = []
    for i, tok in enumerate(tokens):
        name = basename(tok)
        if name in GIT_NAMES:
            j = i + 1
            dash_c = None
            while j < len(tokens) and tokens[j].startswith("-"):
                if tokens[j] == "-C" and j + 1 < len(tokens):
                    dash_c = tokens[j + 1]
                    j += 2
                elif tokens[j] in VALUE_FLAGS and "=" not in tokens[j]:
                    j += 2
                else:
                    j += 1
            if j < len(tokens) and tokens[j] in LANDING_SUBCOMMANDS:
                args = tokens[j + 1:]
                if not NON_LANDING_FLAGS.intersection(args):
                    found.append((tokens[j], dash_c, args))
        elif name == "commit-pathspec.sh":
            args = tokens[i + 1:]
            found.append(("commit-pathspec", _value_after(args, {"-C", "--repo"}), args))
        elif name == "split-hunks.py" and "commit" in tokens[i + 1:]:
            args = tokens[i + 1:]
            found.append(("split-hunks", _value_after(args, {"--repo"}), args))
    return found


def landing_targets(command: str, payload_cwd: str) -> list[tuple[str, str, list[str]]]:
    """(kind, effective_path, args) for every commit/push-landing invocation
    in `command`. A quoted token holding its own command (`bash -c "git
    commit ..."`) is scanned one level deep too."""
    effective_cwd = payload_cwd or "."
    targets = []
    for segment in CHAIN_SPLIT_RE.split(command or ""):
        tokens = _tokenize(segment)
        if not tokens:
            continue
        landings = _segment_landings(tokens)
        for prev, tok in zip(tokens, tokens[1:]):
            if prev.lower() in INLINE_COMMAND_FLAGS:
                for inner in CHAIN_SPLIT_RE.split(tok):
                    landings += _segment_landings(_tokenize(inner))
        for kind, repo, args in landings:
            path = repo or effective_cwd
            if repo and not ABS_PATH_RE.match(repo):
                path = os.path.join(effective_cwd, repo)
            targets.append((kind, path, args))
        cd_pin = _pinned_cd(tokens)
        if cd_pin:
            effective_cwd = cd_pin
    return targets


def date_overrides(command: str, targets) -> list[str]:
    # Regex over the raw command, not tokens: posix=False splits
    # `--date="2026-10-06 14:30:00"` at the space inside the quotes.
    values = [strip_quotes(m.group(1)) for m in ENV_DATE_RE.finditer(command or "")]
    if any(kind == "commit" for kind, _path, _args in targets):
        values += [strip_quotes(m.group(1)) for m in DATE_FLAG_RE.finditer(command or "")]
    return values


def override_hour(value: str) -> int | None:
    """Hour a date override would stamp, read literally off the value, or
    None when it has no readable time (relative dates like "yesterday")."""
    epoch = EPOCH_RE.match(value.strip())
    if epoch:
        return datetime.fromtimestamp(int(epoch.group(1))).hour
    m = HHMM_RE.search(value)
    if m and int(m.group(1)) < 24:
        return int(m.group(1))
    return None


def _repo_key(root: str) -> str:
    norm = os.path.normcase(os.path.normpath(root))
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def allow_path(session_id: str, root: str) -> Path:
    return ALLOW_DIR / f"{session_id}--{_repo_key(root)}"


def is_allowed(session_id: str, root: str, now: datetime) -> bool:
    if not session_id or not _SAFE_SESSION_ID_RE.match(session_id):
        return False
    try:
        data = json.loads(allow_path(session_id, root).read_text(encoding="utf-8"))
        return float(data["expires"]) > now.timestamp()
    except (OSError, ValueError, KeyError, TypeError):
        return False


def grant(session_id: str, root: str, reason: str, now: datetime) -> datetime:
    expires = min(now + timedelta(seconds=ALLOW_TTL_SECONDS), window_end(now)) if in_window(now) else now + timedelta(seconds=ALLOW_TTL_SECONDS)
    ALLOW_DIR.mkdir(parents=True, exist_ok=True)
    for old in ALLOW_DIR.glob("*"):
        try:
            if float(json.loads(old.read_text(encoding="utf-8"))["expires"]) <= now.timestamp():
                old.unlink()
        except (OSError, ValueError, KeyError, TypeError):
            pass
    allow_path(session_id, root).write_text(json.dumps({
        "repo": root,
        "reason": reason,
        "granted": now.isoformat(timespec="seconds"),
        "expires": expires.timestamp(),
    }), encoding="utf-8")
    return expires


def _allow_cmd(root: str) -> str:
    return f"python C:/Users/tecno/.claude/hooks/commit-window-guard.py allow \"{root}\" --reason \"<Joe's answer, quoted>\""


def _window_reason(root: str, now: datetime) -> str:
    wake = window_end(now).strftime("%Y-%m-%dT%H:%M")
    return (
        f"[commit-window] {Path(root).name} is a client repo and it is {now:%H:%M} local, inside Joe's "
        "23:00-10:59 no-commit/no-push window; no part of this call ran. Never shift timestamps to dodge it "
        "(no --date, no GIT_AUTHOR_DATE/GIT_COMMITTER_DATE). If Joe is around, ask him through the "
        "ask_user_question card whether to commit/push now; only on a yes, run this in its OWN tool call, "
        f"then retry: {_allow_cmd(root)}. If he is not around (overnight/unattended), leave the changes "
        f"uncommitted, schedule a one-shot wake-up for {wake} (Conductor schedule tool: action add, "
        f"target this_chat, at {wake}; its prompt must name the repo, the exact files and the commit "
        "message), and at that time re-run /commit by pathspec with fresh checks - never trust the index "
        "to have survived the wait. A push still needs Joe's OK after 11:00."
    )


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    targets = landing_targets(command, payload.get("cwd") or "")
    if not targets:
        sys.exit(0)

    now = now_fn()
    session_id = payload.get("session_id") or ""
    overrides = date_overrides(command, targets)
    checked = set()
    for _kind, path, _args in targets:
        root = git_repo_root(path)
        if not root or root in checked:
            continue
        checked.add(root)
        if not client_slug(root):
            continue
        name = Path(root).name

        if overrides and in_window(now):
            deny(
                f"[commit-window] {name} is a client repo: a commit timestamp override "
                f"({', '.join(overrides)}) is refused inside the 23:00-10:59 window, approved or not - "
                "commit timestamps always stay real. Drop the override."
            )
        if overrides and not is_allowed(session_id, root, now):
            hours = [override_hour(v) for v in overrides]
            if any(h is None or in_window_hour(h) for h in hours):
                deny(
                    f"[commit-window] {name} is a client repo: timestamp override ({', '.join(overrides)}) "
                    "lands inside the 23:00-10:59 window or has no readable HH:MM. Commit timestamps stay "
                    "real. The one legitimate case is /commit fold replaying a commit that really was made "
                    "at night: ask Joe through ask_user_question, and only on a yes run in its own tool "
                    f"call: {_allow_cmd(root)}"
                )

        if in_window(now) and not is_allowed(session_id, root, now):
            reason = _window_reason(root, now)
            if "commit-window-guard.py allow" in command:
                reason += (
                    " This command already chains the allow call: the hook reads the whole command "
                    "before any of it runs, so run the allow in its own tool call first."
                )
            deny(reason)
    sys.exit(0)


def cli(argv) -> int:
    parser = argparse.ArgumentParser(prog="commit-window-guard.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_allow = sub.add_parser("allow")
    p_allow.add_argument("path", nargs="?", default=".")
    p_allow.add_argument("--reason", required=True)
    p_allow.add_argument("--session", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
    args = parser.parse_args(argv)

    if not args.reason.strip():
        print("ERROR: --reason must quote Joe's approval", file=sys.stderr)
        return 2
    if not args.session or not _SAFE_SESSION_ID_RE.match(args.session):
        print("ERROR: no usable session id ($CLAUDE_CODE_SESSION_ID unset); pass --session", file=sys.stderr)
        return 2
    root = git_repo_root(args.path)
    if not root:
        print(f"ERROR: {args.path} is not inside a git repo", file=sys.stderr)
        return 2
    if not client_slug(root):
        print(f"{Path(root).name} is a personal repo; the commit window does not apply, nothing written")
        return 0
    expires = grant(args.session, root, args.reason, now_fn())
    print(f"commit window opened for {Path(root).name} (this session) until {expires:%Y-%m-%d %H:%M}: {args.reason}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[commit-window] hook error, failing open: {e}\n")
        sys.exit(0)
