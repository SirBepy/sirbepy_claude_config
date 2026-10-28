<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=09b260fe -->
# /pickup and /next-ai-prompt handoff cleanup contradicts gitignored .for_bepy

**Type:** skill-improvement

## Goal

Make the handoff-file lifecycle in the pickup/next-ai-prompt skill pair consistent with `.for_bepy/` being gitignored: plain-delete, never `git rm`/commit.

## Context

In the 2026-07-13 Fibo session, `/pickup` step 5 says `git rm .for_bepy/NEXT_AI_PROMPT.md` then `/commit` - but `.for_bepy/` is gitignored in this repo (and the `dont-stage-for-bepy` memory forbids committing it), so the file is untracked and `git rm` errors with "did not match any file(s) known to git" (hit live this session). `/next-ai-prompt` step 3 has the mirror problem: "The caller is responsible for staging and committing the file... /close Phase 5 commits it." The session worked around it with a plain `Remove-Item`.

## Approach

- `C:\Users\tecno\.claude-fibo\skills\pickup\SKILL.md` step 5: replace the `git rm` + `/commit` instruction with: check `git ls-files --error-unmatch` first; if untracked (the normal case - `.for_bepy/` is usually gitignored), plain-delete the file and skip the commit; only `git rm` + `/commit` if it is actually tracked.
- `C:\Users\tecno\.claude-fibo\skills\next-ai-prompt\SKILL.md` step 3: qualify the "caller commits it" note the same way (commit only applies when `.for_bepy` is tracked, e.g. night-run repos that version it).

## Acceptance

- A /pickup run in a repo with gitignored `.for_bepy/` completes cleanly with no git error and no commit attempt.
- A repo that DOES track the handoff file still gets the rm+commit path.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 102; renumbered to 19 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: closed with no code change. Premise is moot: `pickup/SKILL.md` was fully rewritten as a PLAN.md picker (commit 6a976ad, 2026-07-15) and no longer has a NEXT_AI_PROMPT.md handoff-cleanup step at all; `next-ai-prompt/SKILL.md` was deleted outright in the 2026-08-01 skill audit (commit d67421e) and exists nowhere in the tree. The handoff artifact today is a todo file under `.claude/todos/`, which per `close/ai-todos-format.md`'s Git policy is gitignored by default and never `git rm`'d/committed - the contradiction this todo describes cannot occur under the current architecture.
