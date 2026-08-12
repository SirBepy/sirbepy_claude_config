<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=b5ab818d -->
# /pickup and /mega-todos say nothing about an AskUserQuestion that times out mid-run

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the long-running execution skills a written answer for "the question card went unanswered and
the tool call died" so a session does not have to improvise it, and so the answer does not live only
in one project's memory store.

## Context

Hit for real on 2026-08-12 during a `/pickup` of `claude_usage_in_taskbar`'s todo 615, a 15-todo
`/mega-todos` batch. A `ask_user_question` call surfacing two genuine design forks aborted after
**2728s (~45 min)** with an MCP idle-timeout error (`sent no response or progress`,
`CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`). Joe had walked away.

Nothing in `~/.claude/skills/pickup/SKILL.md` or `~/.claude/skills/mega-todos/SKILL.md` covers this:

- `/pickup` Step 4 (Decisions gate) has exactly two branches, **Interactive** and `--unattended`.
  A run that STARTED interactive and became unattended because the human left is neither, and the
  skill has no third branch for it.
- `/mega-todos` adopts `/autopilot`'s contract, which does cover auto-deciding forks, but only by
  reference and only for forks known at triage time - not for one raised mid-run by the Step C scout
  and then left hanging.

The session improvised, and the improvisation was right: proceed on the option already badged
`recommended`, but only because both forks were reversible single commits, then report both
decisions prominently with an explicit offer to redo either. That reasoning currently exists only
in that ONE project's memory
(`projects/C--Users-tecno-Desktop-Projects-claude-usage-in-taskbar/memory/project_auq_never_auto_dismiss.md`,
"Timeout fallback" plus the 2026-08-12 observed-shape note). A `/pickup` in any other repo has no
access to it.

## Approach

Promote the rule out of project memory into global guidance. Preferred home is
`~/.claude/skills/pickup/SKILL.md` Step 4 as a third branch, since that is where the decisions gate
already lives, with `/mega-todos` inheriting it via its existing adopt-by-reference clause. If it
reads as broader than those two skills, `~/.claude/CLAUDE.md`'s Communication section is the
alternative home - but pick ONE, do not write it in both places.

The rule to write, matching what was actually done:

- A question that times out is a TOOL ERROR, not a "no", and not a signal to abandon the task.
- Proceed on the option explicitly badged/labelled recommended, **only** when the resulting action is
  reversible (a code change; never a deploy, push, destructive or outward-facing op).
- If no option is marked recommended, or the decision is high-stakes or hard to reverse, stop and
  leave the work parked instead of guessing.
- Report every auto-taken decision prominently in the final summary, with what it picked and an
  explicit offer to redo it. Never let an auto-decision read as though it were answered.
- Budget expectation: ~45 min of dead wall clock per unanswered card.
- Do NOT plan on `list_pending_prompts` as the recovery path. It was absent from that session's tool
  list entirely, so a recovery-then-continue flow cannot be assumed to exist.

## Acceptance

- One of the two files above gains the third branch; the other is left alone or references it.
- The text names the reversibility gate explicitly - that is the load-bearing half, and the part an
  improvising session is most likely to skip.
- A future cold session reading only `/pickup`'s SKILL.md can answer "the card timed out, now what?"
  without consulting any project's memory store.

## Notes

Filed from a `claude_usage_in_taskbar` session per global CLAUDE.md's rule that findings about the
global `~/.claude` tree belong in this repo's backlog, never the surfacing project's. Filing only -
the same rule forbids executing global work from a project session unless Joe says so in that
session, so this was NOT implemented at the time.
- completed, commit 458760a
