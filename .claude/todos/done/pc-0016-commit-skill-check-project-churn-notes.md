<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=5, reconfirm-count=2, content-hash=0f6e8218 -->
# /commit skill should surface known project formatting-churn notes before running the hook

**Type:** skill-improvement
**Origin:** ai

## Goal
Stop `/commit` from silently running a whole-file-reformatting pre-commit hook on a surgical diff when this exact failure mode is already documented for the repo.

## Context
2026-07-11: ran `/commit` on a 2-file, 20-deletion diff (`RegisterPage.tsx`, `authApi.ts`) in the Fibo frontend. The repo's husky + lint-staged pre-commit hook ran `prettier --write` on the staged files and reformatted them wholesale (quote style, reflow), ballooning the commit to 128 insertions / 109 deletions of pure churn â€” on a diff whose entire point was to be small and reviewable (it was a redo of PR #113, which got closed specifically *for* carrying this kind of unrelated churn).

This exact issue is already captured in memory `fibo-frontend-precommit-prettier-churn.md`: husky reformats whole FE files, CI doesn't check formatting, fix is `git commit --no-verify` for surgical FE commits. The memory existed and was even read earlier in the session for unrelated reasons â€” but `/commit`'s own procedure has no step that checks for a project-specific "this hook causes churn, prefer --no-verify" note before staging/committing. Had to `git reset --soft`, restore both files from `origin/develop`, reapply the two edits, and recommit with `--no-verify` to get a clean commit.

## Approach
Add an optional step to `commit/SKILL.md` between "check for project-level overrides" and "stage/commit": check for a project note (e.g. `.claude/commit-style.md` entry, or a documented memory pattern) that says a pre-commit hook reformats beyond the staged diff, and if present, default to `--no-verify` for diffs under some size threshold (or at least ask). This is Fibo-specific today but the mechanism (a repo can declare "our hook over-reformats, prefer --no-verify for small diffs") is general enough to live in the skill rather than requiring the AI to remember it per-repo, per-session.

## Acceptance
- `/commit` on a small, surgical Fibo frontend diff produces a clean commit (no reformatting churn) without requiring the operator to manually reset/restore/recommit.
- The skill's own logic (not session memory) is what triggers `--no-verify` or the equivalent â€” a fresh session with no prior memory of this issue should still avoid the churn.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 86; renumbered to 16 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: extend `commit/SKILL.md` step 1 - after the existing `.claude/commit-style.md`
  override check, also look for a documented "pre-commit hook reformats beyond the staged diff"
  note, and if present follow the `--no-verify` authorization and threshold exactly as that project
  file states them. Absent such a note, change nothing and never silently bypass a hook. This
  resolves both of the todo's open sub-questions without inventing a global threshold number. This
  was produced by a strict second-pass re-triage that specifically asked whether a defensible answer
  exists without the dev; it concluded yes. Not executed only because the session ended.
- completed, commit 0796403
