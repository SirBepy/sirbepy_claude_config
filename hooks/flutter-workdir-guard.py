"""PreToolUse hook: block destructive Flutter/Dart codegen against an unpinned cwd.

Real incident 2026-07-31: a session driven from zng-app silently kept its
shell cwd there after a Set-Location reset, and `dart run build_runner
build --delete-conflicting-outputs` deleted 8 tracked generated files in
the WRONG repo. Two further bare `flutter analyze`/`flutter test` calls in
that same session produced false "your develop branch is broken" reads.

Scope (deliberately narrow - see report): HARD BLOCK only fires when a
flutter/dart invocation carries `--delete-conflicting-outputs` (the one
flag that deletes files) and has no directory pinned in the SAME command
string. Every other bare flutter/dart call (analyze, test, build, watch
without the delete flag) only WARNS - printed, never blocking - since a
blanket block on ordinary flutter/dart calls would get this hook disabled.

"Pinned" = a `-C`/`--directory`/`--working-directory`/PowerShell
`-WorkingDirectory` flag carrying an absolute path, OR a `cd`/Set-Location/
Push-Location to an absolute path earlier in the SAME command string (chain
operators only - a prior tool call's Set-Location is exactly the failure
mode this guards against, so it never counts).

Override: set CLAUDE_WORKDIR_GUARD_BYPASS=1 to bypass if this hook itself
misfires.

Second, unrelated block (todo 803): `fvm`/`flutter`/`dart` invoked as the
LEADING word of a Bash-tool command is denied outright, distinct from the
pin logic above. `fvm` is missing from Bash's PATH on this machine, so
`fvm flutter analyze` there prints "command not found" and exits 0 - a
silently skipped check. PowerShell commands are untouched.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    # strip_quotes stays imported under its own name (unused locally, no
    # longer than a line) purely to keep test_flutter_workdir_guard.py's
    # todo-501 alias-pin case (guard._lib_strip_quotes) passing.
    from _hooklib import (
        read_payload,
        deny,
        strip_quotes as _lib_strip_quotes,
        tokenize_segment as tokenize,
        basename,
    )
except Exception as e:
    sys.stderr.write(f"[flutter-workdir-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_WORKDIR_GUARD_BYPASS"

RUNNER_BASENAMES = {"flutter", "flutter.bat", "flutter.exe", "dart", "dart.exe", "dart.bat"}
BASH_LEADING_BASENAMES = RUNNER_BASENAMES | {"fvm", "fvm.bat", "fvm.exe"}
FILEPATH_FLAG_TOKENS = {"-filepath", "-file"}
CALL_OPERATOR = "&"
LAUNCHER_BASENAMES = {"fvm", "fvm.bat", "fvm.exe"}
DESTRUCTIVE_FLAG = "--delete-conflicting-outputs"
CD_WORDS = {"cd", "cd.", "chdir", "pushd", "sl", "set-location", "push-location"}
DIR_FLAGS = {"-c", "--directory", "--working-directory", "-workingdirectory"}

# Windows drive-letter (C:\...), UNC (\\server\...), or git-bash style (/c/...).
ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/[^/\s])")
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")


def allow(message: str = "") -> None:
    if message:
        print(message)
    sys.exit(0)


def has_runner(tokens: list[str]) -> bool:
    """True when a flutter/dart basename sits in COMMAND position: index 0, right
    after a Start-Process -FilePath/-File flag, after PowerShell's `&` call
    operator, or after a launcher like fvm. Any other position is an argument,
    not an invocation - `grep -r "flutter" pubspec.yaml` merely contains the word.

    The `&` and fvm forms are not optional extras: `fvm flutter` is the primary
    invocation on this machine, and `& "C:\\tools\\flutter.bat"` is the documented
    way to call an exe path containing spaces. Anchoring to index 0 alone silently
    stopped catching both (todo 908 regression, caught 2026-09-05).
    """
    for i, tok in enumerate(tokens):
        if basename(tok) not in RUNNER_BASENAMES:
            continue
        if i == 0:
            return True
        prev = tokens[i - 1]
        if prev.lower() in FILEPATH_FLAG_TOKENS or prev == CALL_OPERATOR:
            return True
        if basename(prev) in LAUNCHER_BASENAMES:
            return True
    return False


def is_destructive(tokens: list[str]) -> bool:
    lowered = [t.lower() for t in tokens]
    return "build_runner" in lowered and DESTRUCTIVE_FLAG in lowered


def pinned_dir_flag(tokens: list[str]) -> str | None:
    """Return the pinned absolute path if a -C/--directory/--working-directory/
    -WorkingDirectory flag with an absolute value is present, else None.
    """
    for i, tok in enumerate(tokens):
        low = tok.lower()
        if "=" in low and low.split("=", 1)[0] in DIR_FLAGS:
            value = tok.split("=", 1)[1]
        elif low in DIR_FLAGS and i + 1 < len(tokens):
            value = tokens[i + 1]
        else:
            continue
        if ABS_PATH_RE.match(value):
            return value
    return None


def pinned_cd(tokens: list[str]) -> str | None:
    """Return the absolute path of a cd/Set-Location/Push-Location in this
    segment, else None. Scans the 3 tokens after the cd-word so a `-Path`
    flag in between doesn't hide the value.
    """
    for i, tok in enumerate(tokens):
        if tok.lower() not in CD_WORDS:
            continue
        for cand in tokens[i + 1 : i + 4]:
            if ABS_PATH_RE.match(cand):
                return cand
    return None


def is_flutter_project(path: str) -> bool:
    try:
        return os.path.isfile(os.path.join(path, "pubspec.yaml"))
    except OSError:
        return False


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name")
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        allow()
    if os.environ.get(OVERRIDE_ENV):
        allow()

    if tool_name == "Bash":
        for segment in CHAIN_SPLIT_RE.split(command):
            tokens = tokenize(segment)
            if tokens and basename(tokens[0]) in BASH_LEADING_BASENAMES:
                deny(
                    "[flutter-workdir-guard] Blocked: fvm/flutter/dart invoked as the leading "
                    "command through the Bash tool. fvm is missing from Bash's PATH here, so this "
                    "exits 0 having run nothing, and a `| tail`/`| head`/`| grep` on top of it masks "
                    "a real build failure as a false green. Re-run this command through the "
                    f"PowerShell tool instead. Bypass: set {OVERRIDE_ENV}=1."
                )

    segments = CHAIN_SPLIT_RE.split(command)
    prior_pin: str | None = None
    warn_hit = False

    for segment in segments:
        tokens = tokenize(segment)
        if not tokens:
            continue

        if has_runner(tokens):
            pin = pinned_dir_flag(tokens) or prior_pin
            destructive = is_destructive(tokens)

            if destructive and not pin:
                deny(
                    "[flutter-workdir-guard] Blocked: build_runner --delete-conflicting-outputs "
                    "with no directory pinned in this command. A silently-reset cwd has already "
                    "deleted tracked generated files in the wrong repo once (2026-07-31). Pin the "
                    "repo in the SAME invocation, e.g. "
                    "`Start-Process -FilePath dart.bat -ArgumentList 'run','build_runner','build',"
                    "'--delete-conflicting-outputs' -WorkingDirectory <abs repo path> -NoNewWindow -Wait` "
                    "or `dart -C <abs repo path> run build_runner build --delete-conflicting-outputs`. "
                    f"Bypass: set {OVERRIDE_ENV}=1."
                )

            if destructive and pin and not is_flutter_project(pin):
                deny(
                    f"[flutter-workdir-guard] Blocked: pinned directory '{pin}' has no pubspec.yaml "
                    "- looks like a typo'd or non-Flutter path, not a real pin. "
                    f"Bypass: set {OVERRIDE_ENV}=1."
                )

            if not pin:
                warn_hit = True

        cd_pin = pinned_cd(tokens)
        if cd_pin:
            prior_pin = cd_pin

    if warn_hit:
        allow(
            "[flutter-workdir-guard] Warning: flutter/dart call with no directory pinned in this "
            "command. If the shell's cwd silently reset (has happened before), this can run "
            "against, and report on, the wrong repo. Not blocked - just double-check the repo."
        )
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[flutter-workdir-guard] hook error, failing open: {e}\n")
        sys.exit(0)
