<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=f4afea2e -->
# Grep for em dash before any `gh pr create`/`gh pr edit` body publish

**Type:** skill-improvement

## Goal

Add a mandatory em-dash grep step, run right before any `gh pr create --body-file` or
`gh pr edit --body-file` call, to `C:\Users\tecno\.claude-fibo\skills\create-pr\SKILL.md`
(and any other skill/procedure that composes PR-body markdown and publishes it via `gh`).

## Context

2026-07-29: while executing todo 170 (add screenshots to 4 already-merged PRs), the session wrote
short image-caption alt text directly (`![Scope switcher open — searchable...]`) and pushed it live
via `gh pr edit --body-file` to 4 real GitHub PRs without grepping for em dashes first. Caught only
at the next `/close` retrospective grep, after the em dashes had been live on GitHub for the whole
session, and fixed with a follow-up `gh pr edit`.

This is the fourth recorded recurrence of the same failure mode - see (auto-memory)
`feedback-grep-verify-em-dash-and-text-replaces.md`, which now documents all four. The first three
were about committed files (subagent builder output, doc prose); this one is different in kind:
the em dash never touched a file that got committed, it went straight from generated text to a
live, externally-visible GitHub PR body via `gh api`/`gh pr edit`. The existing habit of "grep
before commit" doesn't fire for a `gh` publish call that has no commit step at all.

`create-pr/SKILL.md`'s "Image hosting" section (`## Image hosting`) already documents the upload
commands (`gh api --method PUT ... -F content=@<file>`) and the embed markdown format
(`![<what it shows>](<url>)`) - this is the natural place to add a pre-publish grep step, since
every image caption is exactly the kind of short hand-authored string most likely to carry a
stray em dash.

## Approach

- In `create-pr/SKILL.md`, wherever the body (including the image caption line) is about to be
  written to the preview file or passed to `gh pr create`/`gh pr edit --body-file`, add a step:
  grep the composed body text for the em dash character (`\xe2\x80\x94` / U+2014) and fail/fix
  before publishing, not after.
- Since this failure isn't unique to `/create-pr` (this session hit it doing an ad-hoc `gh pr edit`
  outside that skill entirely), consider whether the check belongs somewhere more general - e.g.
  restated as a rule in this project's own CLAUDE.md's git/PR section, or folded into the global
  `feedback-grep-verify-em-dash-and-text-replaces` memory's "how to apply" (already updated) so it
  surfaces regardless of which skill is driving the `gh` call.
- Fix command already proven this session: `sed -i 's/ — /: /' <bodyfile>` (Bash tool, not
  PowerShell - see `bash-tool-not-powershell-heredoc` memory) then re-run the `gh pr edit`.

## Acceptance

- A fresh `/create-pr` run (or any ad-hoc `gh pr edit --body-file` composing new prose) greps its
  own output for em dash before the `gh` call goes out, not after.

## Notes

Full failure history and the "why" lives in auto-memory
`feedback-grep-verify-em-dash-and-text-replaces.md` - this todo is just "go add the enforcement
step," not re-research why it keeps happening.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 173; renumbered to 31 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: added the mandatory pre-publish em-dash grep as a bullet in create-pr/SKILL.md step 5, right before the `gh pr create`/`gh pr edit --body-file` calls (the actual publish point), rather than in drafting-rules.md's "## Image hosting" section - this run's dispatch scoped edits to SKILL.md only, and the gate lives with the main agent's live approval step anyway, not the drafting subagent.
