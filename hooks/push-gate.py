"""PreToolUse gate: block `git push` in any repo until HEAD carries a pushable
marker from `push-gate.py mark`.

The marker is self-attested: Claude writes it after /commit's Pre-push gate
(/code-check, then /e2e or its "no suite" note), or after Joe says yes to
pushing past a red or impossible check. The gate's job is making that step
impossible to forget, not proving the checks ran.

Keyed by HEAD sha, so any new commit needs a fresh pass. `git push` detection
is push-read-gate.py's own, loaded by path so the two gates never disagree
about what counts as a push.

Target-repo resolution (todo 1044) walks the command the same way
is_git_push_invocation does, since a naive "first `-C` in the command" or
"payload cwd always" both have a real bypass:
- `git -C <cleared> status && git push` must NOT inherit the first git
  call's `-C` - real git scopes `-C` to its own invocation only, so the
  gate now reads `-C` off the invocation that reaches `push`, never an
  earlier, unrelated one.
- `cd <cleared> && git push` must NOT be checked against the pre-`cd` payload
  cwd - a `cd`/Set-Location segment earlier in the same command pins the
  effective cwd for every segment after it, mirroring
  git-workdir-guard.py's own `pinned_cd` (same bypass, same fix shape).

Fails open on any hook error: a bug here must never block every push.

CLI, for skills and scripts:
  python push-gate.py mark [path] --reason "..."   records HEAD as pushable
"""

import argparse
import importlib.util
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

MARKER_DIR = _HOOKS_DIR / ".push-ok"
GIT_TIMEOUT_SECONDS = 10

try:
    from _hooklib import read_payload, deny, git_repo_root, strip_quotes
except Exception as e:
    sys.stderr.write(f"[push-gate] hook error, failing open: cannot import helpers ({e})\n")
    sys.exit(0)

VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
CD_WORDS = {"cd", "cd.", "chdir", "pushd", "sl", "set-location", "push-location"}
ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/[^/\s])")
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")


def _load_push_detector():
    spec = importlib.util.spec_from_file_location("push_read_gate", _HOOKS_DIR / "push-read-gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_git_push_invocation


def _tokenize_segment(segment: str) -> list[str]:
    try:
        return [strip_quotes(t) for t in shlex.split(segment, posix=False)]
    except ValueError:
        return []


def _pinned_cd(tokens: list[str]) -> str | None:
    """Absolute path of a cd/Set-Location/Push-Location in this segment, if
    any - scans the 3 tokens after the cd-word so a flag in between (e.g.
    `Set-Location -Path X`) doesn't hide the value. Mirrors
    git-workdir-guard.py's pinned_cd exactly; duplicated rather than imported
    since that file is a sibling guard, not a shared library."""
    for i, tok in enumerate(tokens):
        if tok.lower() not in CD_WORDS:
            continue
        for cand in tokens[i + 1 : i + 4]:
            if ABS_PATH_RE.match(cand):
                return cand
    return None


def _git_push_dash_c(tokens: list[str]) -> tuple[bool, str | None]:
    """(is_push, dash_c_value) for one segment's tokens: walks past global git
    flags the same way is_git_push_invocation does, but also remembers a `-C`
    value seen along the way - and only returns it when THIS walk's git
    invocation reaches `push`, so an earlier, unrelated `git -C X status` in
    the same chained command is never mistaken for the push's own `-C`."""
    for i, tok in enumerate(tokens):
        if tok != "git":
            continue
        j = i + 1
        dash_c = None
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] == "-C" and j + 1 < len(tokens):
                dash_c = strip_quotes(tokens[j + 1])
                j += 2
            elif tokens[j] in VALUE_FLAGS and "=" not in tokens[j]:
                j += 2
            else:
                j += 1
        if j < len(tokens) and tokens[j] == "push":
            return True, dash_c
    return False, None


def git_dash_c_path(command: str) -> str | None:
    """The `-C <path>` attached to the specific `git ... push` invocation in
    `command`, if any - never an earlier, unrelated `git -C` call in the same
    chained command. posix=False keeps Windows backslashes intact."""
    for segment in CHAIN_SPLIT_RE.split(command):
        tokens = _tokenize_segment(segment)
        is_push, dash_c = _git_push_dash_c(tokens)
        if is_push:
            return dash_c
    return None


def resolve_push_target(command: str, payload_cwd: str) -> str:
    """The effective repo path for the `git push` in `command`: that push
    invocation's own `-C`, else the path pinned by a `cd`/Set-Location
    segment earlier in the same command, else the shell's live cwd."""
    effective_cwd = payload_cwd or "."
    for segment in CHAIN_SPLIT_RE.split(command):
        tokens = _tokenize_segment(segment)
        if not tokens:
            continue
        is_push, dash_c = _git_push_dash_c(tokens)
        if is_push:
            return dash_c or effective_cwd
        cd_pin = _pinned_cd(tokens)
        if cd_pin:
            effective_cwd = cd_pin
    return effective_cwd


def head_sha(path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def is_pushable(sha: str) -> bool:
    return bool(sha) and (MARKER_DIR / sha).exists()


def mark_pushable(path, reason: str) -> str:
    sha = head_sha(path)
    if not sha:
        raise SystemExit(f"ERROR: {path} has no HEAD commit to mark")
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    (MARKER_DIR / sha).write_text(f"{stamp} {reason}\n", encoding="utf-8")
    return sha


def cli(argv) -> int:
    parser = argparse.ArgumentParser(prog="push-gate.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_mark = sub.add_parser("mark")
    p_mark.add_argument("path", nargs="?", default=".")
    p_mark.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    sha = mark_pushable(args.path, args.reason)
    print(f"marked {sha[:7]} pushable: {args.reason}")
    return 0


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not _load_push_detector()(command):
        sys.exit(0)

    target = resolve_push_target(command, payload.get("cwd") or "")
    root = git_repo_root(target)
    if not root:
        sys.exit(0)
    sha = head_sha(root)
    if not sha or is_pushable(sha):
        sys.exit(0)

    deny(
        f"[push-gate] HEAD {sha[:7]} of {Path(root).name} has not been cleared for push. "
        "Follow /commit's Push pipeline (skills/commit/SKILL.md) in order; this hook checks "
        "its Pre-push gate: /code-check over @{u}..HEAD, then /e2e (or its no-suite rule), then: "
        f"python C:/Users/tecno/.claude/hooks/push-gate.py mark \"{root}\" --reason \"<what passed>\". "
        "If a check cannot pass, ask Joe through the ask_user_question tool whether to push "
        "anyway, and mark with a reason naming the failure only if he says yes."
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[push-gate] hook error, failing open: {e}\n")
        sys.exit(0)
