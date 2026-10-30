---
name: global-claude-folder-audit
description: Triggers on /global-claude-folder-audit only. Deep audit of the whole ~/.claude setup - skills, CLAUDE.md, rules, hooks - plus fresh AI-practice research.
disable-model-invocation: true
argument-hint: "[optional focus note, e.g. `skills only` or `skip research`]"
---

# /global-claude-folder-audit

> Every few months: is this setup still right for how AI agents work today?

The setup-level sibling of `/audit`. `/audit` judges one app's code; this judges the `~/.claude`
tree itself: which skills earn their place, which should merge or go, whether `CLAUDE.md` and the
rule files still say the right things, whether the hooks enforce what the rules claim, and what the
outside world has learned about agent setups since the last run. It reuses `/audit`'s machinery
(read `skills/audit/SKILL.md` once before starting) and adds three things it lacks: a lens for
agent-config files (`lens.md`), real usage numbers (`count_invocations.py`), and a committed
`ledger.md` so each run builds on the last one instead of re-suggesting what the dev already declined.

Run it from a session whose cwd is `C:\Users\tecno\.claude`. It edits nothing outside this
skill's ledger; fixes are separate, later work through the backlog.

## Phase 0 - Read the ledger

Read `ledger.md` in this skill's directory. Note the last run date (research covers only what
changed since; first run covers the last ~6 months) and every Declined entry (passed to every
auditor as "do NOT re-report").

## Phase 1 - Inventory and usage (inline)

1. Start `python skills/global-claude-folder-audit/count_invocations.py --json` with
   `run_in_background: true` (it reads every raw transcript, a few minutes). Persist its output to
   the run folder the moment its notification lands: the task output file is cleared on completion.
2. Meanwhile map the tree: every `skills/*/SKILL.md` with line count, aux-file count and its
   `disable-model-invocation` flag; `CLAUDE.md`, `refs/`, `snippets/`, `code-style/`, `context/`
   with sizes; `hooks/*.py` and which `settings.json` matcher wires each; `agents/`. Mark vendored
   skills (a third-party source, a `VERSION` file, an upstream URL) so auditors judge them on
   "keep installed or not", not on prose they would never edit.
3. Partition into slices of 10-25 files with concrete file lists, never a glob. Group skills by
   family (todo pipeline, commit/push/release, testing/e2e, design/UI, Figma, vendored packs,
   game/Roblox, project setup, communication/tickets, meta/session tooling) so overlap inside a
   family is visible to one reader.

Run folder: `.for_bepy/global-audit/<YYYY-MM-DD>/` (gitignored).

## Phase 2 - Rubric

Write `<run folder>/RUBRIC.md`: the Hard constraints, Prior-decision check, Severity and Report
format sections of `skills/audit/rubric-template.md`, then this skill's `lens.md` in place of the
template's four app lenses, then the context: the usage table, the vendored list, the ledger's
Declined entries, and the fact that this is a single-developer setup shared by many concurrent
sessions (so token cost per session and hook latency per tool call are real costs).

## Phase 3 - Fan out

Every dispatch: `model: 'sonnet'`, the canonical preamble from `refs/builder-preamble.md` with the
literal `READ-ONLY DISPATCH` line and its "Leave all changes unstaged" staging variant, and an
instruction to read `<run folder>/RUBRIC.md` first. Launch in the foreground, in parallel batches:
background dispatches have been lost across turns in Conductor chats.

| Slice | Owns |
| --- | --- |
| Research (1-2 agents, web) | What changed since the last run: Claude Code changelog and docs (skills, hooks, subagents, memory, output styles, settings), Anthropic engineering posts, well-sourced community practice. Return each item with its URL and a "so for this setup:" line. Most important question: which custom skills or hooks now duplicate a native feature |
| Skill families (one per family) | All of `lens.md` applied to that family's SKILL.md files and their aux files |
| Trigger map | Every skill's frontmatter description at once: overlap, misfires, listing budget, slash-only skills missing `disable-model-invocation` |
| Rules | `CLAUDE.md`, `refs/`, `snippets/`, `code-style/`, `context/`: contradictions, staleness, rules no longer needed, always-loaded token cost |
| Hooks vs rules | Each hook against the rule text it enforces, both directions; fail-closed risk; per-call latency from `settings.json` matchers |
| Dead references | Every path, script, skill name, flag and tool mentioned anywhere in the tree, checked for existence |
| Settings and agents | `settings.json`, `agents/*.md`, MCP config: unused, risky or contradictory entries |

Hand the research report to the slices still being launched, and keep a growing
"already reported, do NOT re-report" list, per `/audit` Phase 3.

## Phase 4 - Verify

`/audit` Phase 4 applies unchanged, using `skills/audit/verify-template.md`, plus one rule of its
own: **every DELETE and MERGE recommendation goes to a refuter regardless of severity.** A refuter
gets the usage numbers and must argue for keeping it. Retiring a skill is the call most often made
too quickly, and the dev sometimes wants separate skills for autocomplete even when they overlap.

## Phase 5 - Report

Written by this session itself to `<run folder>/REPORT.md`, shaped like `/audit` Phase 5
(themes, looks-bad-but-fine, what is genuinely good), plus:

1. **What changed out there** - the research items that change something here, each with its URL.
2. **Skill verdicts table** - every skill: keep / merge into X / delete / rewrite, with its usage.
3. **Rules verdicts** - per `CLAUDE.md` section: keep / cut / move to a ref / now hook-enforced.

## Phase 6 - Accept, file, record

1. Split findings into **safe to auto-apply** (mechanical, verifiable: a dead path, a missing
   flag) and **judgment calls** (delete, merge, rule changes). The dev does not read code: a finding
   that needs reading code to judge is either rephrased so it does not, or dropped.
2. Question cards: lead with the coarse option ("file every safe one", "accept all deletes"), then
   per-item cards only for the judgment calls the dev wants to go through one by one.
3. Accepted findings become todos in `C:\Users\tecno\.claude\.claude\todos\` per
   `skills/close/ai-todos-format.md`, `Origin: dev` (the dev accepted them in these words).
4. Append to `ledger.md`: one `## Runs` line (`- <date> <N findings, N accepted, N declined>`) and one
   `## Declined` line per rejected finding with the dev's reason. Then `/commit` the ledger.

Fixes are separate, later work through the backlog. This skill reads; the ledger is its only write.

## Cost

Roughly 15-25 sonnet agents at 150k-250k tokens each, plus refuters. The dev triggers it by name,
so no extra cost confirmation is needed; say the expected agent count in the first message.
