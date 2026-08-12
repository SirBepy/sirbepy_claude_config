<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=1, content-hash=a1abda47 -->
# /brainstorm should re-read the relevant CLAUDE.md section before designing, not just the todos backlog

**Type:** skill-improvement

## Goal

Close the gap in `~/.claude/skills/brainstorm/SKILL.md` that let a full design session re-derive a
system that was already specified, and already committed, in `~/.claude/CLAUDE.md`.

## Context

On 2026-08-01 a long session designed a "global cross-project memory vault" from scratch: scoping
rules, where person records live, which store wins for which fact type. All of it already existed as
the `## Global Knowledge Vault` section of `~/.claude/CLAUDE.md`, committed 2026-07-30 in `862b02e`.
Worse, that section was present verbatim in the session's opening context the whole time.

The same session then began regenerating 11 `People/*.md` notes in the Obsidian vault from a blank
template. They were already migrated, with richer content than the regenerated versions (real
`last_seen` dates, personal anecdotes). Only the Write tool's read-before-write guard stopped the
overwrite. Both failures share one shape: acting on a remembered impression of a file rather than
its current contents.

Why the existing rule didn't catch it: brainstorm step 1 currently says "Check the todos backlog
first, then explore code." The prior work was in neither place. It was in the global instruction file
itself, which the skill never tells you to re-read, presumably because it's assumed to be "already
loaded". That assumption is exactly what failed.

Related memory written the same session: `feedback_context_loaded_is_not_applied` in
`.claude-personal/projects/C--Users-tecno--claude/memory/`.

## Approach

Edit step 1 of `~/.claude/skills/brainstorm/SKILL.md` ("Check the todos backlog first, then explore
code") to add a cheap pre-check before any design work:

1. `Grep` `~/.claude/CLAUDE.md` (and the project's own `CLAUDE.md` if one exists) for a section
   heading or keyword matching the thing about to be designed.
2. `git log -S "<distinctive phrase>"` on the file that would be changed, to see whether the idea was
   already implemented and committed in an earlier session.
3. State explicitly that content being in context since session start is NOT evidence it has been
   applied, and is a reason to re-check rather than to skip.

Keep it to a few lines. This is a pre-check to add to an existing step, not a new phase, and
brainstorm's whole selling point is that it's gate-free and low-ceremony. Do not add an approval
checkpoint.

## Acceptance

- `brainstorm/SKILL.md` step 1 names CLAUDE.md (global and project) as a place to check for prior
  art, alongside the todos backlog.
- The `git log -S` trick is mentioned concretely enough to be run without further thought.
- The skill stays gate-free: no new user-approval step is introduced.
- Total addition stays under roughly 6 lines, matching the file's existing terseness.

## Notes

Open question worth Joe's input when this is picked up: the same session wrote a new
`## Memory Discipline` section and a `## Global Knowledge Vault` scope test into CLAUDE.md, and those
two rules do not cleanly answer where Claude-Code-tooling facts belong. The scope test says
"would this matter in a totally different project? If yes, vault", which would push Claude Code
behavior trivia into Joe's personal Obsidian vault next to People/ and Cocktails.md. That is almost
certainly not the intent. Current convention (44 existing memories) keeps them in
`.claude-personal/projects/C--Users-tecno--claude/memory/`. Either the scope test needs a carve-out
for tooling facts, or the vault needs a section for them. Not urgent, but it will keep coming up.
- Dropped via /cleanup-todos 2026-08-12: worth 4/10. Main acceptance criterion already landed - brainstorm/SKILL.md step 1 now names CLAUDE.md as a place to check; only the git log -S trick remains, which is polish.
