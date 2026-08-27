<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=5, reconfirm-count=1, content-hash=ec31f602 -->
<!-- duplicate-checked -->
# The config repo documents every project except itself

**Type:** task
**Origin:** ai

## Goal

A README describing this repo's own layout, a documented convention for authoring skills and hooks,
and a generated skills index that cannot drift from reality.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

This repo has 83 skills, 41 hooks, 10 refs, 6 snippets, 2 code-style files, 1 agent, 1070 tracked
files, and **no document explaining any of it.** There is a `README.md` at the root, but the baseline
inventory pass had to derive the structure by walking the tree, and building that inventory
(`BASELINE.md`, 367 lines) took a full subagent's context. Any future session or agent that needs to
know what exists pays that cost again.

Concretely, three things are missing:

**1. A README for the config tree.** `zircote/.claude` has one describing its whole layout.
Non-obvious things a new session cannot infer and currently has to be told: that `refs/` holds
procedures read on demand while `snippets/` holds `@import`-ed rule fragments; that
`.claude-personal` and `.claude-fibo` are junctions into `skills/`; that `.claude/todos/` is
repo-relative even for this repo; that every hook in `hooks/` is live, because unadopted spikes are
deleted rather than parked there (settled by todo 416, which deleted the three `EXPERIMENTAL-*.py`
files); that `hooks/.commit-marker-*` and `.session-markers/` are live runtime state no cleanup may
touch.

**2. A CONTRIBUTING-equivalent for authoring.** `zircote/.claude/skills/CONTRIBUTING.md` documents a
skill-authoring template and process. `alirezarezvani/claude-skills/CONVENTIONS.md` goes further with
hard rules worth stealing: only `name` and `description` allowed in frontmatter (which matches what
Anthropic's own 18 examples actually use), mandatory Anti-Patterns and Cross-References sections, and
a 500-line cap with overflow pushed to `references/`. `bepy-skill-creator` encodes some conventions in
code but there is no document a human or agent can read to learn them.

**3. A skills index, generated rather than hand-written.**
`hesreallyhim/awesome-claude-code` is the working template: **CSV as source of truth**, entries added
via an issue form, CI validating schema and eligibility, and the README **auto-regenerated** from the
CSV (`resources/parse_issue_form.py`, `templates/README.template.md`,
`.github/workflows/validate-new-issue.yml`). The generation direction is the important part. A
hand-maintained index of 83 skills is guaranteed to drift; one generated from the skills' own
frontmatter cannot.

Related, and the reason a generated index earns its keep beyond documentation: there is no
cross-reference graph across the 83 skills. `citypaul`'s skills reference each other in prose ("for X
see skill Y") with nothing enforcing the links, and this repo does the same informally. A generated
index could surface dangling references. Prior art on skill inventory: the 2026-08-01 audit
(`skills/AUDIT-2026-08-18.md` exists, and a memory entry covers that audit) plus live todo 400 on
description budgets.

## Approach

1. Write the README first, and write it from the baseline inventory that already exists
   (`C:\tmp\claude-harvest\BASELINE.md`) rather than re-deriving the tree. Copy that file somewhere
   durable before `/tmp` is cleaned, or regenerate it. Keep the README a map, not a manual: what each
   directory is for, and the non-obvious invariants listed above.
2. Generate the skills index from frontmatter, not by hand. A script that walks `skills/*/SKILL.md`,
   reads only the frontmatter, and emits a table of name, description, and whether it is
   model-invocable. That is exactly what the baseline pass did manually, so the logic is known to
   work. Wire it so the index is regenerated rather than edited, and say so at the top of the
   generated file.
3. Write the authoring conventions doc. Take `alirezarezvani`'s hard rules as a starting point but
   reconcile with what is actually true here: this repo DOES use `disable-model-invocation`, so a
   two-fields-only rule would be wrong. Document the fields actually in use and why.
4. Have the index generator flag problems, since a generator that only formats is a missed
   opportunity: skills whose description exceeds the budget (feeding todo 400), frontmatter that fails
   the quoting cases from todo 423, and `[[wiki-style]]` or prose cross-references pointing at skills
   that do not exist.
5. Decide whether the index generation runs in CI. That is todo 423's mechanism, so coordinate rather
   than building a second automation path.

## Acceptance

- A README exists describing every top-level directory and the non-obvious invariants named above.
- The skills index is produced by a script from frontmatter, and re-running it on an unchanged tree
  produces an identical file (proving it is deterministic and safe to regenerate).
- The generator's report on over-budget descriptions and dangling cross-references is pasted as real
  output, whatever it finds.
- The authoring conventions doc reflects fields actually in use here, not copied rules that contradict
  this repo's own practice.
- All new files land inside the `.gitignore` allowlist and show up in `git status` as tracked.

## Notes

The allowlist gitignore means a new top-level file is invisible unless explicitly excepted. Check
that before assuming a committed README is tracked.

Do not hand-write the skills index. A stale index is worse than none: it gets trusted.
