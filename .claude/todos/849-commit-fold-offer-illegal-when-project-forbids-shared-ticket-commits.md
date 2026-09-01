<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=1, content-hash=2eca5178 -->
<!-- duplicate-checked -->
<!-- Nearest neighbours checked: no existing todo covers overlap-check.sh's fold offer or its
     interaction with a project commit-style.md. 469 is about handoff mode vs the duplicate guard,
     a different contradiction. -->
# /commit's HEAD-overlap fold offer can be illegal under a project's own commit-style

**Type:** skill-improvement
**Origin:** ai

## Goal

`/commit` step 8's unpushed-overlap policy should recognise that a project `.claude/commit-style.md`
can forbid the fold it is about to offer, so a session does not have to silently pick between two
rules it was told to follow.

## Context

Hit 2026-08-31 in zng-app. Two commits were being made in one session, one per Shortcut ticket
(sc-55209 and sc-55220). Both had to touch `e2e/run-all.js`, which carries one flow-registration
line per ticket. After the first commit landed, `overlap-check.sh` exited 1 on the second:

```
e2e/run-all.js:86-91 ce11d12 55209: Navigate off the root navigator after the entry awaits
```

The blamed sha WAS `HEAD`. `~/.claude/skills/commit/SKILL.md` step 8 says for that case:
"interactive session, overlap includes HEAD - STOP, name the overlapping commit and the blamed
lines, ask via `AskUserQuestion` whether this is follow-up on the same unit of work (-> `git reset
--soft HEAD~1`, restage everything together, one fresh commit) or genuinely separate (-> proceed)."

But zng-app's `.claude/commit-style.md` says: "**Different tickets never share a commit**, even if
the work is closely related (e.g. a ticket and its follow-up/replacement) and shipped in the same
session. One ticket = one commit, always." Folding two tickets into one commit is exactly what that
forbids, and step 1 of the same skill says the project file overrides the global defaults.

So one branch of the offered question is illegal, and asking it presents the dev a choice where one
option violates their own written rule. The session proceeded on the genuinely-separate branch and
disclosed it, which was right, but it had to reason its way there rather than being told.

## Approach

In `~/.claude/skills/commit/SKILL.md` step 8's unpushed-overlap bullet, before offering the fold:
check whether the repo's `.claude/commit-style.md` (already read in step 1) forbids sharing a commit
across the units involved. If it does and the overlapping commits belong to a different ticket than
the one being committed, skip the `AskUserQuestion` entirely, proceed on the separate branch, and
print one line naming the overlapping commit, the blamed lines, and the rule that ruled out folding.

Keep the question for the case the rule does not cover: same ticket, or no project commit-style.

## Acceptance

A dry-run of the zng-app scenario (two commits for two tickets both touching one shared registration
file) proceeds without an `AskUserQuestion`, prints the overlap and the quoted rule that made the
fold illegal, and still asks normally in a repo with no `.claude/commit-style.md`.
