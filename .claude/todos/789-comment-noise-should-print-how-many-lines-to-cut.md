<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=799a79e9 -->
<!-- duplicate-checked -->
# comment-noise.sh should print how many lines to cut, not just the current ratio

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/comment-noise.sh` print the target alongside the breach, so a flagged file
converges in one trim instead of three or four.

## Context

`skills/commit/comment-noise.sh:23`:

```awk
END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }
```

The ratio breach is self-referential: comment lines are counted in BOTH `c` and `add`, so cutting
one comment line shrinks the denominator too. "14/56 (25%)" does not tell you how many lines to
remove - the answer needs solving `c/(add - c_now + c) <= 0.25`, which is `c <= (add - c_now)/3`.

Measured cost on 2026-08-26 in `claude_usage_in_taskbar`: eight `prefilter-gate.sh` runs across two
commits, six of which were pure trim-and-retry. Sequences went 40% -> 30% -> 26% -> 25% -> pass,
each round guessing at the cut because the printed number moves as you trim.

The block-cap breach (`max[k]>=5`) has the same shape in miniature: it prints "longest 6" but not
"cap is 4", so the reader has to remember the number from `comment-noise.md`.

## Approach

Extend the `printf` at line 23 to name the fix, keeping the existing fields so anything parsing the
current shape still works. Something like:

```
src/foo.ts 14/56 (25%) longest 6  -> cut 4 comment lines, longest block to 4
```

`cut N` is `c_now - floor((add - c_now)/3)`, clamped at 0 (emit nothing when only the block cap
tripped). `longest block to 4` only when `max >= 5`.

The cap numbers stay defined in `skills/commit/comment-noise.md` - this change reads them, it does
not become a second place they live.

## Acceptance

- A file breaching only the ratio prints a `cut N` figure, and cutting exactly N lines passes on
  the next run.
- A file breaching only the block cap prints the target block length and no `cut N`.
- A file breaching both prints both.
- `python ci/run_all.py` green.
