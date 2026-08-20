<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Four more CLAUDE.md rules worth taking from the harvest

**Type:** task
**Origin:** ai

## Goal

Adopt the four remaining transferable rules found in production AGENTS.md files, each of which sharpens
a rule already present here rather than adding a new obligation.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). Todo 429 covers the
Timeless Present comment rule and strength-tagged bullets. These are the remaining four.

**1. The Evidence Rule, applied to the agent's own codebase claims** (`biomejs/biome`, 431-line
AGENTS.md). Never assert that a function, behavior or pattern exists without proof, meaning a file path
plus a line number or a snippet, or explicitly say the claim is unverified.

CLAUDE.md already has this rule twice, and both times scoped elsewhere: once for asserting "X causes Y"
about a system not read this session, and once for **outbound** text Joe sends as his own words. Biome
applies it to the agent's claims about the codebase it is working in, which is the half that is missing
and, per this repo's own history, the half that keeps failing. The recorded incident is five recurrences
in one project despite being memory-documented after each one.

**2. "Document deferred work explicitly"** (`repos/serpro69_claude-toolbox/.claude/CLAUDE.extra.md`).
"A 'we'll fix it later' note that lives only in chat is lost the moment the session ends... Explicit
partial > silent postpone", with a required durable-location list (inline TODO/FIXME, a wip doc, a
tasks file).

The todos backlog is that durable location and it is well-developed, but nothing forces writing to it
**at the moment of deferring mid-task.** The current trigger is `/close`, `/code-check` or an explicit
`/create-todo`, all of which happen after the fact. The gap is the mid-task "I'll leave that" that
never reaches a file.

**3. Numeric ratchets** (`openai/codex`, 322-line AGENTS.md). "Unless mechanical, changed lines should
not exceed 800 (500 for complex logic changes)" and "no context item larger than 10K tokens, items
greater than 1K tokens are P0 and need manual review."

CLAUDE.md's equivalents are qualitative: "every changed line must trace to the request", "no drive-by
refactors". The comment rule is the one place a number already exists (2 lines typical, 4 hard, 25%
ratio) and it is also the most reliably enforced style rule here, which is the argument for numbers.

**4. A scoped "Ask First" allowlist** (`prisma/prisma`). Prisma names exactly two triggers requiring
confirmation instead of a general "ask when unsure".

This one cuts against current practice and needs care. CLAUDE.md's front-load rule is deliberately
broad ("Front-load all questions before starting work, trivial or not") and was written that way on
purpose, with a documented incident behind it. So this is not "replace the broad rule" but "name the
categories that always qualify", which would help a session recognise a fork it might otherwise miss.
Treat it as additive, and if it cannot be made additive, skip it.

## Approach

1. Adopt (1) and (2) first. Both are small, both sharpen existing rules, and neither conflicts with
   anything.
2. For (1), extend the existing unverified-claim rule rather than adding a second rule about evidence.
   Two rules about citations in one file is how a rule set gets ignored. The extension is that
   codebase claims need a `file:line` read this session, same standard as the outbound rule.
3. For (2), consider whether it needs teeth beyond prose, given that prose-only rules have a poor
   record here. The cheapest mechanical version: `/close` already sweeps for todos, so the question is
   whether anything can detect a deferral mid-session. Probably not, so ship it as prose and note the
   limitation honestly rather than claiming enforcement.
4. For (3), do not invent numbers. Measure first: look at recent commits and find the actual
   distribution of changed lines per commit. Set a ratchet at or slightly above current practice so it
   catches outliers rather than blocking normal work, exactly as todo 423 does for the token budget.
   A number pulled from another repo's codebase is meaningless here.
5. For (4), draft the allowlist as an addition to the front-load section, listing categories that
   always require a question (a UX/ARCH/SEC/DATA/TOOLING fork not dictated by an existing pattern is
   already the stated bar, so this may be redundant). **If it turns out to be redundant, say so and
   skip it** rather than restating an existing rule in new words.
6. Respect the file's own weight. CLAUDE.md is already large and todo 424 is actively trying to shrink
   the always-loaded portion. Every addition here should be a sentence, not a section, and (3)'s
   supporting reasoning belongs in a ref if it needs any.

## Acceptance

- (1) is folded into the existing unverified-claim rule, not added as a parallel rule.
- (2) is present, with its enforcement limitation stated honestly.
- (3)'s number is derived from measured recent commits, with the measurement shown.
- (4) is either genuinely additive or explicitly skipped as redundant, with the reasoning recorded.
- Net line count added to CLAUDE.md is reported, and checked against todo 424's shrinking effort.

## Notes

The rule to be most careful with is (4). The broad front-load rule exists because of a real incident,
and narrowing it by accident would undo that. Additive or skipped, nothing in between.

Do not adopt all four in one commit. (1) and (2) are safe; (3) needs a measurement; (4) may not ship at
all.
