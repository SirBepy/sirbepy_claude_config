<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=8c0d138d -->
# zirtue-release-backfill: apply the two 9/10 lifts (bundled-ID discovery + all-SHAs-tagged)

**Type:** task

## Goal

Close the two residual gaps that kept `skills/zirtue-release-backfill/SKILL.md` at 8/10 in the 2026-07-14 /rate-it pass: tickets referenced only as bundled secondary IDs never enter discovery, and a ticket with only some of its commits tagged is wrongly treated as fully shipped.

## Context

Committed in `4c82bb9` (FIX: state-independent shipped detection + default-on move to Complete). The redesign fixed the two reported failures (missed shipped tickets in Testing/Backlog; tickets never moved to Complete), but the rating flagged two edge gaps:

1. Step 3 discovery greps only `^[0-9]{5}:` commit-subject prefixes, so a ticket whose ID appears only as `(also 54776)` in another ticket's commit subject/body never enters the candidate list. The broader `--grep "$id"` fallback in step 4.3a only runs for already-discovered IDs, so it cannot rescue an undiscovered one.
2. Step 4 shipped-detection passes if *any* matching SHA is in a version tag; a ticket with one shipped commit plus follow-up work still in flight gets marked shipped and default-moved to Complete (Gate D is default-on now, which raises the stakes of this false positive).

## Approach

In `~/.claude/skills/zirtue-release-backfill/SKILL.md`:

1. Step 3: after the prefix grep, add a second pass that greps subjects (and optionally bodies via `--pretty='%s %b'`) for **all** 5-digit tokens, union into `C:/tmp/sc_dev_ticket_ids.txt`. Accept a few false-positive GETs per run (non-ticket 5-digit numbers get 404s or non-matching stories; skip them).
2. Step 4: require **every** discovered SHA for a ticket to be contained in a version tag before classifying it shipped. Mixed (some tagged, some unmerged/untagged) = new status `partially-shipped`: report it in its own bucket, exclude it from Gate D moves, and leave the Release proposal to the tag of the newest tagged SHA with a flag.

Rejected alternative: keeping any-SHA-tagged semantics with a warning only - too weak now that Gate D moves to Complete by default.

## Acceptance

- A synthetic check: a ticket ID appearing only as `(also NNNNN)` in another commit's subject shows up in the discovery list.
- A ticket with one tagged SHA and one feature-branch-only SHA lands in `partially-shipped`, is NOT moved to Complete, and is visibly reported.
- Must not regress: state-independent shipped detection (the 54761/54776 fix), Gate D default-on with opt-out phrase, confidence guard tying medium/low moves to Gate A approval.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - bundled-ID discovery (SKILL.md:117-129) and the partially-shipped bucket (SKILL.md:182-184) both already shipped. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
