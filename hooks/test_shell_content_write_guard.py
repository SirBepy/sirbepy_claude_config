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
    # todo 845: masking double-quotes globally before single-quotes let a `"`
    # trapped inside one single-quoted span pair across the boundary with a
    # stray `"` elsewhere, swallowing the real `>` in between.
    (
        'sed -e \'s|foo = "bar|baz|\' > out.txt && echo "done"',
        True,
        "todo 845 repro: odd dquote count inside squote swallows a later real redirect",
    ),
    (
        'sed -e \'s|const AUQ_ANSWER_SENTINEL = "<auq-answer/>";|const AUQ_ANSWER_SENTINEL = "<auq-answer";|\' '
        "-e 's|foldText: A|foldText: B|' e2e/a.spec.ts > e2e/zz-scratch.spec.ts && pnpm exec playwright test e2e/zz-scratch.spec.ts",
        True,
        "todo 845 call-1: balanced-but-nested dquotes inside squoted sed exprs, real redirect still catches",
    ),
    (
        "rm -f e2e/zz-scratch.spec.ts && sed -e "
        '\'s|const AUQ_ANSWER_SENTINEL = "<auq-answer/>";|const AUQ_ANSWER_SENTINEL = "<auq-answer";|\' '
        "-e 's|foldText: A|foldText: B|' src.ts > e2e/zz-scratch.spec.ts && pnpm exec playwright test e2e/zz-scratch.spec.ts",
        True,
        "todo 845 call-2: same shape, differing quote parity in the preceding sed exprs",
    ),
    # SHARED INVARIANT with todo 476 (opposite direction, same hook): both must
    # hold after either fix lands.
    ("echo x > f.txt", True, "shared invariant: plain redirect still blocked"),
    ("a >> append.txt", True, "shared invariant: append still blocked"),
    ("echo hi; foo > later.txt", True, "shared invariant: redirect after ; still blocked"),
    ("echo hi && foo > later2.txt", True, "shared invariant: redirect after && still blocked"),
    ("const f = () => onChanged(true)", False, "shared invariant: => is an operator, not a redirect"),
    ("const g = () -> onChanged(true)", False, "shared invariant: -> is an operator, not a redirect"),
    ("a !> b", False, "shared invariant: !> is an operator, not a redirect"),
    ("a <> b", False, "shared invariant: <> is an operator, not a redirect"),
    ("byId >= 0", False, "shared invariant: >= is an operator, not a redirect"),
    (
        "python - <<'PY'\nh = [r for r in h if r['x'] > 0]\nPY",
        False,
        "shared invariant: > inside a quoted-tag heredoc body is not shell syntax",
    ),
    (
        "python - <<'PY'\nonTap: () => onChanged(true)\nPY",
        False,
        "shared invariant: arrow syntax inside a quoted-tag heredoc body",
    ),
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
