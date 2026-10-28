<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=e652862c -->
# zirtue-release-backfill closes tickets QA has rejected, because shipped-in-a-tag is treated as done

**Type:** skill-fix
**Origin:** ai

## Goal

Stop `/zirtue-release-backfill` from moving a story to `Complete` when QA has bounced it backward,
and make its Gate D approval prompt distinguish the two kinds of close it is proposing.

## Context

The ZNG ENG - Core workflow has one legal path to done, each leg owned by someone different:

1. **Joe / Claude**: `Backlog | To Do | In Progress | Blocked | PR Review` -> **Testing**
2. **QA (Lenar, `6061a5e8-158e-4f42-b4a4-230dcd1fbbad`)**: `Testing` -> **Ready for deploy**
3. **`/zirtue-release-backfill`**: `Ready for deploy` -> **Complete** + Release backfill

`~/.claude-personal/skills/zirtue-release-backfill/SKILL.md` was changed on 2026-07-14 to make
discovery **state-independent**: every ticket whose commit exists in a shipped tag is a candidate,
with only `Complete` and `Won't do` excluded as terminal. That fix was correct for its own problem
(shipped tickets parked in `Testing` were being skipped) but it has no notion of a ticket having been
**rejected**. A story QA bounced back to `To Do` is not terminal, so it stays eligible.

Verified 2026-08-07 by pulling `/api/v3/stories/{id}/history` for all 161 stories Joe owns or
requested. A single run on **2026-08-03 20:28:06-20:28:17** closed **19 tickets in 11 seconds**:

- 14 legal, from `Ready for deploy`
- 5 illegal: `53958` and `54740` from `Backlog`, `54840` and `55002` from `To Do`, `49145` from `On hold`

[sc-55002](https://app.shortcut.com/zirtue/story/55002) is the clearest case. Commit `11ba191` was in
tag `v1.0.0+56`, so the skill saw "shipped" and closed it - six hours after Lenar had reviewed that
exact fix, found it insufficient, commented, and moved it `Testing -> To Do`. The rejection was never
read. Three days later work began on a follow-up fix for a ticket that had been sitting in `Complete`
the whole time. [sc-54840](https://app.shortcut.com/zirtue/story/54840) was closed the same way after
**two** separate QA bounces.

Across all history there are 10 illegal closes total; the other 5 predate this run (2026-03-10 to
2026-03-19) and may have a different cause worth checking separately.

## Approach

1. **Add a rejection check to discovery.** Before proposing a close, pull
   `GET /api/v3/stories/{id}/history` and find the most recent transition. If a member other than
   Joe moved the story *backward* (out of `Testing` or `Ready for deploy` into any earlier state)
   and no subsequent forward move by QA followed, the ticket is REJECTED - exclude it from the close
   set regardless of tag membership.
2. **Split Gate D into two lists.** Present `Ready for deploy -> Complete` (routine) separately from
   anything closing out of another state (needs a look). Right now 19 tickets arrive as one
   approve-all block, which is how 5 bad closes rode along with 14 good ones unnoticed. Backfilling
   the Release field on a rejected ticket is fine and should still happen; only the close is wrong.
3. **Consider dropping the close entirely for non-`Ready for deploy` sources** and instead reporting
   "shipped but not QA-accepted" as a distinct bucket for Joe to act on.
4. Decide whether the skill should ever write `500018659` Ready for deploy - that is QA's transition
   and the audit found 5 instances of it being set outside QA.

## Acceptance

- A story QA has bounced backward is never closed by the skill, even when its commit is in a shipped tag.
- Gate D shows routine closes and unusual-source closes as separate lists.
- Release backfill still runs on rejected tickets; only the state change is withheld.
- Re-running the audit (history sweep for `-> Complete` where old state != `Ready for deploy`) after
  a backfill run yields zero new entries.

## Notes

Found during a `/shortcut-priorities` run in `zng-app` on 2026-08-07. Filed here rather than in the
project backlog because it changes `~/.claude-personal/skills/`. The project-side rule is recorded in
that project's memory as `feedback_never_move_ticket_straight_to_complete`, and the 2026-07-14 change
that introduced this is documented in `feedback_release_backfill_shipped_detection`.

The five tickets wrongly closed on 2026-08-03 still need triage by Joe: 53958, 54740, 54840, 49145
(55002 he already moved back to To Do on 2026-08-07).

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: in `zirtue-release-backfill/SKILL.md`, pull `/api/v3/stories/{id}/history` during
  discovery and exclude any ticket whose latest transition is a backward move by a non-Joe member
  with no subsequent QA forward move. Split Gate D into a `Ready for deploy -> Complete` list and an
  other-state list. Remove the skill's ability to ever write state `500018659`, since the file's own
  Context already documents that transition as QA's exclusively. This was produced by a strict
  second-pass re-triage that specifically asked whether a defensible answer exists without the dev;
  it concluded yes. Not executed only because the session ended.
- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - the rejection-history check, split Gate D1/D2 and the 500018659 write-ban are all live in zirtue-release-backfill/SKILL.md:231,250,270. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
