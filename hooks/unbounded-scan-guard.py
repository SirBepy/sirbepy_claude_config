"""PreToolUse hook: deny a recursive filesystem scan rooted at a drive root or
the home directory.

Incident, 2026-10-06 (mc_plugins_tag): two subagents ran
`find / -iname ConsoleCommandSenderMock*.class ...` and
`find / -ipath *phosphor* -iname *.css`. Both kept scanning the whole drive
for over an hour after their subagents finished, and killing them needed
Joe's explicit approval. refs/builder-preamble.md already forbade it in
prose and every dispatch carried the line.

Covered: `find` whose starting point is a root, `grep -r`/`--recursive` and
`rg` with a root path argument, and `Get-ChildItem`/`gci`/`dir`/`ls` with
`-Recurse` (or `ls -R`) from a root, unless `-maxdepth`/`-Depth` bounds it. A root is a
drive root (`/`, `C:/`, `C:\\`, `/c`, `/mnt/c`), `~`, `$HOME`,
`$env:USERPROFILE`, `%USERPROFILE%`, or the expanded home path itself; any
subdirectory of those passes, so `~/.gradle/caches` stays allowed.

Only command position counts: the command is split into statements and
pipeline segments outside quotes, and heredoc / here-string bodies are
dropped first, so a root path quoted in a commit message or in test data
never matches. A scan wrapped inside `bash -c "..."` is not seen; that is
the accepted gap for staying out of quoted text. Fails open on any hook
error so a bug here can never block shell work.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, tokenize_segment, basename, split_command_segments as split_segments
except Exception as e:
    sys.stderr.write(f"[unbounded-scan-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

_DRIVE_RE = re.compile(r"^(?:[a-z]:|/[a-z]|/mnt/[a-z])$")

_HOME = os.path.expanduser("~").replace("\\", "/").rstrip("/").lower()
_HOME_ALIASES = {"~", "$home", "${home}", "$env:userprofile", "${env:userprofile}", "%userprofile%"}
if re.match(r"^[a-z]:/", _HOME):
    _HOME_ALIASES |= {_HOME, "/" + _HOME[0] + _HOME[2:], "/mnt/" + _HOME[0] + _HOME[2:]}
elif _HOME:
    _HOME_ALIASES.add(_HOME)

_WRAPPERS = {"sudo", "time", "nice", "command", "exec", "nohup"}
_GREP_NAMES = {"grep", "egrep", "fgrep"}
_GREP_VALUE_FLAGS = {"-e", "-f", "-m", "-a", "-b", "-c", "--regexp", "--file", "--max-count",
                     "--after-context", "--before-context", "--context", "--include", "--exclude",
                     "--exclude-dir", "--label"}
_GREP_PATTERN_FLAGS = {"-e", "-f", "--regexp", "--file"}
_RG_VALUE_FLAGS = {"-e", "-f", "-g", "--glob", "--iglob", "-t", "--type", "-T", "--type-not", "-m",
                   "--max-count", "-A", "-B", "-C", "--context", "-M", "--max-columns", "-d",
                   "--max-depth", "-j", "--threads", "--type-add", "--max-filesize", "-E",
                   "--encoding", "--sort", "--sortr", "--color", "--colors", "-r", "--replace"}
_RG_PATTERN_FLAGS = {"-e", "-f", "--regexp", "--file", "--files"}
_LIST_NAMES = {"get-childitem", "gci", "dir", "ls"}
_LIST_PATH_PARAMS = {"-path", "-literalpath", "-lp"}
_LIST_VALUE_PARAMS = {"-filter", "-include", "-exclude", "-attributes"}


def is_root(tok: str) -> bool:
    t = tok.strip().strip("\"'").replace("\\", "/")
    if t in ("/", "//"):
        return True
    t = t.rstrip("/").lower()
    return bool(_DRIVE_RE.match(t)) or t in _HOME_ALIASES


def _positionals(args: list[str], value_flags: set[str]) -> list[str]:
    out, skip, opts_done = [], False, False
    for a in args:
        if skip:
            skip = False
            continue
        if not opts_done and a == "--":
            opts_done = True
            continue
        if not opts_done and a.startswith("-") and len(a) > 1:
            if a in value_flags:
                skip = True
            continue
        out.append(a)
    return out


def _find_root(args: list[str]) -> str | None:
    if "-maxdepth" in args:
        return None
    i = 0
    while i < len(args) and re.match(r"^-(?:[HLP]|O\d*)$", args[i]):
        i += 1
    for a in args[i:]:
        if a.startswith("-") or a in ("(", "!", ","):
            break
        if is_root(a):
            return a
    return None


def _grep_root(args: list[str]) -> str | None:
    recursive = any(
        a in ("-r", "-R", "--recursive", "--dereference-recursive")
        or (re.match(r"^-[A-Za-z]+$", a) and re.search(r"[rR]", a))
        for a in args
    )
    if not recursive:
        return None
    paths = _positionals(args, _GREP_VALUE_FLAGS)
    if not any(a in _GREP_PATTERN_FLAGS or a.startswith("--regexp=") for a in args):
        paths = paths[1:]
    return next((p for p in paths if is_root(p)), None)


def _rg_root(args: list[str]) -> str | None:
    paths = _positionals(args, _RG_VALUE_FLAGS)
    if not any(a in _RG_PATTERN_FLAGS or a.startswith("--regexp=") for a in args):
        paths = paths[1:]
    return next((p for p in paths if is_root(p)), None)


def _list_root(args: list[str]) -> str | None:
    lower = [a.lower() for a in args]
    recursive = any(a.startswith("-rec") or a == "-r" for a in lower) or any(
        re.match(r"^-[A-Za-z]*R[A-Za-z]*$", a) for a in args
    )
    if not recursive or any(a.startswith("-depth") for a in lower):
        return None
    candidates, pending = [], None
    for a, al in zip(args, lower):
        if pending == "path":
            candidates.append(a)
        if pending:
            pending = None
            continue
        if al in _LIST_PATH_PARAMS:
            pending = "path"
        elif al in _LIST_VALUE_PARAMS:
            pending = "value"
        elif not al.startswith("-"):
            candidates.append(a)
    return next((c for c in candidates if is_root(c)), None)


def find_unbounded_scan(command: str) -> tuple[str, str] | None:
    """(command name, root) for the first rooted recursive scan at command
    position, or None."""
    for seg in split_segments(command):
        tokens = tokenize_segment(seg)
        while tokens and ("=" in tokens[0] and not tokens[0].startswith("-") or tokens[0] in _WRAPPERS):
            tokens = tokens[1:]
        if not tokens:
            continue
        name = basename(tokens[0])
        if name.endswith(".exe"):
            name = name[:-4]
        args = tokens[1:]
        root = None
        if name == "find":
            root = _find_root(args)
        elif name in _GREP_NAMES:
            root = _grep_root(args)
        elif name == "rg":
            root = _rg_root(args)
        elif name in _LIST_NAMES:
            root = _list_root(args)
        if root:
            return name, root
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    hit = find_unbounded_scan(command)
    if hit:
        name, root = hit
        deny(
            "[unbounded-scan-guard] `%s` scans recursively from `%s`, the whole drive or home "
            "directory. Scope it to the narrowest known path instead (the repo root, a cache dir "
            "such as ~/.gradle/caches or the pub cache, a node_modules). An unbounded scan from "
            "a subagent has outlived its caller by over an hour (2026-10-06)." % (name, root)
        )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[unbounded-scan-guard] hook error, failing open: {e}\n")
        sys.exit(0)
