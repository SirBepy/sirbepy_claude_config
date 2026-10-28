<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=68e49a07 -->
# Update /supervised-run to use the new hub-port HTTP route

**Type:** skill-improvement

## Goal

`~/.claude/skills/supervised-run/SKILL.md` documents a workaround for finding a project's proxy
hub port. The workaround is now obsolete: server_supervisor shipped a first-class HTTP route for
it, so the skill should call that instead of reverse-engineering an internal bookkeeping detail.

## Context

server_supervisor commit `77e1e05` (2026-07-30) added `GET /projects/:project_id/hub-port` to the
localhost API in `src-tauri/src/api.rs`, inside the bearer-token authenticated section. It returns
the port as JSON, and returns 404 with the file's normal error body for an unknown project or for
a project with no presets configured (so "no hub" is distinguishable from a real port, never a
silent 0 or null). Two tests cover it in `src-tauri/tests/api_test.rs`
(`hub_port_without_presets_is_404`, `hub_port_with_preset_returns_the_port`).

The "Proxy hub" section of `supervised-run/SKILL.md` currently tells the agent to add a preset
first, then `GET /ports` and find the entry whose `owner` is `<project_id>:__proxyhub__`. That
owner string is an internal detail of `hub_owner()` in server_supervisor's `src-tauri/src/ports.rs`,
so the skill is coupled to a private naming convention that can change without notice.

This was flagged in server_supervisor's own todo 0026 Notes, which explicitly deferred it because
the skill lives in a different repo (this one) and therefore needs its own commit.

## Approach

- In `~/.claude/skills/supervised-run/SKILL.md`, "Proxy hub" section: replace the
  add-a-preset-then-`GET /ports`-and-match-the-owner-suffix workaround with a plain
  `GET /projects/<project_id>/hub-port` call, same bearer-token header as the other routes.
- Document the 404 case (no presets configured yet means no hub) so the agent does not read it as
  a transport error.
- Update the verified-endpoints line in that skill's Notes to include the new route.
- Do not restate the `__proxyhub__` owner string anywhere; dropping that coupling is the point.

## Acceptance

- `supervised-run/SKILL.md` no longer mentions `__proxyhub__` or the `GET /ports` owner-suffix
  lookup for hub-port discovery.
- The documented call matches the route as shipped: authenticated `GET
  /projects/:project_id/hub-port`, port on success, 404 when no hub is configured.

## Notes

Requires server_supervisor v0.1.34 or later (whatever release first contains `77e1e05`). If the
skill needs to work against an older installed build, say so in the skill text rather than keeping
the old workaround as a silent fallback.
- completed, commit d31c4de
