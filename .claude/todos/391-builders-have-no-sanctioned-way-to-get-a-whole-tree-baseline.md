<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=aacfef3b -->
# A builder needing a whole-tree "before" measurement has no sanctioned mechanism, so it reaches for `git stash`

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `refs/builder-preamble.md` a named, safe way to take a pre-change baseline of something that is
not a single file, so a builder stops improvising with `git stash` in a tree other agents are
working in.

## Context

Real incident, 2026-08-19, `hubbub`, during a `/auto-do-todos` run with two builders live in one
tree.

A builder was told to add a dev dependency and, per global CLAUDE.md's package rule, to run
`pnpm audit` against the **resolved** tree post-install. To tell a pre-existing advisory from one it
had just introduced, it needed the audit output from before its own change. It ran `git stash`, then
`git stash pop`.

That stash swept a concurrent builder's uncommitted edit to
`hubbub/.claude/skills/create-game/SKILL.md` along with its own work. It popped it back and
self-reported the violation in its report, and the orchestrator verified the other agent's commit
(`1131328`) kept its full content, so nothing was lost this time. It was luck, not design: a stash
is whole-tree, so the blast radius was every dirty file in the repo, not just the builder's own.

**The preamble already bans it.** `refs/builder-preamble.md`'s static block says:

> Never run `git stash`, `git reset`, or `git checkout` on paths you don't own [...] To compare
> against clean state, use `git show HEAD:<file>`.

The ban is clear and the builder broke it. But the sanctioned alternative it offers, `git show
HEAD:<file>`, only answers a **single-file** question. It cannot produce "what did `pnpm audit` say
before my change", "what was the bundle size before", or "how many tests passed before" - all of
which are whole-tree measurements, and all of which are things dispatches routinely ask for. So the
rule bans the only obvious mechanism and names a replacement that does not cover the case. A builder
that hits it either violates the ban or silently drops the baseline, and dropping it quietly is the
worse of the two.

Related but distinct: [[377-commit-pathspec-blind-to-peer-working-tree-hunks]] is about a peer's
dirty hunks inside a file you deliberately name at commit time. This one is about a builder
destroying peers' work before it ever gets to a commit, for a reason the doctrine did not anticipate.

## Approach

Add a short "Taking a baseline" clause to `refs/builder-preamble.md`'s static block, next to the
existing stash ban so the ban and its alternative are read together. Options to weigh, cheapest
first:

- **Order of operations.** For most measurements the baseline can simply be taken FIRST, before the
  builder edits anything. `pnpm audit` before installing, test counts before writing the test. This
  costs nothing and needs no git surgery. It is probably the whole fix, and it should be stated as
  the default.
- **`git worktree add` to a scratch path** for the genuinely-need-a-clean-tree case. Isolated by
  construction, touches nobody else's files. Note the cost, it is a second install for a Node repo,
  which may not be worth it.
- **The orchestrator supplies the baseline** in the dispatch prompt, measured before any builder is
  launched. Fits the delegation doctrine's existing "spec pack" idea and is free when the
  orchestrator was going to run the command anyway.

Whichever wording lands, state the rule as: **a baseline is taken before you edit, never recovered
by rewinding a shared tree.** Also mention this explicitly in `delegation-doctrine.md`'s "Every
builder prompt embeds" list if a dispatch asks for a before/after comparison, so the orchestrator
knows it owes the builder either the number or the ordering instruction.

## Acceptance

- `refs/builder-preamble.md` names at least one sanctioned way to take a whole-tree baseline,
  adjacent to the stash ban.
- The guidance covers a measurement that is not file-scoped, since `git show HEAD:<file>` already
  covers the file-scoped case and is what left this gap.
- A cold builder reading the block can tell what to do when asked for a before/after comparison,
  without inventing a mechanism.

## Second case, 2026-08-24 (`claude_usage_in_taskbar`)

`git show HEAD:<file>` does not cover proving a new regression test RED either: a test runner has
to IMPORT the old version from its real path, and `git show` only writes to stdout. The workaround
used twice that session was `cp <file> <scratch> && git checkout HEAD -- <file> && <test> ; cp
<scratch> <file>` - single-file, so no stash blast radius, but still an improvised rewind of a
tracked path in a shared tree. Whatever sanctioned mechanism this todo lands on should name the
red/green case, not just the whole-tree measurement one.

## Notes

Filed from a `hubbub` session per global CLAUDE.md's rule that a finding about the global tree goes
in the global backlog. No global files were edited from that session.
