<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=1, content-hash=08701f74 -->
# hs_addtime.cjs is unwired and hardcoded, so nothing can reach it

**Type:** task
**Origin:** ai

## Goal

Make `skills/clockify-reconciliator/scripts/hs_addtime.cjs` reachable and configurable, or decide
it is not wanted and delete it. Right now it is an untracked 82-line Playwright script that no
documentation references and that only works for one hardcoded project/reason pair.

## Context

The file appeared in the working tree during an earlier session and sat uncommitted. A
`/rate-it-and-commit` pass on 2026-08-19 rated the surrounding batch 6/10 and held this one file
back from the commit for exactly this reason; the other five paths landed as `882d611`, `16abef1`,
`5e20e83`, `88cf6f8`.

What it does: loads a JSON array of `{date, from, to, note}` entries and drives HubStaff's Add-time
dialog per entry (project/reason selects, from/to time inputs, billable toggle, note, save), then
prints a JSON results array with per-entry `ok`/`error`.

Two concrete gaps, both verified 2026-08-19:

- `skills/clockify-reconciliator/hubstaff.md` documents call sites for `hs_preflight.cjs` (line 21)
  and `hs_weekshot.cjs` (line 131), and never mentions `hs_addtime.cjs`. Nothing in the repo
  invokes it. A grep across the backlog found only a passing mention in
  `.claude/todos/372-move-playwright-profiles-out-of-skills.md:59` noting it existed.
- `hs_addtime.cjs:19-20` hardcodes `PROJECT_LABEL` and `REASON_LABEL` as constants, unlike the
  project-config pattern the rest of the skill uses.

It does pass `node --check`, and `comment-noise.sh` / `em-dash.sh` / `secret-scan.sh` are all clean
on it, so the blocker is wiring and configurability, not correctness of syntax.

## Approach

1. Decide with the dev whether bulk add-time is wanted at all. It writes to a live HubStaff
   account, so a broken run is not free.
2. If wanted: move `PROJECT_LABEL` / `REASON_LABEL` to the same config source the rest of the
   skill reads, so it is not single-account.
3. Add a call-site section to `hubstaff.md` matching the shape used for `hs_preflight.cjs` and
   `hs_weekshot.cjs`, including the JSON input shape.
4. Validate it against a real run before documenting it as working. Do not write the doc entry
   first: that asserts behaviour nobody has observed.
5. If not wanted: delete the file and note the decision here.

Rejected: committing it as-is with a "not wired yet" note. An undiscoverable script in a skill
directory is the thing that rots.

## Acceptance

- `hubstaff.md` names the script with a real, executed call site, or the file no longer exists.
- No hardcoded account-specific label constants remain in the script.
- The file is either tracked in git or gone. It does not stay untracked.

## Notes

- Related: `372-move-playwright-profiles-out-of-skills.md` touches the same two scripts and asks
  future editors to re-read them first.
