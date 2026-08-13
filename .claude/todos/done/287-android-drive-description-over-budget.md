<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /android-drive's description is 65 words, well over the skill description budget

**Type:** task
**Origin:** ai

## Goal

Trim `skills/android-drive/SKILL.md`'s `description:` frontmatter to roughly 25 words while keeping
every trigger phrase that makes the skill fire.

## Context

Found by `/code-check` Step 0 during `/close` on 2026-08-12, over the diff that created the skill
(commit `face099`).

`skills/android-drive/SKILL.md:3` carries a 65-word, 392-character description. The budget is
roughly 25 words / 120 characters. Skill descriptions load into every session's system prompt, so
this is a per-session token cost paid by every session on the machine, not just Android ones.

The current text spends most of its length enumerating the subcommand list ("boot/wait, screenshot,
tap, type, clear a field, dismiss the keyboard, read back, repeat"), which is discovery detail that
belongs in the body, not the trigger surface. The genuinely load-bearing parts are the trigger
phrases ("test this on the emulator", "drive the Android app through X", "tap through this flow")
and the two negative routes that stop it firing on the wrong surface (Flutter web goes to
`/flutter-e2e`, scripted Patrol suites are out of scope).

Note this skill is NOT `disable-model-invocation`, so the budget genuinely applies to it, unlike
the flagged skills that never load into the listing at all.

## Approach

Rewrite the description down to the trigger surface: what it drives, the two or three phrases a dev
would actually type, and the `/flutter-e2e` disambiguation. Move the subcommand enumeration into the
body, where it already partly lives. Do not drop a trigger keyword to hit the number, the budget
loses to firing correctly.

## Acceptance

- `description:` is at or near 25 words and under about 120 characters.
- Every trigger phrase and the `/flutter-e2e` disambiguation survive the trim.
- The subcommand list is still discoverable from the body.

## Notes

- Seven other skills (`brainstorm`, `code-check`, `flutter-e2e`, `iterate-it`, `rate-it`,
  `rate-it-and-commit`, `supervised-run`) are also over budget, but their descriptions predate this
  diff and were not touched by it, so they are recorded as a pre-existing observation rather than
  folded in here. Worth a single sweep if someone wants to reclaim the tokens.
- Done 2026-08-13. Description trimmed 65 words / 392 chars -> 27 words / 179 chars. Kept all three trigger concepts (test-on-emulator, drive-through-a-flow, tap-through-a-flow) and both negative routes (/flutter-e2e, Patrol suites). The subcommand list stays in the body.
