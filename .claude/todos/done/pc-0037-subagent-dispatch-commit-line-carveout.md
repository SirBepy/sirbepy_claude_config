<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=92ba09eb -->
# Clarify subagent-dispatch commit-prohibition line for zero-git tasks

**Type:** skill-improvement

## Goal

The global rule (`~/.claude-personal/CLAUDE.md` "Git Commits" section, backed by
`~/.claude/snippets/auto-commit.md` and `~/.claude/refs/process-hygiene.md`) says every subagent
dispatch prompt, foreground or background, MUST include verbatim: "Stage your changes but do NOT
commit. The main agent will run `/commit` after your report-back." No stated exception. Decide
whether that instruction should get an explicit carve-out for dispatches that touch zero
git-tracked files, and if so, add it to the source snippet/ref (not just this todo).

## Context

2026-07-31, `feature/frontend2-standup` session (Fibo `frontend2` package). Dispatched a
`general-purpose` subagent (model: sonnet, foreground) to audit and fill gaps in a `.for_bepy/`
handoff file - `.for_bepy/` is gitignored scratch space, and the task involved zero commits, zero
staged files, nothing git-tracked at all. I omitted the mandatory verbatim commit-prohibition line
from that dispatch prompt on the reasoning that it plainly didn't apply (nothing to stage or
commit). That's a literal violation of a MUST-include rule via my own judgment call rather than
the rule's own stated exception - the rule as currently written has none. No harm resulted this
time (the subagent correctly did not run any git commands), but it's the same class of gap called
out elsewhere in personal memory: [[feedback-apply-project-directive-over-generic-heuristic]]
("read the directive already in memory" - i.e. don't substitute your own reasoning for an explicit
MUST when the directive doesn't itself carve out the exception).

## Approach

Two options, pick one when this is picked up:
1. Add an explicit carve-out to the source snippet(s): "Skip the commit-prohibition line only when
   the dispatched task provably touches zero git-tracked paths (e.g. writing to a gitignored
   scratch dir like `.for_bepy/`, or `.claude/todos/` itself) - state that reasoning inline in the
   dispatch prompt so it's auditable, don't silently omit."
2. Or: keep the rule absolute (always include the line, even when inapplicable) since a static
   boilerplate line costs nothing and removes the judgment call entirely - simpler, zero-cost,
   removes the recurring "does this apply here?" question every dispatch.

Recommend option 2 (always include, no exception) unless the dev has a reason to prefer the
carve-out - a static line is cheaper than maintaining a judgment-call exception across every
future session.

## Acceptance

- The relevant global snippet/ref file states one clear rule with no ambiguity left for a future
  session to reason about case-by-case.
- Whichever option is picked, update `~/.claude/snippets/auto-commit.md` and/or
  `~/.claude/refs/process-hygiene.md` (wherever the MUST-include instruction actually lives -
  confirm exact file before editing, this todo didn't grep for it).

## Notes

This is a personal/global tooling rule, not a Fibo-repo-specific one - the fix (if made) lands in
`~/.claude/` files, outside this repo's git history entirely. Low priority, no user-facing impact
- 2026-08-08: implemented option 2 (absolute, no carve-out). Added a one-line clarification to `refs/delegation-doctrine.md:46-49`, in the existing "Every builder prompt embeds, without exception" bullet that defines the verbatim commit line - state the line even when the dispatch touches zero git-tracked files. Left it as a single clarification, not a second statement of the rule.
this time.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 182; renumbered to 37 per the max+1 id rule. Confirmed by dev 2026-08-07.
