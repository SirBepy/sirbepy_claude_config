<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Handoff: next session runs todo 58, the full skills/ audit, as its own session

**Type:** task
**Origin:** dev

## Goal

Joe's decision on 2026-08-17, in his words: *"i wanna soon do the todo 58"*, then, after the backlog
was cleared down for it, *"lets write the /handoff and make it so that 58 is the next todo"*.

So: **the next session's job is todo 58** - a full audit pass over
`C:\Users\tecno\.claude\skills\`, producing an explicit keep / update / remove verdict per skill.
This handoff exists to get that session started with an accurate picture, not to add work of its
own. Read `58-audit-skills-directory-keep-update-remove.md` in full; it is the actual spec.

## Context

**Why now.** 58 is Joe's fourth deferral of this audit. It kept being deferred because it is a
whole-session job and there was always a cheaper queue in front of it. This session cleared that
queue on purpose. The stated reason for wanting the backlog small first, in Joe's words: *"before
that i wanna make sure as many todos as possible are resolved"*.

**What this session did.** A named-subset `/auto-do-todos` run over five ids Joe picked, all five
landed:

- **352** (`e9df720`) - `/autopilot` and `/delegate` got todo 347's exact commit-cadence wording.
- **354** (`b0b18e8`) - `hooks/.claude/` gitignored. The writer hunt came back EMPTY; nothing in
  this repo writes or reads it. That is recorded, so nobody re-hunts.
- **358** (`d802142`) - `/auto-do-todos` Steps 2-3 no longer claim "no size exemption". Two
  invocations are now sanctioned to move Step 2's work: questions-first and named-subset.
- **359** (`ba7e097`) - `Europe/Zagreb` recorded at skill level in the clockify reconciliator.
- **361** (`8df1b12`) - absolute prefilter paths plus all three scripts in `/mega-todos`' injected
  commit block. Verified empirically from inside a real non-`.claude` repo.

Backlog went 17 active to 14. Nothing is claimed; `.claims/` is empty.

**What 58 itself must know before starting.** Its own file was refreshed this session because half
its blocked-list had rotted: 44 and 63 are DONE, 11 and 30 are still live and still blocked, and
**362 was added to that list** - it proposes a new render-and-diff skill, which is the same
new-skill-surface shape as 11 and 30, and Joe was never asked whether to park it. The audit should
rule on 11, 30 and 362 explicitly.

The skills surface was re-enumerated 2026-08-17: **83 directories, 1101 files, 680 tracked**, up
from 76 / 669 / 664 on 2026-08-13. The 421-file gap between on-disk and tracked is untracked
runtime spill living inside `skills/` (Playwright profiles and similar).

**Decisions already settled - do not re-litigate.**

- 58 is a whole-session job, never a side quest inside another run. Joe on 2026-08-13: *"this is
  meant to be a whole session kind of thing, so skip this for now."*
- 11, 30 and 95 stay parked. Joe reconfirmed all three on 2026-08-16; 95 in particular is a
  `/brainstorm` task for its own session, not a build task waiting for approval.
- The 12 vendored skills (11 Cloudflare-family plus `impeccable`, see `skills/VENDORED.md`) are
  judged on "do we still want this installed", not on quality. Only one carries a local patch.

## Approach

1. Read `58-audit-skills-directory-keep-update-remove.md` in full. It is the spec; this file is not.
2. Claim 58 per `~/.claude/skills/close/ai-todos-format.md` before executing anything.
3. Start from what the 2026-08-01 audit left (12 skills deleted, 3 merges, todos in the 29-48 id
   range), not from zero. See `project_2026-08-01_skill_audit.md` in memory.
4. Produce a per-skill keep / update / remove verdict, and rule explicitly on 11, 30 and 362.
5. Archive this handoff (366) once 58 is genuinely underway - it is a pointer, not work.

## Verify

- [ ] `git -C C:/Users/tecno/.claude status --short` - expect other sessions' files still dirty
      (`skills/flutter-bump/`, `skills/linear/SKILL.md`, `hs_weekshot.cjs`, todo 357). Not yours.
- [ ] `ls C:/Users/tecno/.claude/.claude/todos/.claims/` - expect empty before claiming 58.
- [ ] `git -C C:/Users/tecno/.claude log --oneline -8` - the five commits above should be at HEAD.
- [ ] Read `.claude/todos/PLAN.md` - 58 is pinned as next, directly under this handoff.

## Notes

- This repo has a large unpushed backlog on `master` (50-plus commits) and no push cadence. That is
  normal here; do not "fix" it.
- Other sessions were writing into this repo concurrently during the run - todo 364 arrived
  mid-session from one of them. Expect company; commit strictly by pathspec.
- Two findings were filed this session rather than fixed, both out of scope at the time:
  [[365-session-marker-writes-land-on-malformed-paths]] and, from another session,
  [[364-mega-todos-commit-block-fails-dispatch-guard]]. Neither blocks 58.
- The highest-value item in the remaining queue is **356** (a flagged diff can still be committed
  because the prefilters and `git commit` run in one shell call). It is not 58's problem, but if
  the audit finishes early it is the next thing worth doing.
- Archived 2026-08-18: todo 58 ran and completed this session. This was a pointer, not work.
