<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=08c230df -->
<!-- duplicate-checked: done/441 added the guard, done/883 widened it; neither covers the fallback path -->
# supervised-run's "supervisor not reachable" fallback is blocked by dev-server-guard

**Type:** skill-improvement
**Origin:** ai

## Goal

When server_supervisor is down, Claude has one sanctioned way to start a dev server that the hooks
allow, instead of a skill telling it to do something a hook then denies.

## Context

2026-10-06, fibo session (frontend2 UX sweep): `sv.ps1 ensure` returned "supervisor not reachable -
fall back to a plain shell run". `skills/supervised-run/SKILL.md` "Fallback (supervisor not
reachable)" says: "Run the server the normal way (in your own background shell)... Do NOT try to
launch the supervisor app yourself." Claude ran `npm run dev -- --port 42024` with
`run_in_background`, and `hooks/dev-server-guard.py` denied it: "Route it through /supervised-run
instead of running it raw". Its header documents only one escape (a command invoking `sv.ps1`),
so the skill's own fallback can never pass the guard. The session was blocked until Joe started the
supervisor by hand.

## Approach

Pick one, then make the skill and the hook agree:

1. Give the guard an escape the fallback can use, e.g. allow the launch when a fresh `sv.ps1`
   health probe in the same session reported unreachable (marker file written by `sv.ps1` on that
   failure), so a raw launch is allowed only when the supervisor is proven down.
2. Or change the skill's fallback to "stop and ask Joe to start server_supervisor", matching what
   the hook enforces.

## Acceptance

- With the supervisor down, following `supervised-run/SKILL.md` exactly either starts the server or
  reaches a stated ask, never a hook denial.
- A test in `hooks/test_*.py` covers the chosen path.

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): decided resolution, no guard loosening. SKILL.md fallback and sv.ps1 Require-Supervisor now say stop and tell Joe the supervisor is down. No hook changed, so the existing test_dev_server_guard.py raw-launch cases already cover the guard side.
