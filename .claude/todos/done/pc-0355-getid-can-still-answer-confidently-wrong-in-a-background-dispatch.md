<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=5, reconfirm-count=1, content-hash=c35feef2 -->
# `-GetId` can still answer confidently wrong from a background dispatch, and the script cannot detect it

**Type:** task
**Origin:** ai

## Goal

Close, or consciously accept and document, the residual `-GetId` hole that todo 346's fix provably
cannot reach.

## Context

Todo 346 shipped on 2026-08-16 (commit `f95bc94`): `-GetId` now exits non-zero rather than trusting
the unstable process-tree fallback. Measuring it also **refuted** the suspected mechanism. Measured
facts from inside a real foreground subagent that day:

- `$env:CLAUDE_CODE_SESSION_ID` was present and non-empty.
- `-GetId` returned `34524-134313460443285792`, byte-identical to the orchestrator's own value.
- A process-tree walk confirmed the orchestrator's pid was a direct ancestor.

So a foreground dispatch shares the orchestrator's OS process, the primary sessionId lookup
succeeds, and the fallback is never reached. That is why todo 346's fix could not reproduce the
original incident.

The original incident had **two different pids** (36492 versus 35944), which only happens when the
subagent is a genuinely separate OS process. A background dispatch is the most plausible shape,
since it must outlive the orchestrator's turn. In that case the subagent has its own valid
`CLAUDE_CODE_SESSION_ID` and its own `sessions/<itspid>.json`, so the **reliable** lookup path
succeeds, self-consistently, and returns an id that is correct for that process and wrong for
doctrine purposes. It never touches the `pidwalk` tag todo 346's refusal keys off.

There is no local signal inside the script that distinguishes "my own session" from "the
orchestrator's session" once the primary lookup succeeds. That is precisely why
`refs/delegation-doctrine.md`'s resolve-once-and-pass-it-in rule exists, and that rule is what kept
the 2026-08-15 run safe.

## Approach

**Measure first, and from an actual background dispatch.** The foreground path cannot reproduce
this, so any fix designed without that measurement is guesswork. Print
`$env:CLAUDE_CODE_SESSION_ID`, the resolved pid, and `-GetId`'s output from inside a background
dispatch and compare against the orchestrator's.

Only then decide between:

- **Accept and document.** The doctrine rule already mitigates it, and defence in depth may not be
  worth new surface. Record the measurement in `rename-session.ps1`'s own header so nobody
  re-investigates.
- **Pass an expected id in.** Give `-GetId` an optional parameter naming the orchestrator's id and
  have it refuse on mismatch. This turns an undetectable divergence into a loud one, at the cost of
  every caller needing to thread the value through, which is what the doctrine already asks for.

Do not add a heuristic that guesses whether the current process is an orchestrator. This repo's hook
doctrine killed three guess-based detectors in one day, and this has even less signal to work with.

## Acceptance

- The background-dispatch case is measured, with the numbers written down and dated.
- Either the hole is closed, or the decision to accept it is recorded where the next reader hits it.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` from todo 346's builder report.
- Related: [[346-getid-silently-wrong-inside-a-subagent]] in `done/`, and todo 60 for the original
  process-tree-walk instability.
- 828688b: measurement taken from inside a real background dispatch and recorded in rename-session.ps1. The measurement was the deliverable.
