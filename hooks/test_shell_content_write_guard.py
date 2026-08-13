"""Self-test for shell-content-write-guard.py (todo 289).

Run directly: python hooks/test_shell_content_write_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "guard", Path(__file__).resolve().parent / "shell-content-write-guard.py"
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

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
]


def run() -> int:
    fails = []
    for cmd, expect_block, label in CASES:
        result = guard.find_violation(cmd)
        got_block = result is not None
        ok = got_block == expect_block
        print(f"[{'PASS' if ok else 'FAIL'}] {label}: {cmd!r} -> {'BLOCK' if got_block else 'PASS'} ({result})")
        if not ok:
            fails.append(label)
    print("\nALL PASS" if not fails else f"\nFAILURES: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
