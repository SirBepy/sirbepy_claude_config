<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=ceaf3b2d -->
<!-- duplicate-checked: grepped this backlog for "Product Area", "custom-fields" and "WebApp: Loan Creation" on 2026-09-24 - no hits. -->
# `skills/ticket/shortcut.md`'s pinned Product Area table is missing most of the ZNG values, including `WebApp: Loan Creation`

**Type:** skill-improvement
**Origin:** ai

## Goal

A `/ticket` create against a zng-app loan-flow ticket picks the Product Area value from the pinned
table instead of spending an extra `GET /api/v3/custom-fields` round trip to rediscover it.

## Context

Surfaced 2026-09-24 filing sc-55997 (`FE: Read loan limits from the loan configuration endpoint`)
from a zng-app session. Filed here rather than in zng-app because the fix edits this repo's
`skills/ticket/shortcut.md`, per `CLAUDE.md`'s rule that a todo belongs in the backlog of the repo
it changes. The project session did not edit the skill.

`shortcut.md`'s "Pinned custom fields" table lists only three `ZNG: Product Area` values (`WebApp:
Billers, RPPS, Billing Accounts`, `WebApp: Global`, `AP: Billers`), while the repo-to-field mapping
table immediately below it names `WebApp: Loan Creation` as a per-feature option with no UUID pinned
anywhere. So the mapping table points at a value the pinned table cannot supply.

`GET /api/v3/custom-fields` returned 21 live values on field `6881002d-700f-4bb7-b919-6cf8880ccdb9`
(read 2026-09-24). The one needed was:

- `WebApp: Loan Creation` - `688101d5-2fd8-4ffb-a0c1-9b8f6a53048c`

Also worth noting: the pinned table's `AP: Billers` label is stale. The live value at
`6977aec4-d5e1-4c55-a993-32a33bba368b` is now named **`AP: Billers & Partners`** - same UUID, renamed
label.

## Approach

1. Re-run `GET /api/v3/custom-fields` to get the current list rather than trusting the values quoted
   above, since labels have already drifted once.
2. Pin the WEB APP block in full (the `---- WEB APP----` separator rows are noise, so skip those) and
   the AP block in full, on field `6881002d-700f-4bb7-b919-6cf8880ccdb9`. The second, legacy
   `Product Area` field `6216069e-704d-41d3-8ea9-a47d2cb80170` (Mobile / P.Portal / Dotcom values) is
   not used by any current zng ticket - leave it out rather than doubling the table.
3. Fix the `AP: Billers` label to `AP: Billers & Partners`.
4. Keep the "Missing value_id?" escape hatch paragraph; it stays correct.

## Acceptance

- `skills/ticket/shortcut.md` pins a `ZNG: Product Area` value for every option its own repo-to-field
  mapping table names, `WebApp: Loan Creation` included.
- `python ci/run_all.py` passes after the edit.

## Notes

- 2026-10-02 (zng-admin session, during `/ticket` creates for sc-56209..56212): partially done by
  following `/ticket`'s own "fix the pinned section in the same session" rule. `shortcut.md` now has:
  the `AP: Billers & Partners` rename (step 3 done), `AP: Users` `6977ae32-566a-466d-baa0-0c3a2862ab9e`,
  `WebApp: Banking & Payments` `688101d5-e043-4e09-b87a-bd478a78a6bb`, Technical Area `Biller Portal`
  `6a0366ad-d4ea-407a-bec3-d1aa9c11e99f`, and the Q4'26 iteration `56183`. `WebApp: Loan Creation` is
  still not pinned.
- Two contradictions to resolve while here:
  1. "Always send all five" custom fields cannot hold for zng-biller: the mapping table says Product
     Area "usually none", and there is no Biller Portal value on the field (live list read
     2026-10-02 has only WEB APP and ADMIN PORTAL blocks). sc-56212 was filed with 4 fields. Reword
     to "all five, except Product Area when no value fits".
  2. `/ticket` tells the session to edit `shortcut.md` in place, but root `CLAUDE.md` forbids global
     `~/.claude` work from a project session unless Joe says so. The 2026-10-02 edits followed the
     skill. Decide which wins (likely: pinned-value refreshes are exempt, or the skill files a todo
     here instead of editing) and state it in one of the two files.
