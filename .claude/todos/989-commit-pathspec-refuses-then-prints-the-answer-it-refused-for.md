<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# commit-pathspec refuses, then prints the exact answer it refused for

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `commit-pathspec.sh` costing two invocations for every commit in a session where stale session
markers exist. It already computes what it needs; it just will not use its own answer.

## Context

Measured 2026-09-11 during a long `/loop-todos` run in `countoff`: **10 of 10 commits** needed two
calls instead of one. Every single time, the first call ended with:

```
[own-range] derivation:
  - src/lib/collab.ts: auto-derived own-range 7-20,237-248,256-301, UNVERIFIED (4 live session
    markers - a peer may hold lines in this file, todo 924 REOPENED)
[foreign-hunk-check] UNVERIFIED, refusing (4 live session markers - ... declare --own-range for
the file(s) below, or rerun with --force foreign-hunk to proceed anyway): src/lib/collab.ts
```

and the second call was the identical command with `--own-range "src/lib/collab.ts:7-20,237-248,256-301"`
pasted back in from that very output. The ranges were never edited, never questioned, never wrong -
they were copied verbatim from the refusal message, every time, across 10 commits and roughly 30
files.

**The "4 live session markers" were not live.** `~/.claude/hooks/.session-markers/` held four
files; `list_peers` returned empty, and `git rev-parse HEAD` matched the expected sha on every
check. The markers were leftovers from ended sessions in other repos. The marker directory is
global, not per-repo, so a marker written by a session working in a completely different project
counts toward this repo's "a peer may hold lines in this file" verdict.

## Why it matters

The refusal is doing its job - an auto-derived range genuinely cannot prove absence of a foreign
hunk, and todo 924 is REOPENED for that reason. The problem is not the caution, it is that the
caution is paid for with a round trip that changes nothing. The caller reads a refusal, copies a
string out of it, and sends the same command back. That is a mechanical step the model has to
remember 10 times in a session, and the documented alternative (`--force foreign-hunk`) is strictly
worse because it skips the check rather than satisfying it.

It also trains exactly the wrong reflex. After the fourth identical refusal the temptation to reach
for `--force` is real, and `--force` is the option that would actually let a peer's hunk through.

## Approach

The narrow fix, and the one worth doing first: **make the marker count mean something.**

- Filter `~/.claude/hooks/.session-markers/` by liveness before counting, the same way
  `close/ai-todos-format.md`'s claims rule already does for `.claims/` - a marker whose PID is dead
  is not a live session. That alone would have taken this case from "4 live session markers" to
  zero, and every one of those 10 commits would have passed on the first call with no flag at all.
- Consider also scoping the count to markers whose session shares this repo. A session working in
  another project cannot hold a hunk in this one.

Only if liveness filtering is not enough:

- A `--accept-derived-ranges` flag that means "I read the derivation, I am asserting those ranges
  are mine" would at least make the second call carry intent rather than a copied string. It is
  strictly weaker than the caller genuinely knowing its own ranges, so it should not be the first
  move, and it must never be the default.

Do NOT widen `--force foreign-hunk`'s role here. It skips the check; the case above wants the check
to pass, which is a different thing.

## Acceptance

- In a repo where `list_peers` is empty and every session marker's PID is dead,
  `commit-pathspec.sh` completes a pathspec commit in ONE call with no `--own-range` and no
  `--force`.
- With a genuinely live peer session in the same repo, it still refuses exactly as it does today.
  Prove this: write a marker for a live PID, confirm the refusal returns.
- No path added that lets a foreign hunk through silently. The `--force` semantics are unchanged.

## Notes

Surfaced from a `countoff` session, filed here because the fix is entirely in
`~/.claude/skills/commit/`. The countoff side needed no change.

Related: todo 924 is the REOPENED item the refusal message itself cites, and this is a usability
consequence of that reopening rather than a disagreement with it.
