<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no todo mentions verifiers running e2e or shared-database suites -->
# outbound-verify: 3 parallel verifiers re-ran a DB-writing e2e suite at once and produced false FAILs

**Type:** skill-improvement
**Origin:** ai

## Goal

`refs/outbound-verify.md`'s verifier template should stop parallel verifiers from running commands that mutate shared state, and should warn them about timestamp timezones when they compare DB rows against local-time artifacts.

## Context

2026-10-13, zng-admin session fb06a166, verifying the zng-api PR text for sc-56125 (PR #914). The draft claimed "core e2e 272 passed". All 3 verifiers ran `npm run test:e2e:core` at the same moment against the one shared local Postgres. They collided on unique constraints and reported 20, 18 and 1 failures, so all three FAILed. A solo run earlier in the session had been 272/272.

The same e2e runs also inserted loans dated "today". Two verifiers then concluded that the admin UI total in a screenshot ($8,325, taken 15:47 local) "left out a biller". They had compared `created_at` (UTC, 15:36 UTC = 17:36 local) against the screenshot's local file time, so the rows they counted were created after the screenshot. The claim was cut and the PR shipped on round 3, but two rounds were burned and Joe was asked to re-approve.

## Approach

In `refs/outbound-verify.md`'s template, add two lines near the pointers:
1. "Do not run anything that writes to a shared resource (an e2e suite against a shared database, a deploy, a migration). Three of you run at once. If a claim can only be checked that way, mark it UNVERIFIABLE and say so."
2. "DB timestamps are usually UTC. Convert before comparing them to local file times or screenshots."

On the main-agent side (same file, step 1 "Freeze the text"): prefer cutting a claim that only a shared-state run can verify, rather than letting three verifiers re-run it.

## Acceptance

- The template contains both lines.
- A dry read of the template shows no pointer that invites running a DB-writing suite.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): verifier template forbids writes to shared resources (mark UNVERIFIABLE), adds the UTC conversion line and a Freeze-the-text cut for shared-state-only claims. Hook tests ALL PASS before and after.
