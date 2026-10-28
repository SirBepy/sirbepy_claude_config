<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=f6970b28 -->
<!-- duplicate-checked: grepped for "shortcut activity"/"activity feed"/"secondary evidence"/"gap
evidence" across the backlog, no hit touches step 6a's gap-evidence sources -->
# clockify-reconciliator gap-fill should check the Shortcut activity feed, not only git commits

**Type:** skill-improvement
**Origin:** ai

## Goal

When step 6a finds a commit-free gap and the dev says it was real work rather than a break, step
6a (or a new sub-step) should check the Shortcut activity feed before falling back to "filled from
the dev's own description only" - it independently timestamps ticket updates/comments and can
confirm or deny a gap is backed by real, dated evidence even when git shows nothing.

## Context

Found 2026-09-30, zng-app, `/clockify-reconciliator zirtue` for "today". Two commit-free gaps
(15:31-16:20 and 17:03-17:50 local) surfaced after the dual-subagent sanity check added this same
session (`skills/clockify-reconciliator/SKILL.md` step 7a). The dev said both were
real work ("testing... reading and replying to comments and also checking out the code being
written") and asked "are there any other commits or smth I can find?"

Checked `~/.claude/refs/shortcut-api.md`'s private activity-feed endpoint
(`POST https://app.shortcut.com/backend/api/private/permission/activity`, cookie-based auth per
`reference_shortcut_activity_feed_auth` memory) for the dev's own actions in both gap windows. This
turned up hard, independently-timestamped evidence for the 17:03-17:50 gap - ticket updates on two
stories plus comments on an epic and a story, all inside the window - that upgraded that block from
"dev's word only" to "confirmed via a second system". The 15:31-16:20 gap had no hits in Shortcut
either, and none in a GitHub PR/issue search (this project pushes straight to `develop`, no PR
review trail exists to check), so it stayed backed by the dev's statement alone - which is still
valid per the skill's existing "explicitly named real activity" rule, just weaker evidence than the
other gap got.

This was improvised this session, not documented anywhere in the skill. It's a real, repeatable
technique: git commits are not the only system that timestamps a dev's work, and checking a second
source before accepting "trust me" as the only backing for a gap costs one extra API call.

## Approach

In step 6a (Gap detection), after a gap is confirmed as real work by the dev (not a break), add: 
before filling it purely from the dev's verbal description, check the Shortcut activity feed for
that window (existing private-endpoint pattern, already used by `/shortcut-priorities`) filtered to
the dev's own `member_id`. If it returns ticket updates/comments inside the gap window, use that to
write a more specific, evidence-backed description (naming the actual tickets/epics touched, the
way this session did: "Triage email-gate and impersonation tickets, reply to LLC epic comments")
instead of a generic paraphrase of the dev's statement. If Shortcut also returns nothing, fall back
to the dev's description as before - this is a strictly-better-when-available check, not a new
requirement that blocks anything.

Also worth checking: whether a GitHub PR/issue search (`gh api search/issues`) is worth the same
treatment for repos that DO use a PR review flow (zng-app/zng-admin/zng-biller currently don't -
commits land straight on `develop` - but this may not hold for every configured project).

## Acceptance

- Step 6a documents the Shortcut-activity-feed check as a second evidence source for a
  dev-confirmed gap, alongside (not replacing) the existing "explicitly named real activity" rule.
- A gap backed by Shortcut evidence gets a specific, ticket-referencing description; a gap with no
  trail anywhere still falls back to the dev's own words, same as today.

## Notes

Related: [[1057-clockify-plan-should-state-per-repo-commit-counts-up-front]] (also found this
session, same theme of surfacing evidence the skill can gather but currently doesn't show/use by
default).
- Completed by /loop-todos cycle 1 (2026-10-05), lane F1: skills/clockify-reconciliator/SKILL.md. Docs-only procedure change, untestable by Claude beyond ci/run_all.py (drives live Clockify/HubStaff/Shortcut APIs).
