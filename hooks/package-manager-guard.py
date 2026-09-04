"""PreToolUse hook: block a bare yarn/npm/pnpm mutating call when the nearest
package.json pins a different (or unverified) packageManager.

Fires on every Bash/PowerShell call. Tokenizes the command, finds yarn/npm/
pnpm invocations, and for MUTATING subcommands only (install, add, remove,
up/upgrade, dedupe, ci, plus a bare `yarn` with no subcommand) resolves the
nearest package.json (honouring --cwd/-C/--dir/--prefix) and checks its
packageManager field. If a pin exists and the call is not corepack-prefixed
with the matching manager name, block - corepack is the only invocation that
can be trusted to fetch the exact pinned version regardless of what shadows
it on PATH. No package.json, or no packageManager field: allow, silently.

Incident: bare `yarn install` in revaire-server hit a global yarn 1.22.22 on
PATH (repo pins yarn@4.9.3) and silently rewrote yarn.lock to v1 format.
Fails open on any hook error so a bug here can never block package work.
"""

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    # strip_quotes stays imported under its own name (unused locally, no
    # longer than a line) purely to keep test_package_manager_guard.py's
    # todo-501 alias-pin case (guard._lib_strip_quotes) passing.
    from _hooklib import (
        read_payload,
        deny,
        strip_quotes as _lib_strip_quotes,
        tokenize_command as tokenize,
    )
except Exception as e:
    sys.stderr.write(f"[package-manager-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MANAGERS = {"yarn", "npm", "pnpm"}

# Value-consuming flags that redirect the target directory, across managers.
CWD_FLAGS = {"--cwd", "-C", "--dir", "--prefix"}

# Info/diagnostic flags that must never be mistaken for a bare install.
INFO_FLAGS = {"--version", "-v", "--help", "-h"}

# Mutating subcommands per manager (aliases normalized). Read-only commands
# (run, test, why, list, info, dlx, exec, config, outdated) are deliberately
# left uncovered - see report for the scope rationale.
MUTATING = {
    "yarn": {"install", "add", "remove", "up", "upgrade", "dedupe", "import"},
    "npm": {"install", "i", "ci", "add", "uninstall", "remove", "rm", "un", "update", "up", "dedupe"},
    "pnpm": {"install", "i", "add", "remove", "rm", "update", "up", "dedupe", "import"},
}


def find_nearest_package_json(start_dir: Path):
    d = start_dir
    for _ in range(64):
        candidate = d / "package.json"
        if candidate.is_file():
            return candidate
        if d.parent == d:
            return None
        d = d.parent
    return None


def read_package_manager(pkg_json_path: Path):
    try:
        data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pm = data.get("packageManager")
    if not isinstance(pm, str) or "@" not in pm:
        return None
    name, _, version = pm.partition("@")
    return name.strip(), version.strip()


def resolve_cwd_override(tokens, base_cwd: str) -> str:
    """Scan the whole command for a --cwd/-C/--dir/--prefix value, applied
    globally since these hooks see one command per invocation in practice.
    """
    for i, tok in enumerate(tokens):
        if tok in CWD_FLAGS and i + 1 < len(tokens):
            val = tokens[i + 1]
            p = Path(val)
            return str(p if p.is_absolute() else Path(base_cwd) / p)
        for flag in CWD_FLAGS:
            if tok.startswith(flag + "="):
                val = tok[len(flag) + 1:]
                p = Path(val)
                return str(p if p.is_absolute() else Path(base_cwd) / p)
    return base_cwd


def classify_invocation(tokens, idx):
    """Given tokens and the index of a manager token, return
    (subcommand_or_None, is_info_only, corepack_prefixed).
    """
    manager = tokens[idx]
    corepack_prefixed = idx > 0 and tokens[idx - 1] == "corepack"
    rest = tokens[idx + 1:]

    subcommand = None
    saw_info_flag = False
    j = 0
    while j < len(rest):
        tok = rest[j]
        if tok in INFO_FLAGS:
            saw_info_flag = True
            j += 1
            continue
        if tok in CWD_FLAGS:
            j += 2
            continue
        is_cwd_eq = any(tok.startswith(f + "=") for f in CWD_FLAGS)
        if tok.startswith("-") or is_cwd_eq:
            j += 1
            continue
        subcommand = tok.lower()
        break

    return manager, subcommand, saw_info_flag, corepack_prefixed


def is_mutating(manager: str, subcommand, info_only: bool) -> bool:
    if subcommand is not None:
        return subcommand in MUTATING.get(manager, set())
    # Bare invocation: only classic/berry yarn treats no-subcommand as install.
    if manager == "yarn" and not info_only:
        return True
    return False


def main() -> None:
    payload = read_payload()
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command", "") or ""
    base_cwd = payload.get("cwd") or "."

    if not command.strip():
        sys.exit(0)

    tokens = tokenize(command)
    if not tokens:
        sys.exit(0)

    effective_cwd = resolve_cwd_override(tokens, base_cwd)

    for i, tok in enumerate(tokens):
        if tok not in MANAGERS:
            continue
        manager, subcommand, info_only, corepack_prefixed = classify_invocation(tokens, i)
        if not is_mutating(manager, subcommand, info_only):
            continue

        pkg_json = find_nearest_package_json(Path(effective_cwd))
        if pkg_json is None:
            continue
        pinned = read_package_manager(pkg_json)
        if pinned is None:
            continue
        pinned_name, pinned_version = pinned

        if corepack_prefixed and manager == pinned_name:
            continue

        shown_subcommand = subcommand or "install"
        correct = "corepack %s %s" % (pinned_name, shown_subcommand)
        deny(
            "[package-manager-guard] %s pins packageManager \"%s@%s\" in %s - "
            "run \"%s\", not bare \"%s %s\". A shadowing global binary can "
            "silently rewrite the lockfile into the wrong format."
            % (
                pkg_json.parent,
                pinned_name,
                pinned_version,
                pkg_json,
                correct,
                manager,
                shown_subcommand,
            )
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[package-manager-guard] hook error, failing open: {e}\n")
        sys.exit(0)
