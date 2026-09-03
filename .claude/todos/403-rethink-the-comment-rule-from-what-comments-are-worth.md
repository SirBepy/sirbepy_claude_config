<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=182409d3 -->
<!-- duplicate-checked -->
# Rethink the comment rule from what comments are actually worth, in a dedicated session

**Type:** skill-improvement
**Origin:** dev

## Goal

Replace `CLAUDE.md`'s comment rule with one derived from what comments are actually FOR, rather than
from a line count. The current rule caps blocks at 2 lines typical / 4 hard and treats every repo and
every reader the same. Joe wants that reopened in its own session, with an AI, before any more
tooling is built on top of it.

## Context

Joe's own framing, 2026-08-19, in his words:

> "myb we should reword the comments shit? cuz idc about what comments look like if its for AI"
>
> "for clients i dont wnana have stupid unnecessary comments, but for my projects idc"
>
> "i still dont think comments are very valuable, but if they are valuable to AIs then ofc we should
> use comments the best possible way, i think we should dedicate a lil session to this tho"

Three distinct positions in there, and the current rule collapses all three into one number:

1. **Reader matters.** A comment written for an AI reader is a different artifact from one written
   for a human reviewer. The rule does not distinguish them.
2. **Repo matters.** Client repos (zirtue-corp, Fibo-Studio, revaire) pay real review time and
   merge-conflict risk for comment noise. Joe's own repos do not. The rule applies identically to
   both. Note `/cleanup-todos`' worth rubric ALREADY makes this org distinction for a different
   purpose, so there is precedent and a working org check (the `gh-account-switch` hook's mapping).
3. **Value is unproven.** Joe's prior is that comments are not very valuable. The rule was written
   from a single 2026-07-29 incident ("STOP WRITING THESE BIGGASS UNNECESSARY ASS COMMENTS") and
   generalised, never from evidence about what a comment buys a future reader.

What exists today, so the session starts from facts:

- `CLAUDE.md` "Code Style": 2 lines typical, 4 hard cap per block, under ~25% of added lines once a
  file adds 20+. Says a comment earns its place by naming "a constraint, a gotcha, or a measurement
  the code cannot show".
- Enforced by `skills/commit/comment-noise.sh` at commit time (now via `prefilter-gate.sh`) and by
  `/create-pr`'s comment-noise check.
- Six archived todos already patched the MECHANISM without ever revisiting the POLICY: `258`, `290`,
  `293`, `296`, `340`, `361`.
- Todo `399` (live) found the enforcement has never covered Python docstrings or PowerShell
  comment-based help at all, so the repo's longest blocks (39, 29, 24 lines) were never checked.

## Approach

This is a `/brainstorm` session, not a build task. Do not open it by editing `CLAUDE.md`.

Questions worth putting to it:

- What does a comment actually buy an AI reading this file cold, versus what the code, the commit
  message, and the surrounding docs already give it? Is there evidence either way?
- Should the rule split by reader, by repo org, or not at all? If by org, the `gh-account-switch`
  mapping already resolves that from the git remote.
- Is a line cap even the right instrument, or should the rule be about the CONTENT test that already
  sits in the rule ("a constraint, a gotcha, or a measurement") with the number dropped?
- Do API-documentation constructs (docstrings, PowerShell comment-based help) belong in the same
  rule at all? That is `399`'s question, and it should be answered by whatever this session decides
  rather than separately.

Resolve `399` as part of this, or explicitly leave it as the narrow mechanism follow-up once the
policy is settled. Do not answer them independently and let them disagree.

## Acceptance

- `CLAUDE.md`'s comment rule reflects a decision Joe made in conversation, not an inherited number.
- The rule states who it is for and which repos it binds.
- `comment-noise.sh` and `/create-pr`'s check enforce exactly what the new rule says, no more.
- `399` is either closed by this or explicitly scoped as the leftover mechanism piece.

## Notes

- Filed via `/create-todo` on Joe's direct request, 2026-08-19, during the `/mega-todos` wrap-up.
- Supersedes nothing. `399` stays live and is now gated on this; see its Notes.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [TOOLING] Should the comment rule split by reader (AI vs human) and/or by repo org (client vs personal), or stay one flat cap? Options: split by org only / split by reader only / split by both / keep the flat cap and refine only the content test. Recommended: none of these yet. You asked for this to be a dedicated `/brainstorm` session on 2026-08-19 and that is still the right call. Todo 399 is deliberately gated on this answer and must not be built first.
