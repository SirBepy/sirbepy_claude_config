<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=6, reconfirm-count=2, content-hash=1115c28e -->
<!-- duplicate-checked: 2026-09-29; grepped backlog + done/ for "client-repo", "SirBepy.*origin"; only done/941 and done/433 hit, both predate the client list. -->
# Move the remaining "origin under SirBepy" checks onto the client-repo list

**Type:** task
**Origin:** ai

## Goal
One definition of "client repo" across the config: the list in `refs/client-repos.txt`, read
through `hooks/_client_repo.py`. Plus the per-commit test-coverage check becomes mechanical instead
of prose.

## Context
Since 2026-10-05 the testing floor and push gate apply to every repo; the explicit list
(`refs/client-repos.txt`, `python hooks/_client_repo.py is-client <path>`) now only decides the
client-only rules in `snippets/client-repo.md` (folded tweaks, by-hand e2e on no-suite pushes). Two older checks
still decide it by remote owner, so they now disagree for any repo outside both sets (a
Fibo-Studio repo is personal for testing but "client/employer" for fold asks):

- `skills/commit/SKILL.md` step 8, overlap-check branch 2 ("Personal repo - never ask"):
  `origin` under `SirBepy` or no remote.
- `skills/cleanup-todos/SKILL.md` worth rubric (~line 161): names zirtue-corp, Fibo-Studio,
  revaire as client/employer orgs.

`hooks/gh-account-switch.sh` also maps by org, but that is account selection, a different concern:
leave it alone.

Separately, `/commit` step 6b's test-coverage check ("pathspec changes non-test source files and
touches no test file") is prose only. `/rate-it` on 2026-09-29 scored the prose-only gates 6/10;
the push half is now hook-enforced, the commit half is not.

## Approach
1. Ask Joe (question card, domain arch) whether fold-ask behaviour should follow the testing list,
   since Fibo-Studio flips from "ask" to "never ask" if it does. Do not change branch 2 without
   his answer.
2. On yes: swap both owner checks for `_client_repo.py is-client`.
3. Add a `coverage-tests` refusal to `skills/commit/commit-pathspec.sh`, active in every repo
   (step 6b is universal since 2026-10-05), overridable with `--force` like the other judgement
   checks, and add it to the script's valid `--force` names.

## Acceptance
- Grep for `SirBepy` in `skills/commit/SKILL.md` and `skills/cleanup-todos/SKILL.md` returns only
  the account-mapping mention, or none.
- `skills/commit/test_commit_pathspec.sh` has a case where a commit touching only `src/x.ts` is
  refused, and passes with `--force coverage-tests`.
- `python ci/run_all.py` shows no new failures versus HEAD.

## Open questions

Written by /auto-do-todos on 2026-10-06 (loop-todos cycle 2). The next run opens with these.

- [ ] [ARCH] Should the /commit fold-ask and the /cleanup-todos worth cap read the shared client-repo list instead of their own `SirBepy` check? Unifying flips Fibo-Studio repos from asking to never asking. Options: unify / keep the two checks separate.
