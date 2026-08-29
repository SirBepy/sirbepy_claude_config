<!-- duplicate-checked -->
# Builders still background a long command and end the turn, despite the preamble forbidding it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "run everything synchronously, `run_in_background` is FORBIDDEN" rule in
`refs/builder-preamble.md` actually hold, instead of being prose a builder reads and then violates
by accident.

## Context

Four occurrences in ONE session on 2026-08-25 (claude_usage_in_taskbar, a `/mega-todos` run):

- The 780/781/783 cleanup builder: made every edit, then ended its turn with `cargo test --lib`
  still in flight. Committed nothing. Had to be resumed by hand.
- The settings-fix builder: same failure, **three times in a row**. Resumed twice, and on the third
  it had started a `Monitor` to watch its own backgrounded cargo and ended the turn waiting on
  that. The orchestrator gave up and finished the verify plus both commits itself.
- The orchestrator (main thread) hit the same trap once: a foreground `cargo test --lib` with
  `timeout: 600000` exceeded the ceiling and was auto-backgrounded by the harness.

The preamble text was present and verbatim in every one of those dispatches. It says
`run_in_background` is FORBIDDEN and that any command which may exceed 120 seconds MUST pass an
explicit `timeout` up to 600000ms.

**The mechanism, which is what makes this a design gap rather than carelessness:** the harness
auto-backgrounds a foreground command at its timeout. The tool default is 120s. A cargo build in
that repo routinely runs 2-10 minutes. So a builder that simply omits `timeout` gets its command
backgrounded *by the harness*, without ever calling `run_in_background`. It then observes "the
command is still running", concludes it should wait, and ends its turn - which is the documented
failure. It never knowingly broke the rule.

So the prose forbids the flag, while the actual trap is the missing parameter. Those are different
things, and only one of them is currently guarded.

## Approach

1. The cheapest real fix is a hook, not more prose. `hooks/dispatch-preamble-guard.py` already
   does a literal-substring check on dispatch prompts; the gap is on the OTHER side - the builder's
   own Bash/PowerShell calls. Consider a `PreToolUse` hook that inspects a Bash/PowerShell call for
   a known-slow command (`cargo build|test|check`, `pnpm build`, `npm run build`, gradle) and
   rejects it when no explicit `timeout` is set, with a message naming the value to use.
2. Failing that, make the preamble state the TRAP rather than the rule: "omitting `timeout`
   backgrounds your build whether you meant to or not" is the sentence that would have prevented
   all four, and it is currently buried at the end of a long paragraph whose topic sentence is
   about `run_in_background`.
3. Consider adding, to the same paragraph, what to DO when a command does outlive its ceiling -
   re-run it once (incremental builds resume cheaply) before reporting partial. Three of the four
   agents stalled because they had no next step, not because they lacked the rule.
4. Check whether `Monitor` should be named as forbidden for builders too. One agent used it to
   wait on its own backgrounded command, which turned a recoverable stall into a loop that kept
   re-firing task notifications.

## Acceptance

- A builder dispatch that runs `cargo test` without an explicit `timeout` is either blocked with an
  actionable message, or the preamble makes the auto-background trap unmissable at the point the
  rule is stated.
- The preamble tells a builder what to do when a command genuinely exceeds its ceiling, not only
  what not to do.
- Re-read `refs/builder-preamble.md` afterwards and confirm the `run_in_background` paragraph still
  reads as one coherent instruction rather than three stacked warnings.

## Notes

- Dropped via /cleanup-todos 2026-08-29: already fixed. refs/builder-preamble.md already carries both Acceptance bullets verbatim - an explicit timeout up to 600000ms is required on any command that may exceed 120s, and the only turn allowed to end unfinished is a foregrounded command outliving its own 600000ms cap.
