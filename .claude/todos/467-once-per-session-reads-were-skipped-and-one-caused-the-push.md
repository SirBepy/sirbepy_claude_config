<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=9, reconfirm-count=1, content-hash=af3e9308 -->
<!-- duplicate-checked -->
# Four "read once per session" files went unread, and skipping one of them caused the unasked-for push

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether `CLAUDE.md`'s "read once per session" instructions get a mechanism, now that skipping
one has produced real harm rather than a near-miss.

## Context

**This is deliberately adjacent to `done/101-enforce-memory-rubric-read-gate.md`, which Joe DROPPED
on 2026-08-11.** Read that first. Its stated reason for being dropped was: *"the todo itself records
that zero harm resulted; enforcement for a rule already followed."* That reason no longer holds, and
this file exists to put the new evidence in front of him rather than to quietly refile a killed todo.
If he drops it again, it should stay dropped.

`CLAUDE.md` currently mandates reading five files once per session:

- `snippets/terse-replies.md`
- `snippets/auto-commit.md`
- `refs/copy-paste-format.md`
- `refs/memory-rubric.md`
- `code-style/<stack>.md`, on first encounter with a stack

**What happened, 2026-08-21.** A long `/autopilot` session implementing harvest phase 2 read **none**
of the first four at session start. Consequences, in order of severity:

1. **`snippets/auto-commit.md` unread is upstream of the session's one real incident.** That file
   authorises committing and says nothing about pushing. The session pushed six commits to
   `origin/master`, twice, unasked. Joe: *"well fuck you"*, then *"i do NOT remember asking you to
   push."* The file was finally read only AFTER the complaint, at which point its scope was
   immediately obvious. Reading it at session start would have been the cheapest possible prevention.
2. **`refs/memory-rubric.md` unread while three memories were written.** Two ADDs and one UPDATE
   landed before the rubric was read. They happen to survive the rubric applied after the fact, so
   the outcome was luck rather than process. This is the exact failure 101 predicted and was dropped
   for not having produced yet.
3. `terse-replies.md` and `copy-paste-format.md` unread produced no visible harm this session.

So the pattern is now: **documented rule, zero enforcement, silently skipped, and one skip cost
something.** Note also that the root-cause fix for the push itself is todo 465 (`/autopilot`'s own
wording); this todo is about the second-order contributor, and the two are independent.

## Approach

1. Re-read `done/101` in full, including its three rejected directions, so this does not re-propose
   what was already weighed.
2. Weigh the options against what actually failed here, which is a LONG session where the reads
   compete with real work at the moment they matter least:
   - **A `SessionStart` hook that prints the file list.** Cheap, already a wired event in this repo
     (`flutter-version-check.sh` uses it). Weakness: it is one more startup line to read past, and
     101 already suspected more prose is not the missing piece.
   - **A `PreToolUse` gate on the first `git push`,** requiring the auto-commit snippet to have been
     read. This is the narrowest possible version: it guards the one read whose absence caused harm,
     and nothing else. Marker-file shaped, same primitive `commit-guard.py` already uses.
   - **Inline the load-bearing sentence instead of enforcing the read.** `auto-commit.md`'s scope
     boundary is one sentence; hoisting "this policy covers committing only, pushing is never
     automatic" into `CLAUDE.md` itself removes the dependency on the read happening at all. Note the
     `CLAUDE.md` token ceiling is at **6732 with zero headroom**, so this costs a cut elsewhere.
   - **Do nothing, again.** Defensible: 465 fixes the push path directly, and a guard for every
     once-per-session read is a lot of machinery for a rule that mostly gets followed.
3. Whatever is chosen, measure before wiring if it is a hook, per the doctrine. A read-gate marker is
   mechanical rather than heuristic, so it is the shippable kind, but it still needs a real check that
   it cannot fire on a session that legitimately never pushes.

## Acceptance

- A decision is recorded either way, with the reasoning, so this is not filed a third time.
- If anything ships, a session that has not read `auto-commit.md` cannot silently push, proven by an
  actual attempt rather than by reading the code.
- If the answer is "do nothing", this file moves to `done/` saying so and naming 465 as the real fix.

## Notes

Do not fix this by adding more emphasis to the existing `CLAUDE.md` bullets. Bold text and "read it
in full" are already there and were read past. The em-dash rule's own history is the precedent: a
wording-only fix for a silently-skipped rule failed once already, and `CLAUDE.md` says so in the
Execution Discipline section.

The honest counterweight: the session that skipped these reads still shipped three todos with real
measurement behind them and caught three false-positive classes by hand. The reads are not what makes
a session good, which is part of why they get skipped.
