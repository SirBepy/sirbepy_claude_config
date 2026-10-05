<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=bf912aa8 -->
<!-- duplicate-checked: grepped this backlog and done/ for "gh pr list", "ground check", "ground-check" on 2026-09-29. Only hit for "gh pr list" is done/445 (PR title convention, unrelated). 1002 is the adjacent live todo and covers verdict LOGIC once the queries return honest data; this one covers query 1 returning dishonest data. Folded the overlapping half into 1002 rather than restating it here. -->
# Ground check query 1 reads CLEAN when `gh` cannot resolve the repo, because `gh pr list --search` returns `[]` instead of failing

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-29
**Priority:** High

## Goal

`refs/outbound-ground-check.md`'s query 1 cannot report CLEAN on a `gh` invocation that never
reached GitHub. Either the recipe proves the repo resolved first, or an unresolvable repo is an
explicit UNVERIFIED verdict, never a clean one.

## Context

Surfaced 2026-09-29 filing sc-56121 from a zng-admin session. Filed here because the fix edits this
repo's `refs/outbound-ground-check.md`; the project session did not touch the ref.

Query 1 as written (read 2026-09-29) is:

```bash
gh pr list --state merged --search "<claim>" --limit 10 --json number,title,mergedAt,files
gh pr list --state open   --search "<claim>" --limit 10 --json number,title
```

Run from `C:\Users\tecno\Desktop\Projects\zng-api`, whose origin is the SSH alias
`git@github-work:zirtue-corp/zng-api.git`, all three search variants returned exactly `[]`. Read as
CLEAN. It was not clean: a bare `gh pr list --state merged --limit 5` from the same directory failed
with

```
GraphQL: Could not resolve to a Repository with the name 'zirtue-corp/zng-api'. (repository)
```

`gh auth status` confirmed the correct account (`JosipMuzicZirtue`) was already active, and
`gh repo view zirtue-corp/zng-api` succeeded, so this is not the account-switch hook failing and not
a permissions problem. Adding an explicit `-R zirtue-corp/zng-api` made the same searches return
real results immediately, including the PR that the honest run needed to surface (#833, merged
2026-09-22, which then became the hard stop discussed in
[[1002-ground-check-hard-stop-fires-on-the-be-half-of-a-be-fe-pair]]).

**Why this is the dangerous shape.** `--search` hits GitHub's search API, which answers an
unresolvable repo qualifier with an empty result set rather than an error, while the plain list path
surfaces the GraphQL failure. So the failure mode is silent and inverted: the query that the recipe
tells you to run is the one that cannot tell you it failed, and its failure output is
byte-identical to a genuine all-clear. Every downstream consequence then follows from a false
premise, and the marker gets written.

Root cause of the resolution failure itself is UNVERIFIED and secondary: most likely `gh` parsing
the `github-work` SSH host alias, since `git@github-work:` is not `github.com`. Worth confirming,
but the recipe should be robust to it either way rather than depending on the answer.

## Approach

1. In `refs/outbound-ground-check.md`, make query 1 pass an explicit `-R <owner>/<repo>` resolved
   from the origin remote rather than relying on cwd inference. The owner is already parsed for the
   `gh` account mapping in `hooks/gh-account-switch.sh`, so the same `case "$remote" in` shape works.
2. Add a resolution proof before the searches, so an unreachable repo cannot look empty:
   `gh repo view <owner>/<repo> --json name` must succeed first. On failure, query 1's verdict is
   **UNVERIFIED**, not CLEAN, and the report line says so.
3. State in the Verdict section that an UNVERIFIED query 1 does not block the write, but must appear
   verbatim in the report line, since the honest limitation is the whole point of that line.
4. Check whether any other skill runs `gh ... --search` and reads empty as authoritative
   (`grep -rn "gh pr list" ~/.claude/skills ~/.claude/refs`), and fix those call sites the same way
   in the same pass.
5. Optionally confirm the SSH-alias root cause with `gh repo view` from a repo whose origin is a
   plain `github.com` URL versus an aliased one, and record the answer in the ref as a one-line
   gotcha so the next session does not re-derive it.

## Acceptance

- Query 1 in `refs/outbound-ground-check.md` resolves the repo explicitly and cannot report CLEAN
  without a successful `gh repo view`.
- The Verdict and report-line sections both name UNVERIFIED as a possible query-1 outcome.
- A grep shows no remaining `gh ... --search` call site in `skills/` or `refs/` that treats an empty
  result as proof of absence.
- `python ci/run_all.py` passes after the edit.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), lane K: refs/outbound-ground-check.md. Doc change; the owner/repo sed was proven live against this repo's own origin (one-pass form failed on owner/repo.git, two-pass form resolves).
