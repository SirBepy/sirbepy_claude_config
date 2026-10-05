<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=bfaa56aa -->
<!-- duplicate-checked: 2026-09-29; grepped backlog + done/ for "shell-content-write-guard", "partial staging", "apply --cached"; done/827 (CRLF-safe patching) and done/792 (git show blob extraction) are related but neither covers edge-cases.md's recipe. -->
# `/commit` partial-staging recipe is blocked by the shell-write guard

**Type:** skill-improvement
**Origin:** ai

## Goal
`skills/commit/edge-cases.md`'s "Splitting one file across commits" recipe runs as written, with no
guard denial and no line-ending trap.

## Context
Hit 2026-09-29 committing one new hook entry out of a `settings.json` that also held a peer
session's uncommitted edits. Step 1 of the recipe (`edge-cases.md:21`) says
`git -C <path> diff <file> > <tmp>.patch`. `hooks/shell-content-write-guard.py` denies that `>`
redirect, so the documented recipe is uncallable in this setup.

The workaround that worked: a Python heredoc that reads `git diff <file>` via `subprocess`, keeps
the wanted hunks, and pipes the patch to `git apply --cached --recount -` on stdin. The first
attempt used `text=True`, and `git apply` rejected the patch ("patch does not apply"). On
Windows, text-mode stdin turns `\n` into `\r\n`, which breaks the context match. Switching to
bytes (no `text=True`) applied cleanly.

## Approach
Replace step 1-3 in `edge-cases.md` with the bytes-mode Python recipe (or a small committed
helper, e.g. `skills/commit/stage-hunks.py <file> --match <substring>` that stages only hunks
containing the substring). Name the text-mode CRLF trap in one line so the next session does not
retry it.

## Acceptance
- Running the documented recipe on a file with two unrelated hunks stages exactly one, with no
  guard denial, verified by `git diff --cached`.
- If a helper script is added, it has a self-test that CI discovers.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), lane G2: split-hunks.py stage mode (no shell redirect, bytes mode so no CRLF rewrite), tested in skills/commit/test_split_hunks.sh.
