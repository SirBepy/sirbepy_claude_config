<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Two session-id resolvers disagree, so /close counts 0 screenshots

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/close` Phase 3 step 3 count the screenshots a session actually wrote, by having the two
session-id resolvers agree, or by having `/close` stop trusting the one that can be wrong.

## Context

Reproduced 2026-08-31 in `hubbub-game-music-guesser`, within a single uninterrupted session:

- `close/rename-session.ps1 -GetId` returned **`14236-134326363610796866`**. No such directory
  exists under `.for_bepy/screenshots/`.
- `skills/screenshot/session-shot-dir.cjs`, which the drivers actually call, had written all 11
  screenshots to **`.for_bepy/screenshots/20300-134324723416336555/`**.

`/close` Phase 3 step 3 counts files under the Phase 0 id, so it reported **0 screenshots** for a
session that wrote 11, and Phase 4's counter was wrong. Silent: nothing errors, the number is just
false, so it will not be noticed except by someone checking the folder by hand.

This is adjacent to todo 60 (which established that a process-tree walk was unstable and moved
`rename-session.ps1` onto a `$env:CLAUDE_CODE_SESSION_ID` match). That fixed the PowerShell side.
`session-shot-dir.cjs` was apparently not moved with it, so the two now derive different ids by
different means, and `/close` believes the wrong one.

Note the PIDs differ (`14236` vs `20300`), not just the tick suffix - so this is two different
resolution strategies landing on two different processes, not clock skew.

## Approach

1. Read both resolvers and determine which strategy each uses:
   `~/.claude/skills/close/rename-session.ps1` (`-GetId` branch) and
   `~/.claude/skills/screenshot/session-shot-dir.cjs`.
2. Pick ONE source of truth - almost certainly the `$env:CLAUDE_CODE_SESSION_ID` match todo 60
   settled on - and make the other call it or replicate it exactly.
3. Prefer having `session-shot-dir.cjs` shell out to / mirror the PowerShell logic over a second
   independent implementation, since a second implementation is what created this bug.
4. Consider a cheap `/close` backstop regardless: if the Phase 0 id's folder does not exist but
   exactly one `.for_bepy/screenshots/*` folder was modified during this session's window, count
   that one and say which was used. Defensive, not a substitute for step 2.

## Acceptance

- In one session, `rename-session.ps1 -GetId` and `session-shot-dir.cjs` return the same id.
- A session that captures N screenshots reports N in `/close` Phase 4, not 0.
- Todo 60's fix is not regressed: the id still comes from the session-id match, never a
  process-tree walk.

## Notes

- Found by `/close` itself on 2026-08-31 while counting its own screenshots, which is the only
  reason it surfaced at all.
- Older stray folders exist under `.for_bepy/screenshots/` in that repo (7 of them). They are not
  evidence of this bug on their own - they are prior sessions - but they do mean "just pick the
  newest folder" is not a safe backstop without a time window.
