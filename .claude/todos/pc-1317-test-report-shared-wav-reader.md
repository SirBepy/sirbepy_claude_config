<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new skill from pc-1315, whose scope did not cover this. -->
# /test-report: one WAV reader instead of two

**Type:** task
**Origin:** ai
**Summary:** The skill parses WAV files in two places, and one shared reader with a test should replace them.

## Goal

A single WAV reader used by both the voice client and the encoder.

## Context

Found by /code-check. `skills/test-report/scripts/tts-client.cjs:56` (`lengthMs`) and `skills/test-report/scripts/encode.cjs:12` (`readPcm`) walk RIFF chunks with the same loop. `lengthMs` also hoists a `var rate` out of an `if` inside that loop. `encode.test.cjs` covers `timeline` only, so neither parser has a test.

## Approach

Add `scripts/wav.cjs` exporting `readWav(file)` returning `{ rate, pcm }`, plus a small test that builds a WAV in memory, with an extra chunk before `data`. `lengthMs` becomes `pcm.length / 2 / rate * 1000`, and `readPcm` goes away.

## Acceptance

- `node scripts/encode.test.cjs` and the new test pass.
- A rebuilt report measures the same line count and 0 overlaps.
