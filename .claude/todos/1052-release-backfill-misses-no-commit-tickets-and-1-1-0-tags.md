<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=7, reconfirm-count=1, content-hash=8fca45ee -->
<!-- duplicate-checked: 203 (9of10 lifts), 12 (never set Complete) and 1051 (done-audit arg parsing) touch the same area but none covers commit-less Ready for deploy tickets or the 1.1.0 tag format. -->
# 1052 - zirtue-release-backfill misses Ready for deploy tickets with no commits, and hard-codes 1.0.0 tags

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-30

## Goal

`/zirtue-release-backfill` handles the two cases the 2026-09-30 FE 1.1.0+1 close-out hit by hand:
Ready for deploy tickets with no id-carrying commit, and the `v1.1.0+N` / `FE 1.1.0+N` version format.

## Context

zng-app session, 2026-09-30. Claude ran the backfill procedure by hand (Joe had asked for the
close-out without typing the skill) over 146 Ready for deploy tickets Joe owns:

- 106 matched commits by prefix or bundled-id grep and closed cleanly.
- **22 had no commit mentioning their id in any repo** (zng-app, zng-admin, zng-api, zng-biller).
  Step 3's discovery is a git-author id scan, so the skill would never see them. Six sonnet agents
  (about 4 tickets each) traced them: 21 had really shipped. Most landed under other commits: the
  bulk `7f54ae7` "Mirror the v1 analytics events across the share-to-claim flow", sibling-ticket
  commits (55584's OTP fix covered 55594/55606, 55508 covered duplicate 55382, 54668 covered 54576),
  epic-level commits with no id (55118, 55114). The rest were "ensure X triggers" verifications
  of behavior that already existed (55926 shipped in FE 1.0.0+46, March). One (54084) had no
  traceable fix; Joe left it alone because the legacy flow is being deleted.
- The skill's step 5 regex and step 4c mapping only know `v1.0.0+N` -> `FE 1.0.0+N`. zng-app now
  tags `v1.1.0+0` / `v1.1.0+1`, and the Release enum has `FE 1.1.0+0` / `FE 1.1.0+1`.
- zng-admin jumped from tag `v1.0.0+9` to `v1.0.0+11` (no +10 tag), while the enum had
  `Admin 1.0.0+10` but not `+11`. Joe had to add `Admin 1.0.0+11` in the Shortcut UI mid-run.
- The biller portal (zng-biller) has no version tags at all (only `scaffold-complete`, `auth-complete`,
  `team-complete`), because it has never been deployed. Its Ready for deploy tickets must stay put.

## Approach

In `C:\Users\tecno\.claude\skills\zirtue-release-backfill\SKILL.md`:

1. Generalise the version regexes/mapping from `1\.0\.0` to `\d+\.\d+\.\d+` in step 4c and step 5.
2. Add a discovery pass alongside step 3: every story Joe owns in `Ready for deploy` that step 3
   did not find. Report it in a new "Ready for deploy, no commit" bucket. For each, dispatch a
   read-only sonnet trace (batched ~4 tickets/agent): locate the behavior in code, `git log -S` the
   introducing commit, take its first containing tag as the proposed Release. Never auto-close this
   bucket; it goes through Gate D2.
3. Before step 4c, check that every proposed Release label exists in the enum and list the missing
   ones up front (one ask), rather than failing per ticket.
4. Treat a repo with no version tags (zng-biller today) as "never deployed": its tickets are
   reported and never proposed for Complete.
5. Multi-release tickets: the dev confirmed 2026-09-30 that Release = the NEWEST containing tag, not
   the first. Tickets already in Complete are never touched. Update step 4c's "first matching tag
   wins" line accordingly.

## Acceptance

- A dry run on a repo tagged `v1.1.0+N` proposes `FE 1.1.0+N` values.
- A Ready for deploy ticket with no id-carrying commit shows up in the report instead of vanishing.
- zng-biller tickets are never proposed for Complete while that repo has no version tags.

## Notes

- `git log -E --grep='\b<id>\b'` silently matches nothing (git's ERE has no `\b`); use `-F --grep <id>`
  and filter the digits boundary afterwards. Claude hit this in the hand-run; the skill's own step 3
  uses shell `grep -oE` on piped output, which is fine.
