<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=ae6edea5 -->
# Stop writing over-cap comments and then trimming them six times

**Type:** skill-improvement

## Goal

Hit the comment cap on the FIRST write, so `/commit`'s step-5a prefilter is a check that passes rather than the start of a multi-round trim loop.

## Context

On 2026-08-06 this happened twice in one session, on two separate commits. Both times the flow was: write the code, run the step-5a prefilter, get flagged, trim, re-run, get flagged again. The second commit took SIX prefilter rounds before it came back clean:

```
FLAG stt.rs 35/76 (46%) longest 6   ->  26/67 (38%) longest 4
    ->  20/61 (32%)  ->  15/56 (26%)  ->  14/55 (25%)  ->  clean
```

Each round cost a full edit-plus-rerun cycle for zero product value. The rules were not unknown - the cap is stated plainly in the global CLAUDE.md Code Style section (2 lines typical, 4 hard per block, under 25% of added lines once a file adds 20+) and `/commit` step 5a restates it. It was simply not applied while writing.

Two mechanical traps that made it worse and are worth encoding:
- In Rust, the prefilter's `#` pattern counts `#[tauri::command]` as a comment line, so a 4-line `///` doc block directly above an attribute already trips `longest >= 5`. Budget 3 doc lines above any attribute.
- Restoring a pre-existing comment VERBATIM removes it from the added-lines count entirely. Rewording an untouched comment is the most expensive way to say the same thing.

## Approach

Amend `~/.claude-personal/skills/commit/comment-noise.md` (the single place the cap is defined; `/commit` step 5a and `/create-pr` step 2b both defer to it) with a short "write within the cap" preamble covering:

1. The cap is a WRITING budget, not just a gate. Before writing a block, decide if it names a constraint, gotcha, or measurement the code cannot show - if not, do not write it.
2. The Rust attribute trap above.
3. "Do not reword an untouched comment" - verbatim-restore keeps it out of the diff.
4. When flagged: CUT, never reword. Rewording is what turned one flag into six rounds.

Rejected: adding a pre-write lint or hook. The failure is judgment at write time, not a missing tool, and a hook would fire after the tokens are already spent.

## Acceptance

- `comment-noise.md` carries the preamble and both mechanical traps.
- Next session touching Rust: step 5a comes back clean on the first or second run, not the sixth.
- Must NOT regress: the cap numbers themselves stay defined in exactly one place - do not duplicate them into the `/commit` SKILL.md body.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #523) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Joe's original incident behind this cap (2026-07-29) was a sidebar PR shipping six-to-nine-line comment blocks, reaction: "STOP WRITING THESE BIGGASS UNNECESSARY ASS COMMENTS". The cap is well motivated; the gap is purely that it gets consulted at commit time instead of at write time.
- completed, commit 0796403
