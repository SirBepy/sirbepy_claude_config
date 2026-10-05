"""PreToolUse gate: block `git push` in a client repo (refs/client-repos.txt)
until HEAD carries a pushable marker from `_client_repo.py mark`.

The marker is self-attested: Claude writes it after /code-check and /e2e pass,
or after Joe says yes to pushing past a red or impossible check. The gate's job
is making that step impossible to forget, not proving the checks ran.

Keyed by HEAD sha, so any new commit needs a fresh pass. `git push` detection
is push-read-gate.py's own, loaded by path so the two gates never disagree
about what counts as a push.

Fails open on any hook error: a bug here must never block every push.
"""

import importlib.util
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, git_repo_root
    import _client_repo
except Exception as e:
    sys.stderr.write(f"[client-push-gate] hook error, failing open: cannot import helpers ({e})\n")
    sys.exit(0)


def _load_push_detector():
    spec = importlib.util.spec_from_file_location("push_read_gate", _HOOKS_DIR / "push-read-gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_git_push_invocation


def git_dash_c_path(command: str) -> str | None:
    """The `-C <path>` of the first `git ... push` call, if any. posix=False
    keeps Windows backslashes intact; quotes are stripped by hand."""
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        return None
    for i, tok in enumerate(tokens):
        if tok != "git":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] == "-C" and j + 1 < len(tokens):
                return tokens[j + 1].strip("\"'")
            j += 1
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not _load_push_detector()(command):
        sys.exit(0)

    target = git_dash_c_path(command) or payload.get("cwd") or "."
    root = git_repo_root(target)
    if not root:
        sys.exit(0)
    slug = _client_repo.client_slug(root)
    if not slug:
        sys.exit(0)
    sha = _client_repo.head_sha(root)
    if not sha or _client_repo.is_pushable(sha):
        sys.exit(0)

    deny(
        f"[client-push-gate] {slug} is a client repo and HEAD {sha[:7]} has not been "
        "cleared for push. Follow /commit's Push pipeline (skills/commit/SKILL.md) in order; "
        "this hook checks its client gate: /code-check over @{u}..HEAD and /e2e, then: python C:/Users/tecno/.claude/hooks/_client_repo.py mark "
        f"\"{root}\" --reason \"code-check + e2e passed\". If a check cannot pass, ask Joe "
        "through the ask_user_question tool whether to push anyway, and mark with a reason "
        "naming the failure only if he says yes."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[client-push-gate] hook error, failing open: {e}\n")
        sys.exit(0)
