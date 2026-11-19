<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: grepped todos for subchat-todos; only pc-1344 (the build todo) covers the skill, neither of these gaps -->
# /subchat-todos resume rule and dirty-file criterion are underspecified

**Type:** task
**Origin:** ai
**Summary:** `skills/subchat-todos/SKILL.md` resumes from any existing `queue.md` regardless of phase, never stores the first-sub briefs of lanes past the fifth, and never says what makes a dirty file "this run's to commit" or what happens when a lane touches a file left dirty.

## Context

Found by the 2026-11-19 pre-push review of commit d557ba8 (fresh reviewer after the fix commit that followed it). Not fixed in the push because each needs a design call:

- SKILL.md "State lives on disk": "when today's `queue.md` already exists, skip to Phase 4". That also fires after a `--plan-only` run the same day (skipping preflight, baseline and scout and ignoring todo-id arguments), and when the run is already in Phase 5, 6 or 7, because the Log in `templates.md` records no phase.
- Phase 3 stores only each FOLLOWER's brief. The first-sub briefs for lanes 6 and later, which Phase 4's refill step spawns, are stored nowhere, so a respawn mid-run loses them.
- Phase 0 step 0 defines "this run's to commit" by pointing at Phase 1 step 1, and Phase 1 step 1 points back. A file left dirty contradicts the Phase 1 preamble (a sub cannot merge back over a dirty file); nothing handles a lane whose files include a left-dirty one. This repo's own tree is routinely in that state. The dirty-file questions also fit neither Phase 0 step 2's "defensible default" filter nor step 3's standing options.
- Only Joe can re-invoke a `disable-model-invocation` skill after a respawn; SKILL.md does not say so.

## Approach

Add a `phase:` field to the `queue.md` header (set to `run` when Phase 4 spawns the first sub, updated at Phase 5, 6 and 7) and resume only when it is not `plan-only`; store every lane's first brief in `queue.md`; state the dirty-file criterion (a file is the run's to commit when it is a todo file or a file under a lane's owned paths; any other dirty file is left alone and its lane is excluded); say that a respawned run is re-invoked by Joe.

## Acceptance

A `--plan-only` run followed by a real run in the same day starts at Phase 0; a respawn after the sixth lane was due resumes it; a dirty file inside a lane's owned paths is handled by a written rule.
