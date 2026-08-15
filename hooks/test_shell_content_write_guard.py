"""Self-test for shell-content-write-guard.py (todo 289).

Run directly: python hooks/test_shell_content_write_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "shell-content-write-guard.py"
)

# (command, expect_block, label). expect_block=False means it must PASS through.
CASES = [
    ("grep -nE 'Set-Content|Out-File' skills/android-drive/adb-drive.ps1", False, "todo 289 repro: single-quoted grep pattern"),
    ('grep -nE "Set-Content|Out-File" skills/foo.ps1', False, "todo 289 repro: double-quoted grep pattern"),
    ("Set-Content foo.txt bar", True, "bare Set-Content"),
    ("echo hi | Out-File y", True, "piped Out-File"),
    ('echo "use Out-File carefully"', False, "mention in prose, quoted"),
    ("Add-Content -Path x -Value y", True, "bare Add-Content"),
    ("echo hi; Set-Content x y", True, "Set-Content after semicolon"),
    ("ls | Select-Object Name && Out-File z", True, "Out-File after &&"),
    ("foo > notes.txt", True, "todo 257 regress: real redirect"),
    ("foo > /dev/null", False, "todo 257 regress: devnull redirect"),
    ("x | tee y.txt", True, "tee real write"),
    ("x | tee /dev/null", False, "tee to devnull"),
    ("(echo hi) | Out-File z", True, "Out-File after pipe following paren group"),
    ('iex "Set-Content -Path evil.txt -Value pwned"', True, "iex bypass: double-quoted payload"),
    ('Invoke-Expression "Out-File x.txt"', True, "Invoke-Expression bypass: double-quoted payload"),
    ("iex 'Set-Content -Path evil.txt -Value pwned'", True, "iex bypass: single-quoted payload"),
    ('echo "foo\\" ; Set-Content evil.txt "bar"', True, "pwsh backslash-in-dquote bypass: real Set-Content after fake escape"),
    ('echo "he said ""Set-Content"" nicely"', False, "doubled-quote pwsh escape: mention only, not an invocation"),
    ('echo "say `"Out-File`" now"', False, "backtick-escaped quote: mention only, not an invocation"),
]


def check(case) -> bool:
    cmd, expect_block, label = case
    result = guard.find_violation(cmd)
    got_block = result is not None
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {cmd!r} -> {'BLOCK' if got_block else 'PASS'} ({result})")
    return ok


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
