"""Self-test for unbounded-scan-guard.py.

Run directly: python hooks/test_unbounded_scan_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

The negatives carry the weight: a scoped scan (repo subdir, a cache dir under
home, a node_modules) must pass, and so must a root path that only appears as
text inside a quoted argument or a heredoc body, or the guard gets switched
off for the same false-positive class destructive-command-guard hit.
"""

import os
import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "unbounded-scan-guard.py"
)

fails = []

HOME = os.path.expanduser("~").replace("\\", "/")


def run_main(command: str) -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "cwd": "."}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


MAIN_CASES = [
    ("find / -name x", 2, "find from / is denied"),
    ("find / -iname 'ConsoleCommandSenderMock*.class' -o -iname 'mockbukkit*.jar'", 2,
     "the 2026-10-06 incident command is denied"),
    ("find /c -name x", 2, "git-bash drive root is denied"),
    ("find C:/ -name x", 2, "drive root with forward slash is denied"),
    ("find C:\\ -name x", 2, "drive root with backslash is denied"),
    ("find ~ -name x", 2, "home tilde is denied"),
    ("find $HOME -name x", 2, "$HOME is denied"),
    (f"find {HOME} -name x", 2, "expanded home path is denied"),
    ("find -L / -name x", 2, "a leading find option does not hide the root"),
    ("cd repo && find / -name x", 2, "a rooted find chained after && is denied"),
    ("grep -r foo /", 2, "grep -r from / is denied"),
    ("grep -rn foo C:/", 2, "combined short flags carrying r are denied"),
    ("grep --recursive foo ~", 2, "--recursive from home is denied"),
    ("rg foo /", 2, "rg from / is denied"),
    ("rg -g '*.css' phosphor C:\\", 2, "rg with a valued flag before the pattern is still denied"),
    ("Get-ChildItem -Path C:\\ -Recurse -Filter *.css", 2, "Get-ChildItem -Recurse from a drive root is denied"),
    ("gci C:/ -Recurse", 2, "gci alias with a positional root is denied"),
    ("find / -maxdepth 1 -name x", 0, "a depth-bounded find from / passes"),
    ("find ./src -name x", 0, "repo-relative find passes"),
    ("find C:/Users/tecno/.gradle/caches -name x", 0, "a cache dir under home passes"),
    ("find . -name node_modules -prune", 0, "find from . passes"),
    ("grep -r foo src/", 0, "grep -r on a repo dir passes"),
    ("grep foo /etc/hosts", 0, "non-recursive grep naming a file passes"),
    ("grep -n / file.txt", 0, "a non-recursive grep whose PATTERN is / passes"),
    ("rg foo", 0, "rg with no path (cwd) passes"),
    ("rg / src", 0, "rg whose pattern is / and path is a repo dir passes"),
    ("Get-ChildItem C:\\ ", 0, "non-recursive Get-ChildItem of a drive root passes"),
    ("Get-ChildItem -Path C:\\ -Recurse -Depth 2", 0, "a depth-bounded recursive listing passes"),
    ("git commit -m \"never run find / here\"", 0, "find / inside a quoted message is not a command"),
    ("python - <<'EOF'\nprint('find / -name x')\nEOF", 0, "find / inside a heredoc body is not a command"),
    ("echo hi | grep -r foo .", 0, "piped grep -r on . passes"),
    ("", 0, "empty command passes"),
]


def check_main(case) -> bool:
    command, expected, label = case
    got = run_main(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected exit {expected}, got {got})")
    return ok


fails += _testlib.run_cases(MAIN_CASES, check_main)

sys.exit(_testlib.summarize(fails))
