<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=4, reconfirm-count=1, content-hash=cf31994d -->
<!-- duplicate-checked -->
# Adversarial review is a documented habit, but every reviewer is the same model

**Type:** task
**Origin:** ai

## Goal

Get a genuinely independent second opinion by delegating a review to a different model's CLI, instead
of asking Claude to disagree with Claude.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

There is an established habit here of adversarial validation on consequential decisions: an auto-memory
entry records that big retire/replace/architecture calls get a rate-it/iterate-it panel first rather
than quick agreement, and CLAUDE.md's subagent rules allow escalating to a top-tier verifier on
high-stakes diffs. **Every one of those reviewers is a Claude model.** Shared training means shared
blind spots, which is the one failure mode a panel of siblings cannot cover, however many members it
has. Todo 421 is about fixing panel structure; this is about panel diversity, and they are
independent.

Two reference implementations:

**`ZacheryGlass/.claude` `gemini-agent`** (`repos/ZacheryGlass_.claude/skills/gemini-agent/scripts/gemini_interface.py`)
- headless Gemini CLI delegation. Passes a persona via `--system-md` with frontmatter stripped, injects
files via `--context-file` using `@file` syntax, and supports background runs so a second opinion can
be fetched in parallel with continuing work.

**`okhlopkov.com` write-up** (cited by the community scout) - Claude drafts a plan, then sends it to a
**Codex MCP server** for independent review. Same idea via MCP rather than a CLI shell-out, which is
architecturally cleaner but needs a running server.

Anthropic's own documented Writer/Reviewer pattern is the same instinct one step weaker: two Claude
sessions, one implementing and one reviewing with fresh context. Fresh context removes
self-justification bias but not model bias.

Honest counterweights, because this is the least certain todo in the set:

- It requires a second vendor's CLI installed and authenticated, which is real setup and a real
  dependency. The package-safety rule in CLAUDE.md applies before installing anything.
- The `serpro69/claude-toolbox` repo in the corpus is multi-provider (Claude plus Codex) and is worth
  reading for how someone structures a genuinely two-provider setup, rather than bolting one call onto
  a Claude-shaped workflow.
- A second model's review is only useful if its verdict is actually weighed. A cross-model reviewer
  whose output gets skimmed and dismissed is pure cost. Deciding where its verdict is load-bearing is
  the harder half of this todo, and it is a genuine fork for the dev, not something to settle silently.

## Approach

1. Decide the mechanism before building: CLI shell-out (like `gemini-agent`) or MCP server (like the
   Codex pattern). CLI is simpler and has no running process to manage, which suits this environment's
   process-hygiene rules. MCP is cleaner but adds a server to supervise. Recommend CLI first.
2. Decide the provider. Whichever is chosen goes through the package-safety check in CLAUDE.md first,
   including the resolved-tree advisory check if it installs via npm or pip.
3. Read `repos/ZacheryGlass_.claude/skills/gemini-agent/` for the persona-passing and file-injection
   mechanics, and skim `repos/serpro69_claude-toolbox/` for how a real two-provider setup is shaped.
4. Scope the first use narrowly to one decision type where the verdict genuinely matters and the cost
   of being wrong is high. Candidates, in order: a `/rate-it` panel member on architecture or
   retire/replace calls (the exact case the memory entry describes), a second reviewer on
   security-touching diffs, or a plan reviewer before a large refactor. **Pick one.** A general-purpose
   "ask the other model" skill with no defined role will not get used.
5. Define what happens on disagreement, before building. This is the part that makes it real: if the
   cross-model reviewer dissents, does that block, surface a question card, or just get logged? An
   unanswered disagreement protocol means the reviewer is decorative.
6. Respect process hygiene: no orphaned CLI processes, explicit timeout, and an orphan check, per
   `refs/process-hygiene.md`. A backgrounded second-opinion call is exactly the shape that leaks
   processes.

## Acceptance

- One cross-model review path works end to end, with the real output of an actual review pasted.
- The disagreement protocol is written down and demonstrated on one real case where the two models
  differ. If they never differ on the test cases, say so plainly, because that is itself the finding
  and it would mean the whole idea is not paying for itself.
- The second CLI or server passed the package-safety check, with the check's output recorded.
- No orphaned processes after a review, proven with real process output.
- The scope is one named decision type, not a general-purpose escape hatch.

## Notes

This is the most speculative todo in the harvest set and the easiest to over-build. If step 5's
disagreement protocol cannot be answered convincingly, the honest outcome is to close this without
building it, and that is a legitimate result rather than a failure.

Do not wire this into `/rate-it` as a silent extra panel member. Cross-vendor calls send code to
another provider, which is a decision the dev makes explicitly, not a default that appears in a
skill.
