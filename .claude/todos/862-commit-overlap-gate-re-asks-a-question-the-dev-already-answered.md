<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /commit's overlap gate re-asks per commit a question the dev answered once

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/commit` step 8's unpushed-overlap policy a way to carry the dev's answer across the rest of
a session, so a multi-commit session stops blocking on the same fold-or-separate question.

## Context

Surfaced 2026-09-01 in a `windows_taskbar_widgets` session that landed four commits.

`skills/commit/SKILL.md` step 8's unpushed-overlap check has two interactive branches:

- overlap includes HEAD -> "STOP ... ask via `AskUserQuestion` whether this is follow-up on the
  same unit of work ... or genuinely separate"
- overlap is entirely non-HEAD -> "STOP, name the overlapping commits and blamed lines, ask via
  `AskUserQuestion` whether to fold via `/commit fold <sha>` or state it and proceed"

Both are written per-commit, with no memory across commits. In a session that commits three or
four times into the same files - which is the normal shape after a feature lands - the gate fires
every single time, and the answer is the same every time.

What actually happened: the gate fired on commit 1, the dev was asked, and answered "Two new
commits". It then fired on commits 2, 3 and 4 with structurally identical evidence (the same
files, overlaps mostly against commits from OTHER sessions, e.g. `8bd38bf`, `3a9a954`, `9ffcee2`).
Re-asking would have cost three more full round trips to re-confirm a decision already made, in a
session the dev had asked to wrap up. The agent proceeded on the earlier answer and said so in its
report - correct outcome, but it is a deviation from a rule written as "STOP", which means the
rule and the practice now disagree. That gap is the actual defect: a rule nobody can follow
literally gets ignored quietly next time, including in the cases where the question is real.

Note the honest counter-argument: the per-commit ask is not pure ceremony. Each commit's overlap
evidence genuinely differs, and "separate" for commit 1 does not logically entail "separate" for
commit 4. Any fix has to keep the question alive for a materially different overlap.

## Approach

1. Add a session-scoped answer to step 8's interactive branches: once the dev answers
   fold-vs-separate, record that answer for the session and apply it to later commits whose
   overlap is NOT materially different.
2. Define "materially different" concretely rather than by feel. A reasonable first cut: the
   overlap now includes HEAD when the recorded answer was given for a non-HEAD overlap, or it
   names a commit from THIS session that the recorded answer did not cover. Anything else reuses
   the answer and states it in the commit report instead of asking.
3. Keep the unattended-run branch exactly as it is - it already proceeds and records.
4. Whatever the shape, the skill must say plainly what to do when the answer is reused, so the
   report stays honest: name the overlapping commits and the fact that a prior answer was applied.

## Acceptance

- A session that commits three times into one file, with the same class of overlap each time, asks
  once and states the reuse on the other two.
- A commit whose overlap newly includes HEAD still asks, even after an earlier "separate" answer.
- `skills/commit/SKILL.md` step 8 reads as something a session can follow literally, with no
  judgement call left undocumented.
- `python ci/run_all.py` clean.

## Notes

- Do not solve this by weakening the gate to "warn and proceed". The overlap check exists because a
  pathspec commit says nothing about which lines ride along, and the fold decision is genuinely the
  dev's - the problem is only its repetition within one session, not the question itself.
- The same "answered once, re-asked per invocation" shape may exist in other gates that use
  `AskUserQuestion` inside a loop; worth a grep across `skills/` while in here, but file separately
  rather than widening this todo.
