<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=2f2ffff5 -->
# Playwright MCP screenshots land in the repo, not the session screenshot folder

**Type:** skill-improvement
**Origin:** ai

## Goal

`mcp__playwright__browser_take_screenshot` writes to the working directory (or `.playwright-mcp/`),
NOT to `.for_bepy/screenshots/<pid>-<start-ticks>/`. Every skill that says throwaway shots live in the
per-session subfolder is silently wrong when the capture came through the Playwright MCP rather than
`screenshot-helper.cjs`.

## Context

Observed 2026-08-13 in a `fibo/frontend2` session. Screenshots were captured via the Playwright MCP
because the page needed interaction (a login, then a viewport resize) that the plan-file helper made
awkward. Every one of them landed as `frontend2/<name>.png`, i.e. **inside a git-tracked directory**,
and had to be moved by hand. This happened **three separate times** in one session, once with four
files at a time, and `git status` showed them as untracked additions in the repo each time. One
`Read` even failed first because the file was not where the tool's own return value implied.

Why the rules do not currently cover it:

- `~/.claude/skills/screenshot/screenshot-helper.cjs` auto-resolves a bare filename into
  `.for_bepy/screenshots/<pid>-<start-ticks>/`. That is where the convention comes from.
- `/mockup` step 5 and `/close` Phase 3 step 3 both assume that resolution happened, because both were
  written around the helper script.
- The Playwright MCP has no such resolution. Its `filename` parameter is relative to CWD, and it
  prefers `.playwright-mcp/` for its own artifacts.
- Consequence: `/close`'s purge is scoped to `.for_bepy/screenshots/<id>/` and proves ownership by
  subfolder, so MCP-captured shots are **never cleaned up** and can be committed by accident.

## Approach

Pick one and write it down in the affected skills rather than relying on remembering:

1. **Cheapest:** add a line to `~/.claude/skills/screenshot/SKILL.md` and to `/mockup` step 5 stating
   that MCP-captured screenshots must be moved into the session subfolder immediately after capture,
   and that the session id comes from `close/rename-session.ps1 -GetId` (never a hand-rolled name).
2. **Better:** state a single rule that the Playwright MCP is not the capture path for anything that
   needs to be kept or purged, and that `screenshot-helper.cjs --plan` is, since it already resolves
   the folder. Note the plan-file schema gotchas found the same day: the plan JSON is a **bare array**,
   not `{steps:[...]}`; a screenshot step's key is **`out`**, not `path`; and an `evaluate` step's
   return value is **discarded** (`page.evaluate(step.js)` is called without logging), so results have
   to be surfaced another way, e.g. injected into the DOM and captured in the shot.
3. Also worth stating in `/close` Phase 3 step 3: if a session captured via the MCP, check the repo
   root and `.playwright-mcp/` for stray `.png` files before closing, since the subfolder purge cannot
   see them.

## Acceptance

- A session that captures via the Playwright MCP either lands files in the session subfolder, or the
  skill text tells it to move them and to verify `git status` is clean of stray images before closing.
- The plan-file schema notes above are recorded where the `--plan` flag is documented, so the next
  session does not rediscover them through three failed invocations.
