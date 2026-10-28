<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=fc46b21c -->
# impeccable's concept-seed.mjs CLI prints nothing on Windows when it resolves through the roll API

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `scripts/concept-seed.mjs` actually print its seed on Windows, so a session does not have to
work around it by calling the module directly, which is how the anti-argmax guarantee gets lost.

## Context

Hit on 2026-08-09 during a Split Opinions redesign (`hubbub-game-split-opinions`).

Running the documented command produced **empty stdout and exit code 0**:

```
node <skill>/scripts/concept-seed.mjs --scope direction --mode experience
```

Verified it was not an environment fluke: redirecting to a file gave an empty file, and the same
binary printed the `NO_PRODUCT_MD` gate message correctly when run from a directory without a
`PRODUCT.md`. So the synchronous paths flush and only the async one does not.

Cause, from reading the script: when no local catalog is bundled (the normal case for an
installed skill), `renderConceptSeed` returns a promise via `fetchRoll(...).then(...)`
(`concept-seed.mjs:325`). The CLI does `process.stdout.write(await renderConceptSeed(...))` and
then `process.exit(process.exitCode ?? 0)` at `:552`. On Windows a piped/redirected stdout is
async, so `process.exit` discards the pending write. The comment above that line says it exists so
the CLI "never lingers on a dead network path", which is the trade that broke it.

**Why this matters beyond an annoyance:** the workaround is to import the module and call
`renderConceptSeed({...})` from `node -e`, and in that call the `key` parameter is trivially
supplied. I did exactly that and passed a key I chose, which is precisely the "model picks its own
dice" failure the script exists to prevent. I caught it, discarded the roll and re-ran with a
random key, but the tool made the wrong thing the easy thing.

## Approach

In `scripts/concept-seed.mjs`, stop calling `process.exit` before stdout has drained. Either:

- `process.stdout.write(text, () => process.exit(code))`, or
- set `process.exitCode` and let the loop end naturally, using `unref()` on any lingering socket
  from `fetchRoll` so a dead network path still cannot hold the process open.

Then re-run the documented command on Windows and confirm the seed block prints.

Worth also considering: have `renderConceptSeed` refuse a caller-supplied `key` unless an explicit
`--from`/reproduce flag is set, so the module API cannot be used to hand-pick a roll.

## Acceptance

- `node <skill>/scripts/concept-seed.mjs --scope direction --mode experience` prints the full
  `DIRECTION CONCEPT SEED` block on Windows, both to a terminal and when redirected to a file.
- The no-network degraded path still prints and still exits promptly.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - process.exit() was already removed from impeccable/scripts/concept-seed.mjs:562-563 in favour of process.exitCode + natural exit. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
