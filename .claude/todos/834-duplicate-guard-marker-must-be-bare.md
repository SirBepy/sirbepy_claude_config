<!-- duplicate-checked -->
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=1, content-hash=27dc42d4 -->
# todo-duplicate-guard: say the `<!-- duplicate-checked -->` marker must be bare

**Type:** task
**Origin:** ai

## Goal

Make `hooks/todo-duplicate-guard.py`'s rejection message state that the override marker must be the
exact literal `<!-- duplicate-checked -->`, not a comment merely containing that phrase.

## Context

The message currently reads:

> If it is genuinely distinct and only shares vocabulary, add `<!-- duplicate-checked -->` anywhere
> in the new file's content to proceed.

"anywhere in the new file's content" reads as "the phrase, anywhere", so the natural move is to put
the justification inside the same comment:

```markdown
<!-- duplicate-checked: the "live-verify" hits are all different surfaces; none touches this one -->
```

That does not match, and the hook re-rejects with the identical message, giving no signal that the
FORM was the problem rather than the content. Cost two wasted Write round-trips on 2026-08-29
(claude_usage_in_taskbar, filing todo 825) before guessing that the marker had to stand alone with
the rationale on a separate line.

## Approach

Either:
- **(a)** relax the matcher to a substring/prefix match so `<!-- duplicate-checked: reason -->`
  passes - probably the better fix, since inlining the reason next to the marker is what an author
  naturally wants and it keeps the justification adjacent to the override; or
- **(b)** keep the strict match and change the message to: `add the exact line
  <!-- duplicate-checked --> (on its own, no trailing text inside the comment)`.

Read the hook first to see which form the matcher actually uses before picking.

## Acceptance

- `python ci/run_all.py` passes.
- Whichever branch is taken, a fresh session that puts its reason inside the marker comment either
  succeeds (a) or is told exactly why it failed (b) - never re-rejected with the same message.

## Found by

`/close` Phase 1 retrospective, 2026-08-29, from a project session in claude_usage_in_taskbar.
Filed here per CLAUDE.md: findings about the global `~/.claude` tree belong in this repo's backlog,
not the surfacing project's.
