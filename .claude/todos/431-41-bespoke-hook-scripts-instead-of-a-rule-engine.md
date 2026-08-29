<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=3, reconfirm-count=2, content-hash=a0db9ccc -->
<!-- duplicate-checked -->
# 41 bespoke hook scripts where a declarative rule engine would do

**Type:** task
**Origin:** ai

## Goal

Evaluate replacing the one-Python-file-per-guard pattern with a config-driven rule engine, so a new
simple guard is a config entry rather than a new script plus a new test file.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). This is the largest
structural change in the harvest set and the riskiest, which is why it is an evaluation todo rather
than an implementation todo.

Current state: 41 hook files, 27 of them `.py` guards, each a standalone script with its own argument
parsing, stdin JSON handling, exit-code convention and test file. Adding a guard means writing all of
that again. Several are near-identical in shape and differ only in which field they match and what
pattern they look for.

Reference: `repos/zircote_.claude/patches/hookify-0.1.0/core/rule_engine.py`. A declarative engine
where a rule is `{tool_matcher, conditions: [{field, operator, pattern}], action: block|warn}`,
evaluated generically across PreToolUse, PostToolUse and Stop, with per-tool-type field extraction
and cached regex compilation. New guards are config edits.

Why this is genuinely uncertain rather than an obvious win:

- **Many of the 27 guards are not simple pattern matches.** `dispatch-preamble-guard.py` checks for
  three literal substrings with documented reasoning about why it is a string check and not a semantic
  one. `todo-duplicate-guard.py` greps a destination backlog and scores token overlap.
  `shell-content-write-guard.py` reasons about BOM risk. A rule engine expresses none of those, so the
  realistic outcome is a hybrid: engine for the simple ones, scripts for the rest. A hybrid means two
  mechanisms to understand instead of one, which may be worse than 41 scripts.
- **The existing scripts carry their reasoning in docstrings.** That history is load-bearing here:
  several encode a specific past incident. A config row cannot hold "this exists because X happened
  three times". Losing that is a real cost, and this repo has already been bitten by a docstring that
  drifted from reality (todo 414).
- Todo 423 proposes CI and a uniform fixture format for hook tests. If that lands first, the marginal
  cost of a new bespoke script drops, which weakens the case for an engine. **Sequencing matters:
  do 423 first.**

## Approach

1. Read `hookify-0.1.0/core/rule_engine.py` for the field-extraction and condition model.
2. Classify all 27 guards: expressible as a declarative rule, versus genuinely procedural. Produce
   the classification as the deliverable of this step and count both buckets. **If fewer than roughly
   half are declarative, recommend not doing this and close the todo with that finding.** A negative
   result here is a real result.
3. If the count justifies it, prototype the engine against the three simplest declarative guards
   only. Keep their existing tests passing unchanged, which is the proof that behavior is preserved.
4. Decide the hybrid question explicitly and write the decision down: does the engine live alongside
   scripts permanently, or is it only worth it if nearly everything migrates?
5. Preserve the incident reasoning. If a guard migrates, its docstring rationale moves to a comment
   on the rule or into the rules file's header. Do not let it evaporate.

## Acceptance

- A written classification of all 27 guards into declarative versus procedural, with counts.
- An explicit recommendation, including "do not do this" if that is what the classification supports.
- If prototyped: three guards migrated, their original tests passing unmodified, real output pasted.
- No guard loses its recorded reasoning.
- Runs after todo 423, or states why not.

## Notes

The honest default here is probably "no". 41 scripts is untidy but each one is independently readable
and independently testable, and this repo's guards encode more incident history than pattern matching.
Do the classification before falling in love with the architecture.
