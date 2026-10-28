<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 1128/26/281/327/333 share only generic words; none covers create-pr detecting an existing PR for the same head or ticket -->
# create-pr precondition misses a PR already merged for the same ticket

**Type:** skill-improvement
**Origin:** ai

## Goal

`/create-pr` step 1 must stop before drafting when the ticket the branch encodes already has a merged (or open) PR from someone else, or the base branch has moved past the branch's fork point with a commit for the same ticket.

## Context

2026-10-12, revaire-mobile, REV-7305 (session 7b6eec86). Claude branched `rev-7305-a-fast-tap-after-choosing-shares-can-open-the-full-aircraft` from develop `d7b110ba` at about 14:10 local, fixed the bug, ran tests, an emulator repro and verification, committed `a4a701d6`, and ran `/create-pr`. Meanwhile Justin opened and merged PR #1140 for the same ticket from the SAME head branch name (created 13:36Z, merged 13:43Z, develop moved to `fadc618b`).

`/create-pr` step 1 ran `gh pr view` for the branch and got "no pull requests found", because `gh pr view <branch>` only resolves open PRs. The duplicate was caught only by an outbound-verify subagent that compared `d7b110ba...develop` through `gh api compare`. Two drafting rounds and six verifier agents were spent on a PR that should never have been drafted. In Revaire repos `git fetch` silently 404s (wrong account), so local `origin/*` refs cannot show the move either.

## Approach

In `skills/create-pr/SKILL.md` step 1 (Preconditions), add two cheap single-line checks:

- `gh pr list --head <branch> --state all --json number,state,author,mergedAt` - any MERGED or OPEN PR from this head that is not this session's: stop and tell the dev.
- When the branch name or commits carry a ticket id: `gh pr list --search "<TICKET-ID>" --state all --json number,title,state,author` - same stop rule.
- Optionally `gh api repos/<owner>/<repo>/compare/<fork-point>...<base> --jq .ahead_by` to report how far the base moved, since local remote refs can be stale.

## Acceptance

Re-running the 2026-10-12 shape (a merged PR #1140 on the same head name and ticket) makes `/create-pr` stop at step 1 with a message naming the existing PR, before any drafting subagent or verifier is dispatched.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): create-pr preconditions add gh pr list --head --state all and a ticket-id search, stopping on any merged or open PR not from this session. Prose only, not exercised live.
