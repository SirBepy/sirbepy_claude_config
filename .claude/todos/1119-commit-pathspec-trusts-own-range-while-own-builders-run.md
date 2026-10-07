<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=9, reconfirm-count=1, content-hash=cecf85c6 -->
<!-- duplicate-checked: 1061 (done) fixed parallel builders' STAGED files leaking via git diff --cached; this is two builders editing the SAME file, committed by named pathspec, which 1061's fix does not cover. 1025/924/933 are about multiple session markers; here there is only one -->
# commit-pathspec trusts auto-derived own ranges while the session's own parallel builders are still editing

**Type:** skill-improvement
**Origin:** ai

## Goal

An orchestrator committing one builder's work while another of its own background builders is
still running cannot sweep the still-running builder's hunks into that commit unnoticed.

## Context

2026-10-07, sirbepy_assistant `/auto-do-todos` run. Two sonnet builders ran in parallel in one
tree with "Leave all changes unstaged" (todo 1061's fix, followed): B4 (compose handoff) and B3
(sender logos). Neither dispatch's OFF LIMITS list named `app/lib/state/providers.dart`, so both
edited it. B4 reported first; the orchestrator committed B4's reported files by pathspec via
`skills/commit/commit-pathspec.sh`, including `providers.dart`. The script's `[own-range]` step
printed `auto-derived own-range ... (every current hunk assumed own, todo 924/933)` and
`[foreign-hunk-check] clean`, because `hooks/.session-markers/` showed one live marker. That one
marker was this same session; its own subagents write under it, so the "solo session" test passes
while another writer is active in the file. Result: commit ab5bacf carried B3's half-finished
sender-logo providers, which imported files not yet in any commit, so HEAD did not compile on its
own. Caught only because the orchestrator grepped the committed diff for "logo" afterward; fixed by
soft-resetting and recommitting a hand-trimmed `providers.dart` (029d305).

A pathspec names whole files, and a file two builders share is not attributable by file.

## Approach

Pick one, or both:

1. `refs/delegation-doctrine.md` Parallelism / fan-out section: every parallel dispatch's OFF
   LIMITS must name each shared registry file (providers/DI file, `main.dart`, router, index
   barrels) as owned by exactly one builder, and the orchestrator must not commit a file a still-
   running sibling's lane could reach until that sibling reports.
2. `skills/commit/commit-pathspec.sh`: treat "this session has a running background Agent" like a
   second live marker, so auto-derived own ranges get the UNVERIFIED verdict instead of `clean`
   (needs a cheap signal for running subagents; check what the session can see).

## Acceptance

Replaying the scenario (two parallel builders editing one file, commit after the first reports)
either refuses at foreign-hunk-check or is prevented by the dispatch rule, and the doctrine or
script text names the case.
