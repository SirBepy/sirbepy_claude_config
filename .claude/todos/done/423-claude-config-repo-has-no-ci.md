<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The ~/.claude repo has 13 hook self-tests and nothing that runs them

**Type:** task
**Origin:** ai

## Goal

CI on this repo, so hook tests actually run, skill frontmatter is validated mechanically, and the
always-loaded instruction weight has a hard ceiling.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current state: 83 skills, 41 hooks (13 of which are `test_*.py` self-test files), 10 refs, 6
snippets, 1070 tracked files. **Zero automation.** The hook tests only run when someone remembers to
run them, which in practice means when a todo tells a session to.

Three things the corpus proves are worth having, in value order:

**1. A hard token budget on always-loaded instructions** (`poshan0126/dotclaude/.github/workflows/ci.yml`).
Estimates tokens as chars/4 over `CLAUDE.md` plus rules and **fails the build over 1200 tokens.**
This one is pointed. Global `CLAUDE.md` here is far past that, and an unverified community report in
the harvest describes a CLAUDE.md that grew 45 to 190 lines and saw compliance *drop* because
mechanical rules were mixed into behavioral guidance. A budget gate makes bloat visible at the moment
it is added instead of a year later. It also gives todo 424 (path-scoped rules) a number to aim at.

**2. Skill frontmatter validation** (`citypaul/.dotfiles/test/skills-frontmatter.sh`). Guards a
**real, already-observed bug**: an unquoted `": "` or `" #"` inside a `name:` or `description:` value
silently drops the skill from installation. It cost them their `double-check` skill once, and they
only found out later. With 83 skills here, hand-editing frontmatter, and a live todo (400) about
description budgets, this is a cheap guard against a silent failure. `alirezarezvani`'s
`CONVENTIONS.md` goes further and rejects PRs carrying any frontmatter field beyond `name` and
`description`, which matches what Anthropic's own examples actually use.

**3. Hook fixture tests on a matrix** (`poshan0126/dotclaude/hooks/tests/run-all.sh`). JSON fixtures
per hook specifying stdin, expected exit code, and stdout/stderr substring checks **including
negative checks**, run on ubuntu plus macos. The 13 self-tests here are ad-hoc scripts rather than a
uniform fixture format, so a new hook has no obvious test shape to copy.

Also seen, and worth a decision rather than automatic adoption: `alirezarezvani` runs PR-triggered
security scanning of only *changed* skill directories, plus VirusTotal. The changed-dirs-only scoping
is the smart part. Whether Claude itself should run in CI is answered in the harvest report: narrow
yes for teammate PRs on client repos, not for solo repos, so probably not here.

Constraint worth checking early: this repo's `origin` remote and the `gh` account mapping is handled
by `hooks/gh-account-switch.sh`, and the repo is `SirBepy`-owned. Confirm GitHub Actions is even
enabled and that running CI here does not cost anything unexpected.

## Approach

1. Confirm the repo has a remote and that Actions can run. If it does not, the whole todo becomes a
   local pre-commit hook instead, which is a smaller but still real win. Establish this first rather
   than building a workflow that never fires.
2. Start with the frontmatter validator, because it is the cheapest and guards a known silent
   failure. Read `citypaul`'s `test/skills-frontmatter.sh` for the exact quoting cases it catches.
   Run it against all 83 skills immediately: it may already find live breakage, which would be the
   finding rather than the tooling.
3. Add the token budget gate. Pick the number deliberately: 1200 is `poshan0126`'s figure for a much
   smaller instruction set, and this CLAUDE.md is far bigger, so a gate at 1200 would fail on day
   one. Measure the current weight first, then set the ceiling at current-or-slightly-below so it
   ratchets down rather than blocking all work. State the measured baseline in the workflow file.
4. Unify the hook tests into a fixture format and wire them to run. Convert the existing 13 rather
   than writing new ones. Windows is the primary platform here, so a ubuntu-only matrix would test a
   path the dev never uses; check whether the hooks are actually portable before choosing runners.
5. Consider the changed-dirs-only scoping for anything expensive.

## Acceptance

- The frontmatter validator runs against all 83 skills and its real output is pasted, including any
  live breakage found.
- The token budget gate has a measured baseline written into it, and fails on a deliberate test
  addition that exceeds the ceiling.
- All 13 existing hook tests run from one command and their real output is pasted.
- CI is proven to fire (a real run link or local pre-commit trigger), not just committed.
- No workflow runs Claude itself without a separate explicit decision.

## Notes

Set the token ceiling to the current measured weight, not to an aspirational number. A gate that
fails on the first commit gets deleted; a ratchet that only blocks growth survives.

Do not convert hook tests to a new format and rewrite their assertions in the same pass. Convert
first, verify they still pass, then improve. Otherwise a broken assertion looks like a broken hook.
- Shipped 2026-08-20. ci/run_all.py composes three stdlib-only checkers: run_hook_tests.py (13/13 suites pass; zero-discovery and failing-suite paths both exit 1), check_skill_frontmatter.py (83 skills, 5 hard checks; found 4 files whose unquoted description colon-space is invalid YAML and quote-wrapped them with no wording change), check_instruction_budget.py (CLAUDE.md gated at CEILING_TOKENS=6732, the measured 2026-08-20 baseline; the wider 10981 five-file figure is printed but never gated). Wired two ways: .github/workflows/ci.yml (windows-latest blocking, ubuntu-latest continue-on-error as a portability probe) and /commit step 6a. The ceiling has HEADROOM 0 by construction, so the next addition to CLAUDE.md fails the gate on purpose: phase 4 (todos 429 and 442) adds CLAUDE.md rules and must either cut elsewhere or raise the constant deliberately. Claude Code own skill loader tolerated the 4 invalid-YAML descriptions (android-drive and brainstorm both appeared in this session skill listing with full descriptions before the fix), so that check removes a latent hazard rather than an observed outage; PyYAML rejects the originals and accepts the fixes.
