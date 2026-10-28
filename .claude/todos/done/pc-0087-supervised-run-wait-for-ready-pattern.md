<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=1, content-hash=128d11c2 -->
# supervised-run skill should document a "wait for readiness" pattern

**Type:** skill-improvement

## Goal

Add a documented "wait until the process actually finished booting" pattern to the
`/supervised-run` skill (`~/.claude/skills/supervised-run/SKILL.md` per this project's user-level
skills), so future sessions don't hand-roll the same ad-hoc bash polling loop from scratch every
time.

## Context

During the sc-54840 release-testing session (2026-07-22/23), the same pattern was manually
written out as a fresh bash `until` loop at least 4 separate times: waiting for `zng-api:dev-up` to
print "Nest application successfully started", waiting for `zng-app:flutter-run` to print "Debug
service listening" / "A Dart VM Service", and similarly for a `zng-admin:flutter-run` restart. Each
time this was reinvented inline rather than following a documented recipe, costing a
`run_in_background` dispatch + wait cycle each time.

Current `/supervised-run` skill covers starting/reusing/restarting a process and reading its logs,
but has no explicit guidance on confirming a just-started (or just-restarted) entry has actually
finished its cold-boot sequence before the caller proceeds to use it - callers are left to
figure out per-tool readiness markers themselves.

## Approach

Add a short section to the skill (after the existing "Run it" / "Manage it afterward" steps)
covering:
- The general pattern: after `POST /procs/<id>/start` or `/restart`, poll
  `GET /procs/<id>/logs` for a readiness string, using `run_in_background` + an `until` bash loop
  (per this harness's own Bash tool guidance for "wait for a condition" patterns) rather than
  blocking synchronously.
- Known readiness markers worth documenting as examples (not exhaustive, but save future sessions
  the discovery cost): NestJS (`"Nest application successfully started"`), Flutter web, generic
  Node dev servers (whatever "ready"/"listening on port" line they print).
- **The Flutter marker depends on the `-d` target - do not ship one grep pattern for both.**
  `-d chrome`/mobile print `Debug service listening on ws://` (or `A Dart VM Service`);
  `-d web-server` never prints it at all (that path needs the Dart Debug Chrome extension) and
  instead prints `[flutter] app started` / `[flutter] serving at http://localhost:<port>`.
  Merged from todo 278: on 2026-08-11 a zng-admin wait-loop grepped for `Debug service listening`
  against two `-d web-server` builds; both had compiled fine in ~45s but the loop blocked
  indefinitely on a condition that could never become true, and the dev noticed the turn looked
  stuck. Writing this section from 87's original wording alone would ship exactly that bug.
  The Port table's `Flutter web (auto-reload)` row is the place to state it.
- On `-d chrome`/mobile only, `app.started`/`app started` fires BEFORE the debug connection is up
  and can still be mid-DDC-compile - which is why that target wants the debug-service line.
- A callout that a genuinely large Flutter web app's first cold DDC compile after a fresh
  `flutter run` can legitimately take 1-3+ minutes even after "Debug service listening" appears -
  don't assume a blank/white first page load automatically means something's broken; wait longer
  (up to ~60-90s) before concluding a real problem.

## Acceptance

- The skill file has a documented, copy-pasteable wait-loop pattern instead of leaving each session
  to reinvent it.
- Includes at least the NestJS and Flutter-web readiness markers above as worked examples.
- The Flutter-web example distinguishes `-d web-server` (`app started` / `serving at http://`) from
  `-d chrome`/mobile (`Debug service listening on ws://`); a single shared pattern fails review.

## Notes

Related: `~/.claude-personal/projects/c--Users-tecno-Desktop-Projects-zng-app/memory/reference_playwright_local_dev_e2e_methodology.md` (written this same session) already documents the
Playwright-side auth-bypass gotchas and DB fixture patterns for this same testing effort - this
todo is specifically about the process-readiness-waiting half of that same session's work,
scoped to the skill file rather than project memory since it's a general harness-usage pattern,
not project-specific.
- completed, commit d31c4de
