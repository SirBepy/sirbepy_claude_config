<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=f30c0f43 -->
<!-- duplicate-checked -->
# The transcript-corpus harness gets rebuilt from scratch every time a hook needs measuring

**Type:** task
**Origin:** ai

## Goal

Make the "extract every real tool call from this machine's transcripts and measure a candidate
pattern against it" step a durable script in this repo, so the hook doctrine's own central
requirement stops costing a from-scratch rebuild each time.

## Context

The hook doctrine in `PLAN.md` is explicit: **measure against a real corpus BEFORE wiring anything.**
It is the rule that killed four guess-based hooks and saved a fifth. It is also, currently, an
instruction with no tooling behind it, so every session that follows it writes the extractor again.

Three rebuilds on record, each independent:

- **Todo 311** (`done/`) measured a chaining detector against "30047 unique real commands pulled from
  this machine's own transcripts across ~50 projects". Its prototype was deleted by todo 416 as an
  unadopted spike, and the extractor went with it.
- **Todo 342** (`done/`) measured three match scopes against "7128 real prompts" for
  `flagged-skill-mention`. Writeup survives in `hooks/flagged-skill-mention.md`; the harness does not.
- **Phase 2, 2026-08-21** (todos 419 and 420) rebuilt it a third time: 62,270 unique Bash/PowerShell
  commands and 22,992 Write/Edit calls, from 2,822 transcript files. Scratch scripts live in
  `C:\tmp\p2-corpus\` (`extract_commands.py`, `measure.py`, `inspect.py`, `measure_writes_final.py`,
  `dump_generic.py`) and will be reaped by `/disk-doctor` like any other `C:\tmp` scratch.

The rebuild is not the expensive part; **getting it subtly wrong is.** Real defects hit on the third
attempt: the first extractor escaped backslashes and newlines into a TSV in a way that could not be
round-tripped, so it was rewritten as JSONL and the whole 2,822-file pass re-run. A naive
`du -sh`/`find` over `~/.claude/projects` blew the 120s Bash timeout and orphaned a background task
(already a documented memory, and still stepped on). Neither mistake is visible in a summary; both
cost a full re-extraction.

There is a second, sharper argument for making this durable, learned the hard way in phase 2: a
corpus measurement proves only that no PAST command tripped a rule. Todo 419's guard measured **0
false positives across 62,270 commands** and still had three separate false-positive classes, two of
them caught only when the live guard denied its own author's commands. So the corpus is necessary and
not sufficient, which means the cheap half should be genuinely cheap, leaving the session's attention
for the hand-probing that actually finds things.

## Approach

1. Read `C:\tmp\p2-corpus\extract_commands.py` and `measure_writes_final.py` if they still exist;
   they are the most complete version and already handle the JSONL round-trip and the per-tool split.
   If `/disk-doctor` has reaped them, `hooks/flagged-skill-mention.md` documents todo 342's shape.
2. Decide where it lives, and say why in the file's own docstring. `ci/` is the natural home given
   `ci/run_all.py` already owns this repo's mechanical checks, but note this is NOT a check: it must
   never join `run_all.py`'s CHECKS tuple, because it takes minutes and reads Joe's whole transcript
   history. A `tools/` directory next to `ci/` is the other candidate.
3. Ship two pieces, not one:
   - **An extractor** that walks `~/.claude/projects/**/*.jsonl` and emits JSONL of
     `{tool, count, payload}` for a requested tool set (`Bash`/`PowerShell` for command rules,
     `Write`/`Edit`/`MultiEdit` for content rules). Dedupe by payload, carry an occurrence count.
     Output to a caller-named path, never a fixed one, so two measurements cannot clobber each other.
   - **A measurer** that takes a candidate module and a corpus file, calls the module's OWN matching
     functions, and prints per-rule hit counts plus a few full samples. It must import the real
     module rather than re-declare the patterns: a measurement holding its own copy of the regex
     proves nothing, and phase 2's dispatch had to say so explicitly to stop it happening.
4. Include a `--sample N` mode that prints the FULL text of every hit for one named rule. Judging a
   hit count as genuine or noise is the step that actually decides a tier, and it needs whole
   commands, not truncated ones.
5. Document it in one place a future hook author will actually look: a short section in
   `PLAN.md`'s hook-doctrine block, pointing at the script by path. The doctrine states the rule;
   this makes the rule executable.

## Acceptance

- Both scripts exist, are committed, and run from a cold session with no setup step.
- Re-running phase 2's measurement through them reproduces its published numbers: 0 hits for every
  CORE rule in `hooks/destructive-command-guard.py`, and 3 / 1 / 4 / 1 for the four MIDDLE rules.
  That is the regression test; a durable harness that cannot reproduce a known result is worthless.
- Neither script is wired into `ci/run_all.py`, and the docstring says why not.
- `python ci/run_all.py` still exits 0.

## Notes

Do not make this a skill. There is nothing for a model to decide here; it is two scripts with
arguments, and a skill would add a description to the always-loaded budget for no gain.

Do not cache the extracted corpus in the repo. It is roughly 18MB for the command set alone and
contains the full text of every command run on this machine, including any that carried a
credential on the command line. It belongs in scratch, regenerated on demand.

- ADVANCED in the /mega-todos wave-1 run, commit `99d6d43`, NOT finished. Both tools now exist:
  `tools/extract_corpus.py` walks transcripts to caller-named JSONL, and `tools/measure_corpus.py`
  imports the real candidate module's own matching function rather than re-declaring a copy of the
  regex under test. Both are deliberately kept out of `ci/run_all.py`'s CHECKS.
  REMAINING, two items:
  1. Acceptance asks that re-running phase 2's measurement through these tools reproduces its
     published numbers (0 hits for every CORE rule, 3/1/4/1 for the four MIDDLE rules). The builder
     reported this is not literally reproducible against a live, ever-growing transcript corpus, and
     this todo's own Notes forbid caching the corpus to freeze it. Settle what the acceptance should
     actually be: either pin a fixed transcript subset as the oracle, or replace the numeric
     reproduction with a weaker check (the tools run clean and agree with each other on the same
     input). Do not quietly declare it met.
  2. Approach item 5 wants the harness documented in `PLAN.md`'s hook-doctrine block, pointing at
     both tools by path. The builder could not do this: builders are barred from editing `PLAN.md`.
     It is a main-thread edit.
