<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=ba9242e0 -->
# Enforce AskUserQuestion for mid-task proposal questions, not just formal decision gates

**Type:** skill-improvement

## Goal

Stop asking ad-hoc "want me to do X or Y?" questions as plain chat text mid-conversation. The
global rule (`~/.claude-personal/CLAUDE.md` "Communication" section) is unconditional: "Every
question: use the AskUserQuestion tool with 2-4 options. Never a bare open-ended question." There
is no carve-out for quick/informal proposals raised in the middle of an otherwise-flowing reply.

## Context

During the frontend2 version.json / Caddy caching session (2026-07-28, branch
`worktree-frontend2-version-json`), after diagnosing the stale-refresh caching bug, a response
ended with: "That's a one-line-per-app Caddy change... Want me to add it now (same worktree,
follow-up commit) or as its own PR?" â€” written as plain prose, no `AskUserQuestion` call, no
`[ARCH]`/`[TOOLING]` domain tag. The dev answered inline ("yeah do it in the same pr, might as
well") so no harm resulted this time, but the rule was still violated. This is a different failure
mode from the one already tracked in memory `feedback-no-text-before-question-tool.md` (which is
about narration appearing *before* a tool-based question) â€” that memory assumes the tool gets
called at all; this incident skipped the tool entirely.

## Approach

This isn't a single skill file to edit â€” it's a self-monitoring gap in how the global
communication rule gets applied moment-to-moment during a live response.

Recommend: any time a response is about to end with a question mark aimed at the dev (proposal,
confirmation, fork), stop and route it through `AskUserQuestion` with a domain tag instead of
finishing the sentence in prose â€” even for what feels like a "quick, obvious yes/no." A durable
memory (`feedback-always-use-askuserquestion-tool.md`) was already written this session to
reinforce this; this todo exists to flag that the underlying in-the-moment discipline still needs
reinforcement â€” there's no code or config change to make.

## Acceptance

- Future sessions in this project (and globally, since the rule lives in the personal CLAUDE.md)
  route every dev-facing question â€” including small mid-reply proposals â€” through
  `AskUserQuestion` with a domain tag, not plain text ending in "?".

## Notes

Low stakes this time (dev answered fine inline), but the rule is written as absolute ("never a
bare open-ended question") so treat any repeat as a real regression, not a style nit.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 160; renumbered to 27 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Skipped by /auto-do-todos 2026-08-08: the todo's own Approach concludes there is no code or config change to make, and the behavior is already covered by the feedback-always-use-askuserquestion-tool memory.
