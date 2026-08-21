"""PreToolUse hook: ask before Write/Edit/MultiEdit/NotebookEdit touches a
credential file, a lockfile, this repo's own hook/settings wiring, or
anything under .git/. All four rules `ask`, never `deny` - todo 420
measured 22 legitimate .env.local writes and 3 lockfile writes that a hard
block would have eaten. The hook-self-protection case is the novel one: an
agent that can edit its own guards has no guards. Fails open on any error.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, ask
except Exception as e:
    sys.stderr.write(f"[sensitive-file-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

# .env.example is deliberately excluded below via an explicit basename check,
# not a regex negative-lookahead, so this stays plain-ERE-portable.
CRED_BASENAME_RE = re.compile(
    r"^(\.env(\..*)?|.*\.pem|.*\.key|.*\.p12|.*\.pfx|id_rsa|id_ed25519|credentials\.json|\.npmrc|\.pypirc)$",
    re.IGNORECASE,
)
LOCKFILE_RE = re.compile(
    r"^(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|poetry\.lock|pubspec\.lock|Gemfile\.lock)$",
    re.IGNORECASE,
)
# Checked against the backslash-normalized path built in check() below.
HOOKS_DIR_RE = re.compile(r"/\.claude/hooks/", re.IGNORECASE)
SETTINGS_RE = re.compile(r"(^|[\\/])settings(\.local)?\.json$", re.IGNORECASE)
GIT_DIR_RE = re.compile(r"(^|[\\/])\.git([\\/]|$)")


def check(path_str: str) -> list:
    reasons = []
    normalized = path_str.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1]

    if base.lower() != ".env.example" and CRED_BASENAME_RE.match(base):
        reasons.append(f"{base} matches a credential-file pattern (.env.example is deliberately excluded).")
    if LOCKFILE_RE.match(base):
        reasons.append(f"{base} is a lockfile - regenerate it through the package manager, never hand-edit.")
    if HOOKS_DIR_RE.search(normalized) or SETTINGS_RE.search(normalized):
        reasons.append("this is a hook/settings file - an agent that can edit its own guards has no guards.")
    if GIT_DIR_RE.search(normalized):
        reasons.append("this is inside .git/ - use a git command, not a file write.")
    return reasons


def main() -> None:
    payload = read_payload()
    tool_input = payload.get("tool_input") or {}
    path_str = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path_str:
        sys.exit(0)

    reasons = check(path_str)
    if reasons:
        ask(f"[sensitive-file-guard] {path_str}: " + " ".join(reasons))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[sensitive-file-guard] hook error, failing open: {e}\n")
        sys.exit(0)
