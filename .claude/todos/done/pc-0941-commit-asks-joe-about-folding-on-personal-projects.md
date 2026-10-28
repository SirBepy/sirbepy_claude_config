<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 309/368/474/498/500 are all in done/ and are all ALGORITHM refinements of the same check (make it hunk-level, script it, session-scope the answer, define a non-HEAD branch). This one is a dev standing instruction to stop asking at all on personal repos - a policy change, not a fifth narrowing. Their lineage is cited below on purpose. -->
# /commit's unpushed-overlap fold question should never fire on a personal project

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop `/commit` asking Joe whether to fold a commit. On his personal projects the answer is always
"don't fold, just commit", so the question is pure friction and he has now said to drop it.

## Context

Said 2026-09-05, verbatim, mid-session in `windows_taskbar_widgets`:

> stop asking me for my personla projects if i wanna fold or not
> we never have to fold
> we can always just commit
> pls stop

The machinery he is reacting to is `skills/commit/SKILL.md` step 8's **unpushed-overlap check**. On
exit 1 in an interactive session it queues the hit and then asks ONE `AskUserQuestion` at
end-of-queue, offering `/commit fold <sha>` per item or proceed-as-is. Step 1a already keeps a
session-scoped fold-policy so it does not re-ask within a session - but it still asks once per
session, every session, forever.

**This is the fifth todo about that same question being asked too often**, and the first four are
all closed. 368 made it hunk-level instead of file-level. 474 turned it into a script. 498
session-scoped the answer so a multi-commit sweep asks once. 500 gave the non-HEAD case a defined
branch. Each narrowed WHEN it asks; none questioned WHETHER it should ask on a solo repo. That is
the actual signal here - four rounds of tuning a gate whose value on a personal repo was never
established.

Note this session never actually asked: it was an unattended `/auto-do-todos` run, which already
takes the proceed-as-is branch. So the instruction targets the general interactive path, not a
failure that happened here.

Second, softer contributor worth checking: the same session used "fold" in an unrelated
`AskUserQuestion` option label ("Fold into card 89b78b04" - rolling a verification step into a
Todos card, nothing to do with git). That may be what actually triggered the reaction. Either way
"fold" is now a loaded word; prefer "roll into" / "add to" for the non-git sense.

`/commit fold <sha>` as an explicit dev-typed subcommand is NOT in scope and stays as it is. Joe
asked to stop being ASKED, not to lose the ability to ask for it himself.

## Approach

1. In step 8's unpushed-overlap bullet, add a personal-project branch to the exit-1 policy, keyed
   off the signal the rest of the config already uses for "personal project": the repo imports
   `~/.claude/snippets/full-auto.md`. On a personal repo, behave exactly as the unattended branch
   already does - take the genuinely-separate branch, record the overlapping commit/file/blamed
   lines in the commit report, never ask.
2. Keep the interactive ask for client/employer repos (the `gh-account-switch` org set: zirtue-corp,
   Fibo-Studio, revaire, and any other non-`SirBepy` origin), where a shared history genuinely wants
   a human call.
3. Then re-read step 1a: with the personal path never asking, check whether the session-scoped
   fold-policy state is still carrying its weight. It probably still is, for the client repos.
4. `grep -ril "fold" ~/.claude/skills/` and confirm no other skill asks a fold question of its own.

## Acceptance

- A `/commit` on a personal repo with an exit-1 overlap hit produces the commit plus a one-line
  report of the overlap, with no `AskUserQuestion` anywhere in the run.
- A `/commit` in a client-org repo still asks, unchanged.
- `/commit fold <sha>` still works when Joe types it.
- `python ci/run_all.py` clean.

## Notes

- Filed from a `windows_taskbar_widgets` session per root `CLAUDE.md`: the fix edits
  `~/.claude/skills/commit/SKILL.md`, so it belongs in this backlog, not the project's.
- Done 2026-09-05, same day it was filed - Joe said 'do it now'. skills/commit/SKILL.md step 8's unpushed-overlap bullet now has a personal-repo branch that never asks: origin under SirBepy, or no remote, takes the genuinely-separate branch and prints one line, same as the unattended branch. Client/employer repos still ask, and /commit fold <sha> typed by hand is untouched. Verified no other skill asks a fold question; ci/run_all.py clean, all 6 checks.
