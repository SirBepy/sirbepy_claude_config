<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits 0205 (multi-phase plan skill), 0347 (auto-do-todos commit cadence) and 1277 (dashboard cards) only share the words skill/backlog/through/conductor; none is about running a backlog through worktree subchats -->
# A /subchat-todos skill: run the backlog through Conductor worktree subchats

**Type:** skill-improvement
**Origin:** ai
**Summary:** One skill does the preflight, lane split, follower queue and final review that the 2026-11-07 subchat run did by hand, so the next backlog run through subchats costs no orchestrator improvisation.

## Why

On 2026-11-07/08 Joe had Claude replace `/loop-todos` cycles with Conductor subchats (worktree=true, report_back=true). It closed 57 of 69 todos in 19 subs with zero merge conflicts, but the orchestrator rebuilt the whole procedure by hand. Every step below was a manual repeat or a recovery from a surprise:

- 27 orphaned tracked edits and 38 untracked todo files had to be committed first, because a worktree sub branches from HEAD and cannot merge back over a dirty file or see an untracked todo.
- Conductor caps a chat at 5 subs (queued ones count too), and `spawn_chat`'s `after=` refuses a sub that is not registered yet, so 14 followers were spawned by hand, one per report_back wake-up, from a hand-kept `.for_bepy/loop-2026-11-07/queue.md`.
- After each merge, the orchestrator ran the merged lane's own tests on master by hand.
- 20 merged `sub-*` worktrees were left on disk and removed by hand with `safe-remove-worktree.ps1`.
- Every sub reported "reviewer: ran", yet a separate review-unpushed pass over the 145-commit range found 26 real issues (2 were false auto-approves in live guards), which took 5 more fix lanes.

Memory: `reference_conductor_subchats_orchestration_mechanics`.

## Goal

`/subchat-todos` (or a `--subchats` mode of `/loop-todos`; pick whichever keeps the Phase 0 question round in one place) runs a backlog through worktree subchats with these steps built in: a clean-tree and tracked-todo preflight; a read-only scout that maps each todo's files into lanes; a queue file the orchestrator follows to spawn each follower when its predecessor reports back; per-merge tests on master; merged-worktree cleanup; and a mandatory review-unpushed pass with fix lanes before the push gate.

## Approach

- Reuse `skills/loop-todos/SKILL.md` Phase 0 and 3.5 (question rounds) by reference; do not restate them.
- Reuse the scout prompt shape and the `triage.md` / `queue.md` / `review-findings.md` files from `C:\Users\tecno\.claude\.for_bepy\loop-2026-11-07\` as the templates. That folder is gitignored scratch, so copy what is needed into the skill.
- Lanes are chains of at most 5 concurrent subs. A follower's brief is written to the queue file up front, and spawned verbatim on its predecessor's report_back.
- Every brief points at the triage file and states the never-ask rule when the dev is away.
- End with `skills/review-unpushed/SKILL.md`, then hand the push to `/gate-chat` with `gate: true`.

## Acceptance

- A dry run of the skill on a small backlog (3-5 todos) produces the preflight output, a lane plan and a queue file without spawning anything (a `--plan-only` flag).
- `python ci/check_skill_frontmatter.py` passes.

## Notes

- Filed by /close on 2026-11-08 from the subchat run's retrospective.
