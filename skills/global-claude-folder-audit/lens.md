# Lens: agent-config files (skills, rules, hooks)

Replaces `/audit`'s four app lenses for this audit. The reader of every file here is a model, not
a human: a skill is good when an agent following it literally does the right thing, and bad when it
can be misread, contradicts another instruction, or costs context without paying for it.

## 1. Trigger and necessity (skills)

- **Trigger quality:** does the description make the skill fire on the asks it serves, and not on
  others? Quote the description and name a concrete ask that misfires or is missed.
- **Overlap:** two skills whose descriptions both claim the same ask. Cite both descriptions.
- **Earns its place:** use the usage table. Low use is evidence, not a verdict: check `created`
  (new skills have short exposure), whether another skill calls it via the Skill tool (internal
  callers count), and whether it guards a rare but costly moment (a release, a migration).
- **Native replacement:** the harness now does this natively (cite the research report's URL).
- **Vendored packs:** judge only keep-installed vs remove, plus overlap with the dev's own skills.

## 2. Merge and split

- Two skills always run together, or share most of their steps: merge candidate, name which absorbs which.
- One skill doing several unrelated jobs behind flags: split candidate, name the seam.
- The dev keeps some overlapping skills separate on purpose for autocomplete. A merge finding must
  say what is lost beyond one autocomplete entry, or it is not a finding.

## 3. Drift and dead references

- A path, script, skill name, flag, tool or env var the text names that does not exist. Prove it
  (`ls`, `grep -rn` scoped to the tree). This is the most common real defect in config trees.
- A step that contradicts `CLAUDE.md`, a ref, or another skill: quote both sides.
- A step a hook will block (the text says run X, `hooks/` denies X).
- A rule claiming hook enforcement that the hook does not do, or a hook enforcing a rule no text states.

## 4. Clarity for an agent

- Ambiguous steps a literal reader could take two ways; missing stop conditions; loops with no exit.
- Instructions that make the agent ask mid-task, against the front-load rule.
- Incident accretion: rules bolted on one incident at a time ("todo NNN", "2026-09-xx incident")
  until the instruction is buried. Name the consolidated version in a sentence.
- Rationale that belongs in a commit or `refs/incidents.md`, sitting in an always-loaded file.

## 5. Weight

- Always-loaded cost: `CLAUDE.md`, its imports, every skill description in the listing. Estimate
  the words a cut saves.
- SKILL.md bulk serving a rare path that should move to an aux file read on demand.
- Aux files nothing references (prove with grep).

## Severity for this domain

- `CRITICAL` - a rule or hook combination that can lose work, leak a secret, or take shell access
  from every live session.
- `HIGH` - an instruction agents follow that produces wrong behavior today, or a contradiction
  agents resolve the wrong way, or large always-loaded waste.
- `MEDIUM` - a delete/merge candidate, a dead reference in a live path, a rule no longer needed.
- `LOW` - a dead reference in a rare path, a wording fix.

Report with the rubric's format; `Lens:` is one of `trigger | merge | drift | clarity | weight |
research`.
