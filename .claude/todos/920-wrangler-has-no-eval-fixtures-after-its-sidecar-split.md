<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the likely hit, done/477, is the SPLIT itself and is complete. This is 477's optional "Consider" note, unbuilt, and it only became worth doing BECAUSE the split landed. Distinct work. -->
# /wrangler has no eval fixtures now that it is split across sidecars

**Type:** task
**Origin:** ai

## Goal

`/wrangler` has eval fixtures proving the skill still routes correctly after being split, so a
future edit to one sidecar cannot silently break a path that used to work.

## Context

Todo 477 split `skills/wrangler/SKILL.md` from 923 lines into progressive-disclosure sidecars on
2026-09-04 (commit `1ccac92`). Its own Notes suggested writing eval fixtures for the skill, shaped
like `skills/rate-it/evals/`, before or as part of the split. That was marked "Consider" rather
than required, and the builder correctly did not do it.

The split is exactly what makes this worth doing now. Before it, everything lived in one file and
a reader either had it all or none of it. After it, `SKILL.md` is a router: a task hits the entry
point and has to reach the right sidecar. That routing is a new failure mode with no coverage, and
it fails quietly - the skill still loads, it just never surfaces the section that had the answer.

`tools/skill_eval.py` now also has the mutate-and-restore mode added by todo 478 (commit `27630b0`),
which is the natural way to probe this: cut a sidecar, confirm the eval that depends on it degrades,
restore. That capability did not exist when 477 was written.

## Approach

1. Read `skills/rate-it/evals/` for the fixture shape, and `tools/skill_eval.py` for the runner
   contract, including the `--cut-section` / `--cut-file` flags added by todo 478.
2. Write one fixture per sidecar, each a task that can only be answered from that sidecar's content,
   so a routing failure shows up as a score drop rather than a pass.
3. Verify with the mutate-and-restore mode: with a sidecar cut, its own fixture should degrade
   materially while the others hold. A fixture that still passes with its sidecar removed is not
   testing the routing and should be rewritten.

Note before starting: `skill_eval.py` runs cost real money and network per its own docstring. Bound
the run, and say in the report what it cost.

## Acceptance

- One fixture per sidecar, each demonstrably dependent on that sidecar's content.
- A recorded before/after showing each fixture degrading when its own sidecar is cut.
- `python ci/run_all.py` passes. The fixtures themselves are not added to `ci/run_all.py`'s CHECKS,
  since they cost money and network.
