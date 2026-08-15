<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=8, reconfirm-count=1, content-hash=8b2668a0 -->
# Builder-preamble omissions aren't caught until /close sweeps for them

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the delegation doctrine's mandatory dispatch-preamble lines fail loudly when
a dispatch omits them, instead of surfacing hours later as an orphan process or
an uncleanable screenshot folder.

## Context

`~/.claude/refs/delegation-doctrine.md` "Dispatch discipline" lists items every
builder prompt embeds "without exception", including the orphan-check text and
the pre-resolved `.for_bepy/screenshots/<pid>-<start-ticks>/` id. The doctrine is
emphatic about both, and both were still omitted.

Observed 2026-08-14 in `revaire-mobile`, in three emulator dispatches written by
hand across one session:

- **Orphan check omitted.** An agent reported it had stopped its `flutter run`.
  The process was alive ~2h later, found only by a `/close` Phase 6 sweep. It
  also carried a live API key in its command line, visible to any process listing
  (`--dart-define=EPHEMERAL_API_KEY=...`).
- **Screenshot id omitted.** Screenshots went to a hand-picked
  `.for_bepy/screenshots/persona-signin/`. The doctrine explicitly warns this
  leaves files `/close` can never prove ownership of, and that is exactly what
  happened: the folder now cannot be cleaned by any session.

The rule already exists and was already read that session. Restating it more
loudly is the fix that has failed before (see the em-dash enforcement history
noted in the doctrine itself). The gap is that nothing checks.

## Approach

Options, roughly in order of cost:

1. **A dispatch-prompt linter.** A `PreToolUse` hook on the `Agent` tool that
   inspects the `prompt` argument and blocks when it lacks the required markers
   (`.for_bepy/screenshots/`, the staging line, the "run_in_background is
   FORBIDDEN" line) - and, when the prompt mentions `flutter run` / `npm` / a
   dev server, the orphan-check text. Mechanical, catches it at the only moment
   it is cheap to fix. Note the doctrine already considered and REJECTED a
   PreToolUse write-guard for a different problem (todo 291) on the grounds that
   the report-back channel sufficed; that reasoning does not transfer here,
   because there is no report-back channel for a preamble that was never written.
2. **Make the preamble a file, not prose to retype.** The doctrine already has a
   "Canonical builder preamble" block with four placeholders. Ship it as a
   template file the orchestrator reads and fills, so omission requires deleting
   a line rather than forgetting to type one.
3. **A `/close` Phase 6 process sweep**, which is what caught it this time - keep
   as a backstop regardless, but it is detection hours late, not prevention.

Prefer 1 + 2 together. 2 alone still relies on remembering to read the file.

## Acceptance

- A dispatch missing the screenshot id or (where applicable) the orphan-check is
  blocked or visibly flagged before the subagent starts.
- A session that runs emulator/dev-server dispatches ends with no orphan
  processes without the orchestrator having to remember to sweep.

## Notes

- Do not "fix" this by rewording the doctrine. It was read, quoted, and followed
  in most respects during the session that broke it; the two omitted items are
  precisely the ones with no downstream signal.
- Secondary finding worth folding in: a `--dart-define`/env secret passed to a
  dispatched process is exposed in that process's command line for its whole
  lifetime. Worth a line in the doctrine or process-hygiene about preferring a
  file or env var over a command-line argument for secrets in dispatched runs.

## Open questions

Written by /auto-do-todos on 2026-08-15. The next run opens with these.

- [ ] [ARCH] This repo's own hook doctrine (see `PLAN.md`) says exact mechanical checks ship and
      heuristic judgment calls do not, and it killed three detectors in one day on that basis. A
      preamble-enforcement hook is partly mechanical (is the staging line present, verbatim) and
      partly heuristic (is the orphan-check text required for THIS dispatch, which depends on
      whether it runs a dev server). Options: enforce only the always-required verbatim lines and
      ignore the conditional ones / measure the whole thing against a real corpus of past dispatch
      prompts first, per the doctrine / drop it and rely on `/close` sweeping for omissions as
      today. Recommended: **enforce the verbatim-only subset**, because that half is a string
      comparison and would have caught both cited incidents, while the conditional half is exactly
      the shape the doctrine rejects.
- [ ] [SEC] The Notes carry a separate finding: a `--dart-define` or env secret passed to a
      dispatched process sits in that process's command line for its whole lifetime. Options: fold
      a line into `refs/delegation-doctrine.md` / into `refs/process-hygiene.md` / file it
      separately. Recommended: **process-hygiene**, since it is about how processes are launched
      rather than how dispatches are written, and it applies outside dispatches too.
