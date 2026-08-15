<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=5, reconfirm-count=1, content-hash=c3d787cb -->
# Replicate zng-admin's UI-verification Stop hook into zng-app and zng-biller

**Type:** task
**Origin:** dev

## Goal

Mirror zng-admin's once-per-session Stop hook into the two sibling Flutter repos (`zng-app`,
`zng-biller`) so the "show Joe the test URL + screenshots after a visual change" reminder fires
there too.

## Context

Relocated from `zng-admin/.claude/todos/21-replicate-ui-verification-hook-to-siblings.md`
(2026-08-14, Joe: "lets move it to global claude folder") since it's a cross-project-tooling
finding, not zng-admin-specific work.

Built in zng-admin on 2026-06-04. The hook lives in `zng-admin/.claude/settings.local.json` under
`hooks.Stop` (the `.claude/` dir there is gitignored = personal). It:
- Reads stdin JSON; exits silently if `stop_hook_active` is true (loop-safe).
- Exits silently unless `git status --porcelain` shows a dirty path matching `lib/.*ui/`.
- Fires at most once per session via a sentinel file `${TMPDIR:-/tmp}/zng-ui-reminder-<session_id>`.
- On fire, prints `{"decision":"block","reason":"...show the live URL from supervised-run + any
  screenshots just made..."}`.
- Uses only grep/printf/git (Joe's Git Bash has no `jq`), `shell: bash`.

The general principle already lives in global CLAUDE.md ("UI verification - show your work"), so
this is just the per-repo teeth. **Still unconfirmed as an active want**: Joe offered to do this
once, it was never actually built out, and when asked directly on 2026-08-14 he said he didn't
recall it - he chose to keep it queued here rather than drop it, but did not re-confirm he wants
it built. Confirm with Joe before executing.

## Approach

- Copy the `hooks.Stop` block verbatim from `zng-admin/.claude/settings.local.json` into each
  sibling's `.claude/settings.local.json` (create the file / merge with existing permissions; do
  NOT clobber).
- Keep the `lib/.*ui/` matcher - both siblings are Flutter with `lib/.../ui/` layout (verify each
  repo's UI path; zng-biller/zng-app may differ).
- Confirm each sibling's `.claude/` is gitignored before writing (zng-admin's is).
- Pipe-test both branches per repo (first stop fires, second silent) as done for zng-admin.

## Acceptance

- Editing a `lib/**/ui/**` file in zng-app or zng-biller and stopping triggers the reminder
  exactly once per session; subsequent stops are silent; non-UI edits never trigger it.
- `settings.local.json` in each repo still parses as valid JSON and existing permissions are
  intact.
