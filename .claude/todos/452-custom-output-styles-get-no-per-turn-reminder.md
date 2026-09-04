<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=7, reconfirm-count=3, content-hash=af3408dd -->
<!-- duplicate-checked -->
# Custom output styles get no per-turn reminder, so Silent will fade

**Type:** task
**Origin:** ai

## Goal

Give the active custom output style the same per-turn reinforcement Claude Code gives its
built-in styles, so `output-styles/silent.md` does not quietly stop applying partway through a
long session.

## Context

Filed 2026-08-20, the session that wrote `output-styles/silent.md`.

Verified by reading the installed binary at `C:\Users\tecno\.local\bin\claude.exe` (v2.1.237):
every built-in style object carries a `turnReminder` field alongside `prompt`, and the harness
re-injects that one-liner every turn. Concise's is `"Be concise: lead with the result, skip
preamble and narration, keep only what the user needs."` The custom-style frontmatter schema is
`.strict()` and accepts only `name`, `description`, `keep-coding-instructions`, and the
plugin-internal `force-for-plugin`. There is no `turn-reminder` key. A custom style is injected
into the system prompt once at session start and never reinforced.

This is not theoretical. `done/209-caveman-mode-reinforcement.md` recorded the exact failure:
caveman mode "faded back to normal-length structured prose" over a long, topic-mixed session
because its `SessionStart` hook fired once. That todo was dropped 2026-08-11 as moot only because
the caveman plugin was uninstalled. `silent.md` reintroduces the same one-shot-injection shape,
so the underlying problem is live again.

`done/239-delegate-sticky-orchestrator-mode-carrier.md` proposed a `UserPromptSubmit` hook as the
carrier for the structurally identical problem (sticky mode with no mechanism behind it). It was
dropped 2026-08-11 for having "no live incident cited, purely a theoretical compaction risk".
That objection does not apply here: 209 is the live incident, and `silent.md` is the live artifact.

Prior art worth reading before building: `smixs/awesome-claude-output-styles` ships
`hooks/style-reminder.sh`, a `UserPromptSubmit` hook that reads `outputStyle` from settings,
exits silently for `default` and the built-ins (which already get the reminder), and otherwise
echoes `"<Name> output style is active. Remember to follow the specific guidelines for this
style."` Their `implementation-notes.md` states they made it opt-in via an `--enforce` flag
rather than default, on the grounds that silently writing hooks into someone's settings during a
style install is too invasive. That reasoning does not apply here since this is Joe's own repo.

## Approach

1. Confirm the gap still exists in whatever `claude.exe` version is installed at the time. The
   schema is read from the binary, so a later release could add a `turn-reminder` key and make
   this whole todo unnecessary. Check first, do not assume.
2. Write `hooks/output-style-reminder.py`, following the existing hook conventions in
   `~/.claude/hooks/` (Python, not shell, matching `status-marker-guard.py` and friends).
   It reads `outputStyle` from `settings.local.json` first, then `settings.json`, and emits
   nothing unless the value names a file that exists under `output-styles/`.
3. Emit a reminder derived from the style itself rather than a generic sentence. For `Silent`
   the load-bearing line is rule 1: put everything in `send_message`, write nothing outside tool
   calls. A generic "remember your style" nudge is weaker than restating the actual constraint.
   Consider reading a `<!-- reminder: ... -->` comment out of the style file so the reminder
   lives next to the rules it reinforces, but note that HTML comments in a style body DO reach
   the system prompt verbatim, so keep it short.
4. Register it under `hooks.UserPromptSubmit` in `settings.local.json`.
5. Measure before trusting it. Reinforcement that fires but changes nothing is worse than no
   reinforcement, because it looks solved.

## Acceptance

- The hook fires on every prompt submit and is verifiably silent when `outputStyle` is `default`
  or one of the built-ins (`Proactive`, `Concise`, `Explanatory`, `Learning`), so the harness
  reminder is never doubled.
- It fails safe: unreadable, missing, or malformed settings degrade to emitting nothing, never
  to crashing the turn.
- A long topic-mixed session with `Silent` active still produces short `send_message` bubbles
  near the end, not just at the start. State how this was checked; "it looks fine" is not a check.
- `output-styles/silent.md` itself is unchanged by this work.

## Notes

Do not fold this into an existing hook. It is its own trigger and its own failure mode.

If the measurement in step 5 shows the style holding fine without a hook, close this as declined
and record that result. A hook that solves nothing is worth less than the settings entry costs.
- Advanced in /mega-todos wave 2, commit `3348930`, NOT finished. `hooks/output-style-reminder.py` is a UserPromptSubmit hook that reads `outputStyle` from settings.local.json then settings.json, stays silent for the default and the five built-ins, and for a custom style re-injects a short reminder derived from the style file's own text. Remaining: acceptance item 3 wants proof that a long topic-mixed session with Silent active still produces short bubbles near the end, which cannot be observed inside one dispatch. What WAS verified is that the hook fires deterministically and picks the right text. Confirm item 3 by simply noticing whether Silent holds through a long session from here on, rather than staging an artificial one.
