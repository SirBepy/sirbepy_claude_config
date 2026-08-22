<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# One CLAUDE.md bullet states a preference and a requirement in the same sentence

**Type:** task
**Origin:** ai

## Goal

Split the Packages research bullet so its soft half and its absolute half stop sharing a sentence.

## Context

Filed out of todo 429's rule-force audit (2026-08-22). The full audit is in
`refs/claude-md-rule-force-audit.md`; this is its single actionable finding.

The audit classified all 81 `CLAUDE.md` bullets by intended force and found the prose already
carries the distinction in 76 of them. Four entries turned out not to be rules at all (scope
definitions), exactly one genuine AVOID exists in the whole file, and **exactly one bullet mixes
two forces in a single sentence:**

> Prefer a subagent for the research; required for anything load-bearing or crypto/network. A quick
> inline web search is acceptable for a single obvious package.

`Prefer` is a default a session may reasonably decline. `required` is absolute. They are joined by a
semicolon, so a reader skimming for the rule's force gets whichever half they landed on. This is
also why the audit recommended against tagging: a single ALWAYS/PREFER tag on this bullet would have
to pick one half and would silently demote or promote the other.

The risk is not hypothetical in shape - the harvest's whole premise is that a rule set loses
compliance as it grows - but no incident is on record for THIS bullet specifically. It is a
correctness fix to the file, not a response to harm.

## Approach

1. Split into two bullets: one PREFER-shaped (use a subagent for package research; a single obvious
   package can be an inline web search) and one absolute (a subagent is REQUIRED for anything
   load-bearing or crypto/network).
2. Keep the token cost at or near zero. `CLAUDE.md` sits at 6558 tokens against a
   `CEILING_TOKENS` of 6558 with **zero headroom**, so `python ci/run_all.py` fails on any net
   addition. A split that reuses the existing words should come out flat or slightly under; if it
   comes out over, cut words rather than raising the ceiling.
3. Do not tag either half with ALWAYS/PREFER/NEVER/AVOID. That was decided against in 429 with the
   reasoning recorded; splitting the sentence is the alternative the audit recommends.

## Acceptance

- The two forces live in separate bullets and neither one's meaning changed.
- `python ci/run_all.py` exits 0, meaning the split did not push `CLAUDE.md` over its ceiling.
- `refs/claude-md-rule-force-audit.md`'s finding 2 is updated to say it was fixed, so the audit does
  not keep reporting a resolved problem.

## Notes

Small and safe, but it edits the most load-bearing file in the repo, so it gets its own commit with
nothing else in it.

Do not use this as an opening to re-litigate the tagging half of 429. That closed on evidence and
carries its own re-open trigger, which this is not.
