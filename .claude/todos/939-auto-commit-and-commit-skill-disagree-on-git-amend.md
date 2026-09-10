<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=8, reconfirm-count=1, content-hash=3c3df184 -->
<!-- duplicate-checked: 917 is about marker files accumulating, 933 is about range computation. Neither touches the amend rule. -->
# auto-commit.md and commit/SKILL.md disagree on whether --amend is allowed

**Type:** skill-improvement
**Origin:** ai

## Goal

Resolve the direct contradiction between the two documents so a session does not have to pick one.

## Context

Two always-loaded-or-once-per-session documents say opposite things:

- `snippets/auto-commit.md:46`: "Never `git commit --amend` or `git rebase` interactively. Always new
  commit on top OR the atomic `update-ref` fold below, nothing else." Line 41 repeats it: "never
  amend."
- `skills/commit/SKILL.md:66`, inside step 8's staged-pathspec coverage check: "Recovery if a
  half-committed move already landed: `git commit --amend --no-edit -- <both paths>`, which only
  works before anything else lands on top of it."

`auto-commit.md` states its ban without a carve-out, and its own scope line says the policy "governs
committing only", which reads as covering exactly this. A session that has read both is left to
guess.

Observed 2026-09-05 in a `server_supervisor` `/mega-todos` run: a `CHORE: bump tauri_kit` commit was
made, then `src-tauri/Cargo.lock` turned out dirty from the same submodule update and belonged in
that commit. The session used `git commit --amend --no-edit -- vendor/tauri_kit src-tauri/Cargo.lock`
on the strength of SKILL.md:66's wording. The result was correct (unpushed, no peers, pathspec form
so only those two paths were rebuilt) but it violated auto-commit.md as literally written, and the
session had to report the violation to the dev rather than being able to point at a rule.

Note the case was ADJACENT to SKILL.md:66's, not identical: it was "a file that belonged in the
commit I just made", not "a half-committed `git mv`". So even the permissive document does not
actually sanction it, which is the second half of the gap.

## Approach

Pick one and make both files agree:

- Narrow `auto-commit.md`'s ban to "never amend a commit you did not make this session, and never to
  edit a message", explicitly permitting the pathspec-scoped `--amend --no-edit -- <paths>` form when
  the commit is HEAD, unpushed, and nothing has landed on top. Then say so in one line in
  `commit/SKILL.md` too, so the permission is discoverable from either entry point; or
- Keep the ban absolute and rewrite `commit/SKILL.md:66`'s recovery to use the same atomic
  `update-ref` fold `auto-commit.md` already prescribes, so there is exactly one sanctioned mechanism.

Whichever is chosen, also state what to do for the adjacent case above (a file that should have been
in the commit just made), since neither document currently covers it and it is the common one.

## Acceptance

- `grep -rn "amend" ~/.claude/snippets/ ~/.claude/skills/commit/` returns statements that agree.
- The chosen rule names the exact preconditions (HEAD, unpushed, nothing on top, pathspec form) rather
  than a bare allow or ban.

## Notes

Filed 2026-09-05 by `/respawn`'s retrospective, from a `server_supervisor` `/mega-todos` run.
