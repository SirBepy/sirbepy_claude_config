# Audit verify template

Copy this into `.for_bepy/audit/VERIFY.md` (or the project's scratch equivalent)
for Phase 4 and dispatch one refuter per report (or per 2-3 small reports) once
every area/cross-cutting report has landed. Built from the fibo frontend2 audit
(session e3334a4a, 2026-10-01 to 2026-10-03): 21 reports, one refuter each, which
rejected 3 findings outright, downgraded about 16 (mostly HIGH to MEDIUM), and
added 2 real HIGHs the auditors had missed - the refutation pass earned its cost.

## Why a refuter, not the orchestrator reading everything

At 15-30 reports, every CRITICAL/HIGH read by the orchestrator directly doesn't
fit in one context window. A refuter per report keeps each verification read
scoped to one report's claims, and the orchestrator then only reads the
CONFIRMED CRITICAL/HIGH lines the refuters hand back - a fixed, small set
regardless of how many reports were dispatched.

## Refuter dispatch (one per report, or per 2-3 small reports)

Give the refuter: the report's full text, the repo root, and this instruction -
read every CRITICAL and HIGH's cited `path:line` yourself, follow each link of a
multi-step claim separately, and return a verdict file. `model: 'sonnet'`,
read-only (same hard constraints as the audit rubric: no edits, no build tools).

## Verdict vocabulary

- **CONFIRMED** - you read the lines and the claim holds as stated. Keep the
  severity.
- **NARROWER** - the mechanism is real, the impact is smaller than claimed.
  Rewrite the impact honestly and propose a corrected severity. An exaggerated
  CRITICAL costs more credibility than a missed MEDIUM.
- **UNVERIFIED** - part of the claim depends on something outside the repo (a
  third-party binary's behavior, a runtime property, a live system state).
  Label that part `UNVERIFIED` explicitly and say what would settle it. Never
  let a verified half launder an unverified half into a clean CONFIRMED.
- **WRONG** - the cited lines don't support the claim, or you traced it and the
  failure mode doesn't actually occur. Drop it. State the reason in one
  sentence - this feeds the merged report's "looks bad but is actually fine"
  section.

## Drift check (run before verifying, not after)

If the audit outlives even a small amount of time between the dispatch sha and
the sha you're verifying against, a cited file may have changed underneath the
finding. Before trusting or rejecting a finding:

```
git log --oneline <audited-sha>..HEAD -- <cited path>
```

If that cited file changed since the audit's sha, re-read the CURRENT lines,
not the ones the original report quoted, before confirming or rejecting. Note
the drift explicitly in the verdict ("file changed at <sha>; verified against
current HEAD, not the audited version") so the orchestrator knows the verdict
is about today's code, not a snapshot.

## Missed section

Every refuter also does a quick independent pass over its report's slice (not a
full re-audit - bounded, maybe 10-15 minutes of reading) looking specifically
for anything the original auditor missed in that same slice. Report these under
a `## Missed` heading in the verdict file, same severity/receipt rules as a
normal finding. This is where the fibo audit's 2 extra real HIGHs came from -
a second reader with the rubric already loaded catches different things than
the first.

## Verdict file format

```
## VERIFY: <report's slice name>

### <original finding title>
- **Verdict:** CONFIRMED | NARROWER | UNVERIFIED | WRONG
- **Corrected severity:** <if NARROWER, the new severity; otherwise omit>
- **Reasoning:** one to three sentences, citing the line(s) you actually read.
- **Drift:** none, or "file changed since <sha>, verified against current HEAD"

### ... (repeat for every CRITICAL/HIGH in the report)

## Missed
### <SEVERITY> | <title>
(same shape as a normal finding - Where/What/Why it matters/Fix/Confidence/Effort/Lens)
```

## Who writes the merged report (Phase 5)

A dispatched subagent returns findings as text; it does not write report files to
disk - that's a harness-level rule on every `Agent`-tool dispatch, not a
project-specific hook, and it is why a prior merge attempt that dispatched a
subagent to write `.for_bepy/audit/REPORT.md` was refused and returned 79KB of
inline text instead, which then had to be extracted by hand. The fix is
structural, not a workaround: **the orchestrator (the session running `/audit`
itself, never a dispatched subagent) performs the final Write of the merged
report.** Refuters and auditors return their text; the orchestrator reads each
return value and writes the single merged file itself. If the merged text is
too large for one assembly pass, have the orchestrator append to the file
across several of its own Write/Edit calls rather than delegating the write.
