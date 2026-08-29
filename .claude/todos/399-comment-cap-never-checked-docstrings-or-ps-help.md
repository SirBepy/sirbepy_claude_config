<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=5, reconfirm-count=2, content-hash=004ebba4 -->
<!-- duplicate-checked -->
# The comment cap is unenforced for Python docstrings and PowerShell comment-based help

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether a module/function docstring and a PowerShell `<# .SYNOPSIS #>` help block count
against the comment cap, write that decision into `CLAUDE.md`, and make `comment-noise.sh` match it.
Right now the rule and its named enforcer disagree, and the repo's own practice disagrees with both.

## Context

`CLAUDE.md` says the cap is "2 lines typical, 4 lines HARD CAP per block" and that it is "Enforced
at commit time by `/commit`". `/commit` step 5a delegates that to `skills/commit/comment-noise.sh`.

That script cannot see either construct. Its awk line-comment pattern is
`^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)` (`skills/commit/comment-noise.sh:19`), which never
matches a `"""` docstring and never matches `<#`, since `<#` is not `<!--` and the `#` alternative
is anchored to the start of the line.

So the cap is enforced for `#` and `//` comments and silently not enforced for the two constructs
that produce the longest blocks in this repo.

Meanwhile the repo's established practice is that these blocks are long, and this predates the
2026-08-19 run. Measured that day:

- `hooks/commit-guard.py` module docstring: 24 lines
- `hooks/shortcut-create-guard.py`: 17 lines
- `hooks/dispatch-preamble-guard.py`: 13 lines
- `hooks/_hooklib.py`: 10 lines
- `skills/close/complete-todo.ps1` help block: 39 lines
- `skills/close/claim-todo.ps1`: 29 lines
- `skills/cleanup-todos/update-markers.ps1`: 11 lines

A `/code-check` pass flagged four NEW files (`hooks/todo-duplicate-guard.py`,
`hooks/write-session-marker.ps1`, `skills/disk-doctor/orphan-audit.ps1`,
`skills/e2e/scripts/design_diff.py`) as BLOCKERs for exactly this. They were not trimmed, because
doing so would hold new files to a standard no existing file in the repo meets. That is a doc gap,
not four code defects, which is why this is one todo instead of four.

## Approach

Pick ONE and apply it end to end. Do not do half.

1. **Exempt them** (the answer the repo's practice already implies): say so explicitly in
   `CLAUDE.md`'s comment rule, naming the constructs, and add a one-line note in
   `comment-noise.md` that the script deliberately does not check them. Cheapest, and API
   documentation genuinely is a different thing from a comment narrating the next line.
2. **Cap them**: extend `comment-noise.sh` to recognise `"""`/`'''` and `<# ... #>`, then bring all
   ~7 existing offenders under the cap in the same pass. Do not ship the script change alone, or
   the next commit touching any of those files fails a check it never had to pass before.

Either way, state the decision where the next reader hits it, and make the two agree.

## Acceptance

- `CLAUDE.md` says plainly whether these two constructs are in or out of the cap.
- `comment-noise.sh` behaves the way `CLAUDE.md` says.
- If option 2: every pre-existing offender is under the cap, so the check passes repo-wide.

## Notes

- **Gated on todo 403** as of 2026-08-19. Joe reopened the comment rule itself rather than answering
  this in isolation: he does not value comments for their own sake, does not care how they look in
  his own repos, does care about noise in client repos, and wants to know what a comment is actually
  worth to an AI reader before more tooling is built on the current cap. 403 is a `/brainstorm`
  session for that.
- Do not answer this todo independently. Whatever 403 settles about who the rule is for and which
  repos it binds determines whether docstrings and comment-based help belong in the rule at all. 403
  may close this one outright.

