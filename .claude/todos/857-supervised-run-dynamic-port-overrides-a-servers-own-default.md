<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# supervised-run: say that dynamic PORT overrides a server's own default port

**Type:** skill-improvement
**Origin:** ai

## Goal
State plainly in `skills/supervised-run/SKILL.md` that `ensure` sets `PORT` in the child's environment even when the command contains no `{PORT}` placeholder, so a server that reads `PORT` itself will NOT bind its own default. Name `-NoDynamicPort` as the fix.

## Context
Not a duplicate of the done todo `807`, which covers the client-side case: an app whose persisted `localStorage`/`sessionStorage` state is origin-scoped and breaks when the port moves between restarts. This one is the server-side case: the port a backend binds versus a port its clients hardcode. Different failure, different reader, different search terms.

The relevant sentence does exist today - "`use_dynamic_port: false` does not pin a port; it only accepts whatever port the app's own default is" - but it sits inside the **Pinned port for client-side persisted state** note added by `807`. Someone debugging "my API is running but nothing is listening on 3009" has no reason to read a paragraph about localStorage, so the fact is present and undiscoverable. The Port table itself only teaches the opposite direction: how to template `{PORT}` INTO a command.

Also missing everywhere: that `PORT` is injected into the environment regardless of whether the command templates it. That is the actual mechanism, and without it the behaviour reads as arbitrary.

Measured 2026-09-01 in zng-app. `ensure -Project zng-api -Cmd "npm run start:clean core"` started NestJS core, which reads `configService.get('PORT', 3000)`. It bound the supervisor's assigned port rather than 3009, which `e2e/run-all.js` hardcodes as `LOCAL_API_PORT`. The entry reported `status=running`, the process was alive and healthy, and `netstat` showed nothing on 3009. Cost ~15 minutes and two stop/rm/restart cycles.

## Approach
Add a short row or note to the Port table itself, not to the existing localStorage paragraph, phrased for the server-side symptom: an entry that reports `status=running` with a live process and nothing listening on the expected port means `PORT` was injected and the server honoured it. Say that `ensure` sets `PORT` in the child environment whether or not the command uses `{PORT}`, and name the `-NoDynamicPort` flag - `sv.ps1` accepts it (`sv.ps1:146` maps it to `use_dynamic_port`), but the SKILL.md only ever names the underlying API field.

## Acceptance
`grep -n "NoDynamicPort" ~/.claude/skills/supervised-run/SKILL.md` returns a hit, and it sits in or beside the Port table rather than only inside the client-side-persistence note.
