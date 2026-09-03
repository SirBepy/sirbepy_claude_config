<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog and done/ for "list_peers", "peer", "handoff" - no todo covers making the peer check a step inside a skill. The existing coverage is a zng-app memory (feedback_list_peers_before_every_commit_and_push), which is recall-dependent; this is the mechanical half. -->
# 890 - /handoff and /close Phase 3 should check peers before asserting work is unstarted

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-02

## Goal

Add a peer-channel check to the skills that write artifacts claiming what is or is not already being
worked on, so the claim is verified mechanically rather than depending on the model remembering a
project memory.

## Context

Filed from a zng-app session on 2026-09-02, per CLAUDE.md's rule that findings about the global
`~/.claude` tree live in this backlog rather than the surfacing project's.

Joe asked for a sweep of a month of QA Slack tickets, written up via `/handoff`. The resulting todo
asserted in writing that eleven items were unstarted. Two were not: a live peer session had sc-55405
reproduced, root-caused and fixed, and had independently found sc-55360's root cause. Its two
untracked `e2e/repro-55405-*.js` files were sitting in the shared working tree and got written up as
abandoned WIP. Both shipped within the hour as `d850735` and `c479fa0`.

Joe caught it himself - "check with other agents if one of them picked up some of these issues tho
ofc". One `list_peers` + `read_messages` pair answered it completely, and one of the two live peers
was literally named `sc-55405 name-step mechanism`.

**Why the existing coverage did not fire.** `feedback_list_peers_before_every_commit_and_push` (a
zng-app memory, now carrying this as its fifth incident) lists the triggers as: before the first
edit, before commit, before push. Every one is a WRITE to the repo, so the check reads as a
concurrency-safety habit about file collisions. Writing a handoff is none of those - no file in
`lib/` is touched, nothing is staged, nothing is pushed - so no trigger matched, and the check was
skipped without any rule being consciously broken.

But the claim being made was factual and about other sessions. `git log` cannot see uncommitted
work, and a peer mid-fix has usually not moved the Shortcut ticket yet, so neither source available
to `/handoff` can detect an in-flight session. The channel is the only thing that can.

This is an enforcement gap, not a "be more careful" fix: a memory helps only when recalled, whereas
a step in the skill runs every time.

## Approach

1. `~/.claude/skills/handoff/SKILL.md` - add a step before writing the todo: if the project has
   concurrent Conductor sessions, run `list_peers` and `read_messages`, and fold the result into the
   file. Cheapest useful form: any peer whose session name matches a ticket or file the handoff is
   about gets asked directly via `post_message` rather than inferred from the working tree.
2. `~/.claude/skills/close/SKILL.md` Phase 3 step 2 - same check before writing `task` todos from
   Phase 0/Phase 1, for the same reason.
3. `~/.claude/skills/close/ai-todos-format.md` "Handoff mode" - require the artifact to record the
   sweep and its timestamp, since the claim ages within minutes and the reader needs to know how
   stale it is. This is the durable half; steps 1 and 2 are just where it gets invoked.
4. Consider whether `/code-check` needs it too. Weaker case: its findings are about code, not about
   who is working on what. Probably out of scope - decide, do not assume.

Keep it conditional on peers actually existing. In a solo repo this must be zero extra calls, or it
becomes noise that gets skipped.

## Acceptance

- `/handoff` in a repo with a live peer produces a todo that names the peer sweep and its timestamp.
- `/handoff` in a repo with no peers is unchanged in output and costs no extra tool calls.

## Notes

- The related memory is `feedback_list_peers_before_every_commit_and_push` in zng-app's store. It
  was updated the same day with this incident and the widened trigger; if this todo lands, that
  memory's "How to apply" should point at the skill step instead of restating it.
- Do not widen this into a general "always check peers" rule. The specific failure is artifacts that
  assert unstarted state; a blanket check on every skill would be the kind of ceremony that gets
  ignored.
