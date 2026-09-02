<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=2, content-hash=70ffd043 -->
<!-- duplicate-checked -->
# `/commit`'s unpushed-overlap check has no branch for a non-HEAD overlap

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/commit` step 8's unpushed-overlap check a defined outcome for the case it currently cannot
express, so a session doesn't have to improvise past its own gate.

## Context

Surfaced 2026-08-22 in `zng-app`, across a session that made 13 commits on a branch carrying 45
unpushed ones.

`skills/commit/SKILL.md` step 8's **unpushed-overlap check** ends with:

> On a real hunk-level hit: **interactive session** - STOP, name the overlapping commit and the
> blamed lines, ask via `AskUserQuestion` whether this is follow-up on the same unit of work
> (-> `git reset --soft HEAD~1`, restage everything together, one fresh commit) or genuinely
> separate (-> proceed).

Both offered remedies assume the overlap is with **HEAD**. `git reset --soft HEAD~1` can only fold
into the immediately preceding commit.

What actually happened: the hunk-level blame on `v2_share_screen.dart` returned **five** unpushed
shas (`14062e0`, `b2d3b3e`, `b3d2926`, `b964229`, `ecf4905`), none of them HEAD - HEAD was an
unrelated commit from a different todo. `request_v2_step_scaffold.dart` and `v2_verify_screen.dart`
each returned three or four more. Every one is a genuine hunk-level hit by the skill's own
definition, and **not one of them is foldable**: `reset --soft HEAD~1` would have folded the new work
into the wrong commit entirely.

So the card the skill mandates would have offered one option that is actively destructive and one
("genuinely separate") that is the only possible answer. I proceeded and surfaced it in text instead
of opening a card with a single viable choice. That was the right call for the diff and the wrong
shape against the written rule, which is the gap.

This is expected to be the **common** case on any long-lived unpushed branch - which is exactly the
situation the check was written for.

## Approach

1. Split the hit's outcome on whether the blamed sha **is HEAD**:
   - Overlap includes HEAD -> the existing card, unchanged. Folding is real here.
   - Overlap is entirely non-HEAD -> folding is impossible via `reset --soft HEAD~1`. Either point at
     `/commit fold <sha>` (which already exists, already refuses on pushed commits, and already
     handles commits with others stacked on top), or define "state it and proceed" as the sanctioned
     outcome. Do not mandate a card whose primary option cannot be executed.
2. While there: `commit-style.md`'s "**Different tickets never share a commit**" has the same shape
   of gap. Two todos whose changes land in one file cannot be split by pathspec, and the rule gives
   no pointer at the point of use. `skills/commit/edge-cases.md` does cover partial staging - the
   rule should name it, or say explicitly that one commit covering both is acceptable when the file
   overlaps. Same session hit this with todos 166 and 167.

## Acceptance

- Step 8's hit-handling text distinguishes HEAD from non-HEAD overlap and names an executable
  remedy for each.
- ~~`commit-style.md`'s never-share-a-commit rule links to the partial-staging section or states the
  overlapping-file exception.~~ **DROPPED 2026-09-02, premise false: no such rule exists in this
  repo. See Notes.**
- Re-read the two files end to end afterwards: both rules are load-bearing on every commit, so an
  edit that contradicts a neighbouring clause is worse than the gap.

## Notes

- **Advanced but NOT finished, 2026-08-31, `/mega-todos` batch 1, commit `8658bd1`.** The primary fix
  landed: `skills/commit/SKILL.md` step 8's unpushed-overlap hit handling now splits on whether the
  blamed sha IS HEAD. Overlap including HEAD keeps the existing question card; overlap that is
  entirely non-HEAD no longer offers `git reset --soft HEAD~1`, which was actively wrong there, and
  points at `/commit fold <sha>` instead.
- **The second acceptance item is undispatchable as written, and that is a defect in this todo, not
  in the work.** It names a rule in `skills/commit/commit-style.md`. That file does not exist anywhere
  in this repo: `find skills/commit -type f` lists no such file, and the quoted rule "Different
  tickets never share a commit" appears verbatim nowhere repo-wide. Verified independently by the
  Step C scout and by the orchestrator on 2026-08-31. The only `commit-style.md` `SKILL.md` references
  is a PROJECT-level override at `.claude/commit-style.md` in OTHER repos, read at step 1.
- Next run: either point that item at wherever the never-share-a-commit rule actually lives (if it
  exists under another name), or drop the item and archive this todo on the primary fix alone. Do NOT
  invent a file to satisfy it.
- **Resolved 2026-09-02, `/mega-todos` batch 3: item dropped, todo archived on the primary fix.**
  A repo-wide grep for `never share a commit`, `Different tickets`, `One purpose per commit` and
  `share one commit` over every `.md`/`.sh`/`.ps1` returns exactly two hits, neither of which is the
  rule this item describes: `skills/commit/SKILL.md:174` and `skills/mega-todos/SKILL.md:356`, both
  reading "One purpose per commit" - and SKILL.md:174 continues "Many files is fine if it's one
  logical change", which explicitly PERMITS the case the item wanted an exception carved out for.
  So there is nothing to link and no gap to close. The project-level `.claude/commit-style.md`
  variant of this concern is tracked separately in todo 849.
- Archived on the primary fix alone; the second acceptance item was DROPPED, not satisfied. A repo-wide grep for the never-share-a-commit rule it named returns only One purpose per commit in skills/commit/SKILL.md:174 and skills/mega-todos/SKILL.md:356, and SKILL.md:174 continues Many files is fine if it is one logical change, which explicitly permits the case the item wanted an exception carved out for. There was nothing to link and no gap to close. Evidence written into the todo body before archiving. The project-level .claude/commit-style.md variant of this concern stays tracked in 849.
