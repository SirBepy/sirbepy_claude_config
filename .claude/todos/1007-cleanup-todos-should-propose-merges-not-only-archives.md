<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: searched the live backlog and done/ for merge/consolidate/fold proposals against /cleanup-todos. The skill has a Step 2 DEDUPE (two todos describing the SAME task, one is archived as a loser) and a Step 6.4a low-worth roundup. Neither is this: this is about todos describing DIFFERENT tasks that share a target file. No existing item covers it. -->
# 1007 - /cleanup-todos should propose MERGES, not just dedupes and archives

**Type:** skill-improvement
**Origin:** dev
**Created:** 2026-09-24

## Goal

Give `/cleanup-todos` a step that groups the surviving backlog by the files each todo actually
touches, and proposes merging each group into one todo, with every original's context preserved
rather than summarised away.

## Context

Joe, 2026-09-24, during a `/cleanup-todos` run on zng-app:

> "the idea of merging todos (WITHOUT LOSING ANY CONTEXT OF EACH ORIGINAL TODO) cuz sometimes myb
> we will want to archive smth, but we might aswell do it if we are already working on that file
> on some other cleanup stuff"

That is the load-bearing insight and the skill currently has no step for it. What exists today:

- **Step 2, dedupe.** Only fires when two todos describe the *same underlying task*. One is kept,
  the loser is archived.
- **Step 6.4a, low-worth roundup.** Lists every deep-tier todo scoring `worth <= 4` for the dev to
  scan. Explicitly "not drop suggestions".

Neither handles the common case: N todos describing *different* tasks that happen to land in the
same file or the same tight cluster of files. Individually each scores 3 or 4 and looks like churn.
Together they are one editing pass and one commit, which is a completely different proposition in a
repo where review time is a real cost.

### The measured case that produced this

That run's own numbers, zng-app backlog on 2026-09-24. 30 `ai`-origin todos scored `worth <= 4`.
Grouped by the files they actually touch, they collapsed to **10 todos, 1 fold-into-an-existing-one,
and 5 genuine drops**. Examples:

- `70, 71, 137, 178` all edit `request_v2_contact_fields.dart` and/or `request_v2_identity_fields.dart`.
  Todo 70's own text already said "do this before or together with todo 71" - the coupling was
  recorded in prose where nothing could act on it.
- `175, 176` are both `lib/api/session.dart`, and so is `177`, which scored **8**. The two cheap
  ones are nearly free if done in the same pass as the expensive one. Nothing in the skill surfaces
  that adjacency.
- `74, 124, 150` are three separate duplicated helpers, all landing in `e2e/lib/`. One commit.

The `175/176/177` case is the sharpest argument: the merge step is not only a way to shrink a
backlog, it is a way to find cheap work riding along with work that is already justified.

## Approach

A new read-only step after Step 4's triage and before Step 6's report, so its output feeds the
report as a proposal rather than an action.

1. **Extract each todo's target files.** Grep each surviving todo for path-shaped tokens
   (`lib/...dart`, `test/...dart`, `e2e/...js`, `web/index.html`, and so on). This is mechanical
   and needs no subagent; the triage chunks have already read every file by this point, so the
   information can also come back as a fifth CSV column rather than a second pass.
2. **Group by file overlap**, not by topic similarity. Two todos merge when they name at least one
   file in common. Transitive closure, so a chain A-B, B-C merges all three.
3. **Report each group** as `<ids> -> one todo, shared files: <paths>`, with the sum of their
   worth scores alongside the max, since a group of five 3s is not a 3.
4. **On confirm, write the merged todo** under a fresh reserved id, then archive each source via
   `complete-todo.ps1` with a `folded into <new-id>` note. This is the existing Merge-mode
   machinery `/pickup --merge` already implements in its Steps M3 and M4 - reuse it, do not write a
   second one.

### The context-preservation rule is the hard requirement

Joe's parentheses are the specification, not a caveat. The merged todo must carry each source's
own evidence, its own acceptance criteria and its own `file:line` citations, attributed by source
id, not a paraphrase of all of them. `/pickup --merge`'s Step M3 already states this shape
("what only one knew, kept and attributed to it") and its `## Open questions` convention handles
the case where two sources contradict each other. Inherit both.

Archiving to `done/` already preserves the originals byte-for-byte, so "without losing context" has
two independent guarantees: the merged file quotes what matters, and the originals stay readable.
Say that in the report, because it is what makes a merge safe to accept quickly.

## Acceptance

- A `/cleanup-todos` run on a backlog with a known file-overlap cluster reports that cluster as a
  merge proposal.
- Accepting it produces one todo whose body contains every source's evidence and acceptance
  criteria, attributed per source id, and moves each source to `done/` with a `folded into` note.
- A backlog with no overlapping todos produces no merge proposals and no extra noise in the report.
- The step never merges on its own judgement: `dev`-origin sources go on the Step 6 confirm list
  like every other destructive proposal.

## Notes

- Grouping must be on **file overlap**, not title or topic similarity. Topic similarity is what
  Step 2's dedupe already does and it answers a different question. Two "split this file" todos
  pointing at two different files are not a merge; a "split this file" and a "dedupe this helper"
  pointing at the SAME file are.
- Watch for the false merge: a file that nearly every todo touches (a barrel file, a constants
  file, `app_router.dart`) would drag unrelated todos into one blob. Consider ignoring a file from
  the overlap key once more than N todos name it, and say so in the report rather than silently.
- Related but distinct: `/batch-todos` classifies EASY/HARD for execution. This is about the shape
  of the backlog, not about running it. Do not couple them; the skill's own Non-goals section
  already rules that coupling out for v1.
