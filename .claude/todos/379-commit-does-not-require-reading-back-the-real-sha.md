<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=9, reconfirm-count=1, content-hash=4bb6d7d4 -->
# /commit never requires reading the real sha back, so a fabricated one reaches the dev

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` force the actual commit hash to be read out of git's own output before it can be
reported to Joe.

## Context

On 2026-08-18 in `zng-app`, a commit was made with
`git commit -m "..." -- <pathspec> | grep -v "^warning:" | tail -5`. On that repo git emits a
CRLF warning per file, so the filter left only `create mode` lines and **the summary line carrying
the sha was cut off**. The sha was never seen. It was then reported to Joe as `04e2f11` - a hash
that does not exist in the repo. The real one was `2958157` (later folded into `98142a4`).

Joe would have gone looking for a commit that was never there. It was caught only because the same
session later ran `git log --oneline` for an unrelated reason.

The root cause is a gap in the skill's contract, not carelessness in one run:

- `~/.claude/skills/commit/SKILL.md` step 8 specifies exactly how to build the `git commit`
  invocation, but says **nothing** about capturing or verifying the resulting hash.
- Nothing downstream re-reads it either. `/close` Phase 2 asks the model to "recall every sha THIS
  session's own commits produced" - which is precisely the recall path that failed here.
- The global rule in `CLAUDE.md` ("before asserting X about a system not read or run this session,
  read it first") already covers this in principle. It did not fire, because a sha does not feel
  like a claim about a system. That is what makes this an enforcement gap rather than a
  be-more-careful note.

## Approach

Add to `skills/commit/SKILL.md` step 8, right after the `git commit` invocation:

> After every successful commit, run `git rev-parse --short HEAD` as its own call and use THAT
> value anywhere the sha is reported or recorded. Never quote a sha from the commit command's own
> output, which is routinely truncated by output filters, and never from recall.

One extra call per commit, and it is immune to whatever filtering the commit line used.

Consider the same line in `close/SKILL.md` Phase 2, so its "recall every sha" instruction has a
verified source instead of relying on memory of an earlier turn.

## Acceptance

- `skills/commit/SKILL.md` step 8 contains an explicit `git rev-parse --short HEAD` requirement.
- A commit whose output is fully filtered still ends with a correct sha being reported.

## Notes

- Filed from a `zng-app` session per the "global findings go in the `~/.claude` backlog" rule. **Do
  not execute it from a project session** - global tooling work needs Joe's say-so in the session
  that does it.
- Related existing item: `377-commit-pathspec-blind-to-peer-working-tree-hunks.md`, also a step-8
  gap. Worth fixing in one pass.
