<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=1, content-hash=9fc9acb2 -->
# supervised-run: document the actual ready signal for `flutter run -d web-server`

**Type:** skill-improvement
**Origin:** ai

## Goal

Document, in the Port table's `Flutter web (auto-reload)` row, what log line actually signals a
successful compile/launch for `-d web-server` â€” so a future session doesn't grep for a string
that never appears there.

## Context

2026-08-11, zng-admin session: wrote a background wait-loop grepping supervisor logs for `"Debug
service listening"` to confirm two `flutter run -d web-server` builds (zng-admin, zng-biller)
compiled cleanly. That string only appears for `-d chrome` / mobile targets â€” `web-server` instead
prints `[flutter] app started` and `[flutter] serving at http://localhost:<port>` with no "Debug
service listening" line at all (the daemon needs the Dart Debug Chrome extension for that path).
Both builds had actually succeeded within ~45s, but the wait-loop sat blocked indefinitely on a
condition that would never be true. Joe noticed the turn looked "stuck" and asked directly before
it was caught.

Relevant file: `C:\Users\tecno\.claude\skills\supervised-run\SKILL.md`, Port table, `Flutter web
(auto-reload)` row.

## Approach

Add a line to the `Flutter web (auto-reload)` Port table row (or a short note directly below the
table) naming the actual success signal to grep/poll for: `[flutter] app started` (or `serving
at http://`) for `-d web-server`, vs. `Debug service listening on ws://` for `-d chrome`/mobile
targets. Anyone writing a wait-loop against supervisor logs should match on the signal that
corresponds to the actual `-d` target, not assume one grep pattern covers both.

## Acceptance

- SKILL.md's Port table (or the paragraph beneath it) states the web-server ready signal
  explicitly, distinct from the chrome/mobile one.

## Notes

- Migrated on 2026-08-12 from the dead top-level `~/.claude/todos/` path (was #02 there). That location was superseded by the repo-relative backlog on 2026-08-11; nothing reads it, so these were invisible to the Conductor app.
- Duplicate of 87 - merged during /cleanup-todos 2026-08-12. Its corrected readiness signals (-d web-server prints "app started"/"serving at http://", NOT "Debug service listening") folded into 87 Approach and Acceptance, which had the wrong marker.
