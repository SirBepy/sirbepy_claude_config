<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=0d262793 -->
<!-- duplicate-checked: 1037 is impeccable's self-update failing; no open todo covers its Stop-hook findings loop. -->
# impeccable's Stop hook re-flags pre-existing lines on every turn, forcing empty turns

**Type:** skill-improvement
**Origin:** ai

## Goal

Once a file has been touched, the impeccable design hook stops re-injecting the same findings on
untouched lines at every Stop. Ideally it reports only lines the session's diff added.

## Context

claude_usage_in_taskbar session 2026-10-01/02 (Hidden-at-bottom sidebar change). The session edited
4 lines of `src/views/sessions/session-list.css`. From then on, every turn end got a Stop-hook
`additionalContext` block ("Design hook findings requiring review in session-list.css (12 issues)"
or "(4 issues)", alternating). It listed pre-existing values: the FAB's `rgba(0,0,0,0.4)` shadow,
1.6rem / 0.78rem / 10px font sizes, `#666` / `#ccc` fallbacks, and the `is-rate-limited` side-tab.
None of those lines came from this session.

Each injection starts a new model turn. Under the Conductor output style, every turn must call
`send_message` + `report_turn_status`. So the session spent about 15 turns posting "still ignoring the
design-lint noise" bubbles to Joe while waiting on CI and background runs. The hook's own text says
to suppress only after the user confirms, so the model had no clean way out.

## Approach

1. Find the impeccable Stop hook's config: the plugin's hooks.json, plus its "Suppressing further
   design hints after 6 edits" logic, which already exists for PostToolUse.
2. Scope Stop findings to lines in `git diff HEAD` for that file, or at least dedup: once a
   finding set has been surfaced and acknowledged for a file, stay quiet until the file changes again.
3. If it is a third-party plugin with no config knob, see whether a local wrapper or setting can
   disable the Stop event alone and keep PostToolUse.

## Success

Editing one line of a file with pre-existing findings, then running 5 more turns without editing
it, produces at most one Stop injection.


## Notes

- Completed by /loop-todos cycle 1 (2026-10-05); full CI green (7/7) before commit.