<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=8, reconfirm-count=1, content-hash=fa01fc15 -->
# complete-todo.ps1 happily closes a todo that was never claimed, so the claim rule has no enforcement

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "claim before executing" rule detectable at the one moment a violation is guaranteed to be
visible: completion. Right now nothing anywhere notices that a todo went from backlog to `done/`
without ever having been claimed.

## Context

`~/.claude/CLAUDE.md` states the rule in the strongest terms it uses anywhere: *"Claim rule
(non-negotiable): before EXECUTING any todo, claim it via `.claude/todos/.claims/<id>.claim` per the
contract - every path, including ad-hoc 'do todo 07'."* `~/.claude/skills/close/ai-todos-format.md`
repeats it under "Claims - the mutex every executor obeys".

**It was still violated on 2026-08-14** in `claude_usage_in_taskbar`: a `/pickup` session correctly
claimed todo 641, then executed and completed todo 564 in the same run without ever claiming it. The
only trace was `complete-todo.ps1`'s own cheerful line - `No claim file for id 564 (already released
or never claimed) - nothing to remove.` That message treats "never claimed" and "already released" as
the same benign case, so the script printed the evidence of the violation and moved on. Nothing else
in the pipeline looks at claims at all.

The rule is prose-only, and prose-only rules in this tree have a track record of being re-broken -
see the em-dash enforcement history called out in `CLAUDE.md`'s Execution Discipline section, and
[[318-em-dashes-arrive-in-todos-filed-by-other-sessions]] for the same shape of problem.

This is deliberately NOT proposing a hard block. A concurrent session legitimately releases its claim
before the completion call in some flows, and `/cleanup-todos` archives todos it never executed, so
refusing to complete an unclaimed todo would break real paths.

## Approach

1. In `~/.claude/skills/close/complete-todo.ps1`, split the current single message into two distinct
   outcomes:
   - a claim file existed and was removed -> unchanged behaviour, quiet.
   - no claim file at all -> print a clearly-marked warning naming the rule, e.g.
     `WARNING: todo <id> is being completed with no claim on record - it was executed without
     claiming (see close/ai-todos-format.md). Not blocking.`
2. Do not change the exit code and do not refuse the completion. The point is a visible signal in the
   session transcript that a reviewer or the model itself can catch, not a new failure mode.
3. Consider the same split in `claim-todo.ps1`'s sibling messaging if it has an equivalent ambiguity.
4. Leave `/cleanup-todos`'s archival path alone, or give it a flag to suppress the warning, since
   archiving without executing is legitimate there.

## Acceptance

- Completing a todo that was claimed behaves exactly as today.
- Completing a todo with no claim on record prints an unmistakable warning and still succeeds.
- No path starts failing that used to work, `/cleanup-todos` included.

## Notes

- Filed by `/close` on 2026-08-14 from a first-hand violation in this session, not a hypothetical.
- The deeper fix would be for whatever executes a todo to claim it automatically, but that is a much
  bigger change across `/pickup`, `/batch-todos`, autopilot and ad-hoc runs. The warning is the cheap
  detection layer that makes the bigger fix's absence visible in the meantime.
- Completed via /auto-do-todos 2026-08-15: complete-todo.ps1 now splits the claim-release else branch, printing a named WARNING when no claim file matches instead of one undifferentiated line. Non-blocking by design, and idempotency re-verified. Honest limit recorded: the only signal at completion time is whether a .claim file exists right now, so this cannot tell never-claimed from claimed-then-released-early; no new release-log artifact was invented, per the todo Approach scoping this to a detection layer. claim-todo.ps1 was reviewed and needed no change, its four messages are already differentiated.
