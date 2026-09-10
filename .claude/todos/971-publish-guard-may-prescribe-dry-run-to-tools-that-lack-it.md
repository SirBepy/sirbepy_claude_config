<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/945 fixed exactly one tool, wally, by hand and its Approach
     explicitly asked for this survey as separate follow-up work; this is the survey, not a
     second attempt at 945's own fix -->
# The publish guard may prescribe `--dry-run` to more tools than actually support it

**Type:** task
**Origin:** ai

## Goal

Establish, per tool, whether every publish command `hooks/destructive-command-guard.py` gates
actually supports the `--dry-run` flag its CORE rule orders the caller to add, and split out the
ones that do not, the way `wally` was split out.

## Context

Filed 2026-09-10 by `/loop-todos` cycle 1 from the out-of-scope findings of the builder that closed
`done/945-destructive-guard-demands-dry-run-wally-lacks.md`.

945 fixed one tool. `wally publish` was matched by the generic `PUBLISH_ANCHOR_RE` and denied at
CORE with "add `--dry-run`/`-n` first", a flag wally does not have, so a publish the dev had
explicitly approved could not proceed at all. The fix carved wally out into a MIDDLE-tier matcher
whose message names the real preflight (`wally package --output <file>`).

The same generic matcher still covers the other publish tools, and nobody has checked whether each
one has the flag. The builder that fixed wally said so plainly rather than guessing:

> "I did not verify whether `gem push`, `twine upload`, or `yarn` (classic v1) actually support
> `--dry-run` - I recall doubts about at least `gem push` and `twine upload`, but I have no receipt
> from this session and did not want to guess-fix an unmeasured claim."

That is the right call and it is why this is a separate todo: the failure mode is a guard that
blocks an approved, irreversible action with an instruction that cannot be followed, and the dev
has no in-session remedy when it fires.

## Approach

1. Read `hooks/destructive-command-guard.py`'s `PUBLISH_ANCHOR_RE` and enumerate every tool it
   matches. Do not work from the list in this file: it was written from one builder's recollection
   and the regex is the source of truth.
2. For each tool, get a real receipt for whether `--dry-run` (or `-n`) exists: `<tool> publish
   --help` / `<tool> --help` output pasted, or the tool's own documentation fetched. A tool not
   installed on this machine gets the docs route, and the verdict records which route it came from.
3. For each tool that lacks the flag, name what its actual preflight IS before moving it, the way
   `wally package --output <file>` was named. A tool with no preflight at all is a third case:
   decide deliberately whether it stays CORE with different wording or drops to MIDDLE, and record
   why.
4. Move each lacking tool into `match_publish_no_preflight` (or a per-tool table if the count makes
   a table cheaper than another regex), and add a test case per tool in
   `hooks/test_destructive_command_guard.py` proving both directions: the tool's publish reaches
   its intended verdict, and a tool that DOES have `--dry-run` is still CORE-denied unchanged.

## Acceptance

- Every tool matched by the publish rule has a recorded verdict with its receipt, including the
  ones that already have the flag.
- No tool is told to pass a flag it does not have.
- `python ci/run_all.py` exits 0, with a new test case per tool moved.

## Notes

- Do not extend the fix pattern to a tool on recollection alone. The whole reason this is a
  separate todo rather than part of 945 is that an unmeasured claim was correctly refused.
- A per-tool table is likely to age better than a growing alternation regex, but that is a call for
  whoever counts the tools in step 1, not a decision made here.
