<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=5, reconfirm-count=1, content-hash=95a4c552 -->
<!-- duplicate-checked: 857 is about dynamic PORT overriding a server's default; this is variant selection for templated commands -->
# sv.ps1 ensure: add -Param k=v so an agent can pick a server_supervisor command variant

**Type:** task
**Origin:** ai

## Goal

Let `skills/supervised-run/sv.ps1 ensure` request a specific variant of a parameterized
server_supervisor command (Flutter device, flavor, env file) without hand-rendering the template.

## Context

server_supervisor todo 0027 (commits `4fa0386`..`8ab9758`, 2026-10-06) made a stored command a
template such as `flutter run {DEVICE} --web-port {PORT}` with named params. `POST /run` accepts an
optional `params` object (axis name -> value id) that selects a variant; an unknown name or value id
returns 400 listing the valid ones. `GET /procs` exposes each proc's `params` and `resolved_cmd`.

Today `sv.ps1 ensure` matches the registry by exact `cmd` string (`sv.ps1` around line 115-129). A
templated command's stored `cmd` is the template, so a concrete `-Cmd` never matches locally and
falls through to `/run`. That is safe: `/run` matches the concrete line back to the template and
either starts a stopped command in that variant or, if it is already running on a different
variant, leaves it untouched and adds `param_mismatch: { running, requested }` to the response.
sv.ps1 currently ignores that field, so the caller never learns it got a different variant.

## Approach

- Add a repeatable `-Param name=value` to `ensure`, sent as `params` in the `/run` body.
- Print `param_mismatch` from the `/run` response when present, so the agent can decide to restart.
- Optionally match templated commands locally via `/procs`' `resolved_cmd`.

## Acceptance

- `sv.ps1 ensure -Cmd "<template or concrete line>" -Param device=chrome` starts the chrome
  variant; a bad value surfaces the 400 message; a running different variant prints the mismatch.

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): sv.ps1 ensure takes repeatable -Param name=value, sends params in the /run body, surfaces the 400 message and prints param_mismatch. Optional local resolved_cmd matching left out.
