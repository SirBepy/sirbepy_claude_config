<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=6, reconfirm-count=1, content-hash=cd7be509 -->
<!-- duplicate-checked -->
# /create-pr scales the body to the diff but has no anti-pattern list

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/create-pr` named body anti-patterns and a manual-only validation rule, so PR descriptions stop
restating what the diff and CI already show.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

`/create-pr` currently scales body length to diff size and runs a comment-noise check on the diff. What
it does not have is guidance on what a PR body should NOT contain.

Reference: `repos/ooloth_dotfiles/tools/agents/config/skills/write-pr-description/SKILL.md`. Two ideas:

1. **Named anti-patterns**, including "listing every file changed" and "escaped inline code". The first
   is the common failure: a body that enumerates the diff adds nothing, since the reviewer can see the
   file list, and it pads a description until the actual reasoning is buried.
2. **A hard rule that the validation checklist is manual end-to-end only, never referencing automated
   tests, because CI already shows those.** This is the sharper of the two. A checklist item saying
   "tests pass" is noise; one saying "logged in as a new user and confirmed the redirect" is the only
   thing a human reviewer cannot get from the pipeline.

Both fit existing practice here rather than fighting it. CLAUDE.md already routes design rationale out
of code comments and into "the PR body, a PATTERNS/CLAUDE doc, or the commit message", so the PR body
is explicitly the place reasoning belongs. That makes it worth protecting from padding. The comment
budget's own logic applies directly: a comment earns its place by naming something the code cannot
show, and a PR body line earns its place by naming something the diff and CI cannot show.

The manual-only validation rule also connects to the testing floor. CLAUDE.md keeps slow e2e suites out
of the fast floor and says to mention in one line when e2e looks worth running, never to run it
unprompted. A manual validation checklist in the PR body is where that judgment gets recorded for the
reviewer, which is a use `/create-pr` does not currently serve.

One thing to verify rather than assume: `/create-pr` already has a comment-noise check (per the
delegation doctrine, which names `/create-pr`'s comment-noise check as a real step). So part of the
anti-pattern enforcement may already exist for comments and simply not extend to the body text itself.
Read the skill before adding anything.

## Approach

1. Read `skills/create-pr/SKILL.md` in full and inventory what body guidance already exists. The
   diff-scaled length rule and the comment-noise check are known; there may be more.
2. Read `write-pr-description/SKILL.md` for its anti-pattern list and its validation-checklist rule.
3. Add the anti-patterns as an explicit list in `/create-pr`, not as prose advice. At minimum: do not
   enumerate changed files, do not restate the commit messages, do not include a "tests pass" line. Each
   one needs to be checkable by reading the drafted body, since that is what makes it enforceable at
   draft time.
4. Add the manual-only validation rule. The checklist section of a generated PR body should contain
   only steps a human performs in the running app, and should be empty rather than padded when the
   change is not user-observable (a refactor, a config change). **An empty checklist with a one-line
   reason is better than a fabricated one**, and this matters here because CLAUDE.md's testing floor
   already requires saying so explicitly when a change is genuinely untestable by Claude.
5. Check the interaction with the existing diff-scaled length rule. If length scales with diff size and
   the anti-patterns remove the easiest padding, a large diff may now produce a short body. That is the
   desired outcome, but the length rule should not then demand filler to hit a size. Reconcile the two
   explicitly.
6. Validate on a real PR body. Draft one for an actual recent change under the new rules and compare it
   against what the current skill would have produced. Report both.

## Acceptance

- The anti-pattern list is explicit and each entry is checkable by reading a drafted body.
- The validation checklist rule is manual-only, and an un-observable change produces an empty checklist
  with a stated reason rather than invented steps.
- The diff-scaled length rule is reconciled with the anti-patterns, with the resolution written down.
- A before-and-after comparison on one real change is included in the report.
- No existing `/create-pr` behavior regresses, in particular the comment-noise check.

## Notes

The "no tests pass line" rule is the one most likely to feel wrong and be quietly dropped. It is
correct: CI reports that already, and a human-facing checklist that includes it trains reviewers to
skim the whole section.

Do not turn this into a PR template. The value is in what gets left out, and a template invites
filling every heading.
