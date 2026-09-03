<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# commit-guard blocks a pure code move that /commit's own docs say must NOT be trimmed

**Type:** skill-improvement
**Origin:** ai

## Goal

Let a commit whose comment-noise hits are all **verbatim moves from another file in the same
commit** reach `git commit`, without weakening the gate for genuinely new comments.

## Context

Reported 2026-09-03 by a builder during a `/mega-todos` run in `claude_usage_in_taskbar` (todo 862,
splitting `event-store.ts` into `event-store-delivery.ts`).

The rule and the enforcement disagree:

- `skills/commit/SKILL.md` step 5a and `skills/commit/comment-noise.md` both carry an explicit
  **exception**: "a block flagged only because it moved verbatim from elsewhere in this same commit
  is not new noise - confirm via `git show HEAD:<old-file>` before trimming it." `refs/builder-preamble.md`
  states the same carve-out for subagents.
- `hooks/commit-guard.py` (PreToolUse on `git commit`, added per todo 844) re-runs
  `prefilter-gate.sh` against the commit's own `-- <files>` pathspec and blocks on **any** non-zero
  exit. It has no notion of the carve-out, because the carve-out is a judgement call about
  provenance, not something the gate's output encodes.

Concretely, on that split: the new module was 235 lines of code moved verbatim out of a file the
builder had just read, and the gate reported 38% comment ratio / 17-line longest block. Every one of
those comment lines already existed at `HEAD` in `event-store.ts`. The builder had followed the
documented exception and correctly declined to trim them, and then could not commit.

The builder also checked the escape hatches and found none reachable: `CLAUDE_COMMIT_HOOK_BYPASS`
must be set in the environment before Claude launches, so a subagent cannot set it mid-dispatch.

**Not yet verified, and it decides the fix:** whether the builder ultimately trimmed the moved
comments to get past the hook, or found another route. If it trimmed them, this gap has already
silently damaged carried-over documentation at least once, which raises the priority.

## Approach

Options, roughly in preference order:

1. **Teach the gate provenance.** In `comment-noise.sh`, before reporting a block, check whether the
   identical block exists at `HEAD` in any file in the same pathspec (`git show HEAD:<f>`). If it
   does, it is a move, not new authorship - drop it from the report. This fixes the rule and the
   hook together, and removes the judgement call from the human entirely. Most work, best outcome.
2. **A commit-message opt-out.** Recognise a marker like `[moved]` in the commit message and skip
   comment-noise for that commit only, the way `<!-- duplicate-checked -->` unblocks
   `todo-duplicate-guard.py`. Cheap and symmetric with an existing pattern, but it is a blanket skip
   for the whole commit, so a move commit that also adds new noise gets a free pass.
3. **Per-file opt-out** naming which paths are pure moves. Narrower than 2, more typing.

Option 1 is the one to aim for. Option 2 is an acceptable stopgap if 1 proves fiddly, but do not
ship 2 and call the todo done.

## Acceptance

- A commit consisting only of a verbatim code move, whose moved comments exceed the cap, reaches
  `git commit` without the moved blocks being trimmed.
- A commit that adds NEW over-cap comment blocks is still blocked, including one that mixes a real
  move with new noise.
- A test under `hooks/` covers both cases, so this cannot regress silently.

## Notes

- Do not solve this by raising the comment cap or by loosening `comment-noise.sh`'s thresholds. The
  cap is correct; the gap is that provenance is invisible to it.
- `hooks/commit-guard.py` deliberately re-runs the gate rather than trusting the caller (todo 844).
  Keep that property - the fix belongs in what the gate reports, not in the guard trusting a claim.
