<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1058 (done) is about clockify gap-fill reading the feed; 234 (done) added pagination + liveness probe. Neither covers feed lag or the missing workable-ticket pass. -->
# 1186 - /shortcut-priorities misses workable tickets and lagging activity-feed events

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-16

## Goal

When Joe asks `/shortcut-priorities` "is there anything we can work on?", the report should surface
the highest-priority ticket that actually needs his work, even when the private activity feed has
not caught up yet and even when the ticket's owner is QA rather than Joe.

## Context

zng-app session 6c4669d7, 2026-10-16. Joe ran `/shortcut-priorities is there anything we can work on?`.
The report recommended sc-55910 (a zng-admin branch) and sc-56376. Joe pushed back later: "is there
anything on the main zng-app codebase that we should be working on rather? no tickets?" A manual
search then found sc-56344 ("BUG: Amplitude: user properties missing in LLC flow"): priority
Highest, Johanna called it "HP", and Lenar @-mentioned Joe on it at 2026-10-16T12:34Z. The
first report never listed it. Two separate gaps caused this:

1. **Feed lag.** The activity feed was pulled at about 14:20Z with `before = now - 10min`. The
   newest event it returned for sc-56150 was at 10:13Z, but the story's own `comments[]` has a
   comment at 11:20Z. Lenar's 12:34Z mention on sc-56344 was also missing. So the private feed
   returned nothing from roughly the last 4 hours. Cause not established: it could be server lag,
   or the `before` cursor behaving differently from what the skill assumes.
2. **Scope.** The skill only reads tickets that appear in the feed, then ranks threads waiting on a
   reply. It never looks at Joe's own To Do / In Progress list, or at Highest-priority FE tickets
   owned by QA (Lenar files and owns bug tickets, the dev only gets a group assignment). sc-56344
   was To Do, owned by Lenar, and Joe was not an owner.

Step 7's tiers in `skills/shortcut-priorities/SKILL.md` have no "workable now" tier at all.

## Approach

In `C:\Users\tecno\.claude\skills\shortcut-priorities\SKILL.md`:

- After the feed pass, add a public-API search pass that does not depend on the feed, through
  `search/stories` (see `refs/shortcut-api.md`). At minimum cover: Joe's own open stories in To Do,
  In Progress and Testing; and open stories updated in the lookback window whose comments
  @-mention `josipmui`, whoever owns them. Dedupe against the feed candidates.
- When the args read as "what can we work on", add a "workable now" section: To Do / In Progress
  tickets with no blocker, ranked by the Priority custom field (Highest first), split by repo
  (zng-app first in zng-app sessions).
- In step 0/2, record the newest event timestamp the feed returned. If it is more than ~1h older
  than now, print a "feed lags by Xh, mentions after <ts> come from the search pass only" line,
  so a gap is never silent.

## Acceptance

- Re-run against a window that contains a fresh @-mention on a QA-owned Highest ticket: the
  ticket appears in the report even if the feed does not return it.
- The report prints the feed's newest-event timestamp, and a lag warning when it applies.
- "is there anything we can work on" produces a workable-now list ordered by priority.

## Notes

**Fold-in 2026-10-19 (session 556b5881):** a related but distinct wording gap. The skill correctly
ran step 7 and found only sc-56344 needing a reply (everything else resolved/not-Joe's-call), but
Joe then asked "wait, youre saying the only ticket i can work on is the 56344? theres no other
ticket for me to work on?" - the step 7 report's "There is no FYI tier" language reads as "this is
everything on your plate" even when it worked exactly as designed (reply-needed items only). Once
this todo's "workable now" section ships, add one line to step 7's template making the section
boundary explicit (e.g. "this covers who's waiting on a reply, not your full active queue") so a
thin reply-needed result doesn't read as an exhaustive backlog even with the new section present.
- Completed 2026-10-23 (loop-todos cycle 1): feed-lag line (Step 3a), public search/stories pass for own queue and @-mentions (Step 3b), workable-now section and the boundary line (Step 7). Not run live; updated: operator and feed timestamp key are documented as assumptions with fallbacks.
