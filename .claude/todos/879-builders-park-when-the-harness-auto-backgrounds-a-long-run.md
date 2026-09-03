<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo covers the auto-background case. 441 is /supervised-run enforcement, 430 is cross-model delegation. A grep for "auto-background", "600000", "outlives its own" across the backlog returned nothing. -->
# 879 - Builders park instead of reporting when the harness auto-backgrounds a long command

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-02

## Goal

Stop a builder subagent silently converting a long-running command into an indefinite wait, when
the preamble already tells it exactly what to do instead.

## Context

Observed three times in one zng-app session on 2026-09-02, with `refs/builder-preamble.md`'s ban
pasted verbatim into every one of those dispatch prompts.

The ban says `run_in_background` is FORBIDDEN, that any command which may exceed 120 seconds must
pass an explicit `timeout` up to 600000ms, and that a command outliving its own 600000ms cap must
be reported as partial output plus the exact command still in flight, "never a bare 'still
waiting'".

What actually happens: the agent obeys the first two clauses, passes `timeout: 600000`, and the
command STILL exceeds the cap because a full e2e suite legitimately takes 14 minutes. The harness
then auto-backgrounds it. At that point the agent is in the third clause's territory, but instead
of reporting partial output it sets up a `Monitor` and ends its turn with a non-report:

- `"Standing by for the phase 2 background run to complete - will report back once the monitor fires."`
- `"I have set up a monitor to notify me when the first full suite run completes. Pausing here."`

Both returned as a completed dispatch with no findings, wasting the whole run. A single direct
nudge ("deliver the final report now, no waiting") recovered a real report both times, which is the
documented recovery in `refs/delegation-doctrine.md` - but the recovery firing twice in one session
means the preamble text is not landing.

The gap is that the ban is phrased around a CHOICE the agent makes (`run_in_background: true`),
while the failure mode is a thing the harness does TO it. An agent that never chose to background
anything reads the ban as already satisfied.

## Approach

1. Rewrite the clause in `refs/builder-preamble.md` so it leads with the harness-initiated case
   rather than the agent-initiated one. Something to the effect of: if a command you foregrounded
   gets auto-backgrounded past its cap, you are now in the reporting case - read the log file from
   disk, quote its tail, name the PID still running, and deliver the report. Do not start a
   `Monitor`. Do not end a turn with an intent to report later.
2. Name `Monitor` explicitly as forbidden in a builder. The current text bans `run_in_background`
   but says nothing about `Monitor`, and both agents reached for `Monitor` specifically.
3. Consider whether this is enforceable rather than restated. Per `refs/delegation-doctrine.md`'s
   own note (todo 290, the em-dash case), "a flag is a fix, never a louder restatement of the rule"
   - three violations of a verbatim-pasted rule is the same shape. A `Stop`-hook check on a
   subagent's final message for a parked non-report ("standing by", "will report back", "pausing
   here", "waiting for the monitor") would catch it mechanically. Check first whether hooks can see
   a subagent's final message at all; `hooks/_hooklib.py`'s `read_payload` may not distinguish
   subagent turns, which is the same open question recorded in the doctrine's "Out-of-scope
   findings" section.

## Acceptance

- The preamble's long-command clause leads with the auto-backgrounded case and names `Monitor`.
- Either a hook catches a parked non-report, or a note in the doctrine records why it cannot, so
  the next person does not re-derive the question.

## Notes

- Do not weaken the timeout guidance while fixing this. Passing `timeout: 600000` is still correct;
  the problem is only what happens after it is exceeded.
- Filed from a zng-app session per CLAUDE.md's rule that a finding about the global tree belongs in
  this repo's backlog, not the surfacing project's.
