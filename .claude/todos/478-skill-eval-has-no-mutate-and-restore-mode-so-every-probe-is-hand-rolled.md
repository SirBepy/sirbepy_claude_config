<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# skill_eval has no mutate-and-restore mode, so every regression probe is hand-rolled

**Type:** skill-improvement
**Origin:** ai

## Goal

Make "cut a section out of a skill, measure it, put it back" a flag on `tools/skill_eval.py`
instead of a scratch script written fresh each time.

## Goal is not

A general mutation-testing framework. One flag, one guaranteed restore.

## Context

Filed 2026-08-22 at the end of phase 3. Todo 422 built the harness; proving it worked needed the
same mutate-run-restore dance three times in one session, hand-written each time as
`C:\tmp\rate-it-regression-probe.py`, `C:\tmp\rate-it-fmt-probe.py`,
`C:\tmp\rate-it-repeat-probe.py`, plus a fourth in `C:\tmp\rate-it-preverify-probe.py` for 421's
before/after. All four are scratch and `/disk-doctor` will reap them.

This is the same complaint as todo 466 makes about the transcript-corpus harness, and it lands the
same way: the rebuild is cheap, getting it subtly wrong is not. Three real hazards were hit or
narrowly avoided:

1. **The skill under test cannot be a copy.** Skills resolve from `~/.claude/skills`, so a probe
   must edit the LIVE file and restore it. Every probe therefore needs a `finally` block, and a
   probe without one leaves a mutated skill on disk for every other concurrent session.
2. **A section cut can leave the skill half-converted.** 421's probe had to delete the verification
   section AND the synthesis steps that referenced it by name, or the "old" panel it measured never
   existed in that form. A naive single-section cut silently measures a chimera.
3. **The restore assertion was weaker than it read.** The probes compared `read_text()` output, not
   bytes, so a newline-translation difference would have passed as "byte-identical". It happened to
   be fine here because the repo stores these files CRLF, which is luck, not a check.

`resolve_skill_hash()` already exists in the harness for a related reason: a regrade after a
restore was re-hashing the restored skill and mis-attributing the run. That fix is evidence this
workflow belongs inside the tool rather than beside it.

## Approach

1. Add to `tools/skill_eval.py`, roughly:

   ```
   --cut-section "<heading>"   repeatable; delete from this heading to the next one
   --cut-file <path>           which file the cut applies to (default skills/<skill>/SKILL.md)
   ```

   With any cut requested, the runner: snapshots the target files' BYTES to the run dir, applies
   the cuts, records the mutated `skill_hash`, runs the fixtures, and restores from the byte
   snapshot in a `finally`, asserting equality on bytes.
2. Refuse the run if a requested heading is not found, rather than measuring an unmutated skill and
   reporting it as a mutant. That is the silent-failure shape that would waste a whole pass.
3. Print a loud line naming every file mutated and the byte count removed, then a matching
   RESTORED line. A probe whose restore is invisible is a probe nobody trusts.
4. Warn (do not block) when a cut section's heading text appears elsewhere in the file, which is
   the hazard 3 above: a reference to the removed section left behind.
5. Unit-test the pure parts in `tools/test_skill_eval.py`: heading-to-heading slicing, the
   not-found refusal, and that the snapshot/restore round-trips bytes for a CRLF file.

## Acceptance

- Reproduces phase 3's decisive result through the flag alone, no scratch script:
  `--only 5 --repeat 3 --cut-section "## How-to-raise rules"` against `/rate-it` scores materially
  below the 18/18 recorded for `v0-baseline-f5x3`, and `history.json` records a mutated
  `skill_hash`.
- The skill file is byte-identical afterwards, asserted on bytes and verified with
  `git status --porcelain`.
- A `--cut-section` naming a heading that does not exist exits non-zero and runs nothing.
- `python ci/run_all.py` exits 0.

## Notes

Do not wire it into `ci/run_all.py`. Same reason as the harness itself: it spends real money and
needs network, and `tools/test_skill_eval.py` already asserts the harness stays out of CHECKS.

Keep the flag out of the default path. A tool that can edit live skills should only do so when
explicitly asked, and the restore is the only thing standing between a probe and every concurrent
session reading a mutated skill.
