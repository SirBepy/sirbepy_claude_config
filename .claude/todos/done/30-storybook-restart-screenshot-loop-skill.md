<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=4, content-hash=a3bae045 -->
# Skill for the Storybook restart-wait-screenshot loop

**Type:** skill-improvement
**Origin:** ai

## Goal

Collapse the three-command dance of "restart Storybook, poll until it answers, screenshot a story"
into one reusable step. It ran roughly fifteen times in a single design session on 2026-07-29 and
was hand-assembled every time.

## Context

Design work in `frontend2/` is done in Storybook, and every visual iteration needs the same
sequence:

1. `POST /procs/frontend2:storybook/restart` against the server_supervisor API (token and port read
   from `%APPDATA%\com.sirbepy.server-supervisor\supervisor\`).
2. Wait for the dev server to actually answer. Screenshotting too early fails with
   `ERR_CONNECTION_REFUSED`, which happened on the first attempt after several restarts. A bare
   `Start-Sleep` is blocked by the harness, so the working pattern was a bash
   `for i in $(seq 1 40); do curl -sf -o /dev/null <url>/index.json && break; sleep 3; done`.
3. `node C:/Users/tecno/.claude/skills/screenshot/screenshot-helper.cjs --url
   "http://localhost:<port>/iframe.html?id=<story-id>&viewMode=story" --viewport WxH --wait N
   --screenshot <out.png>` then `Read` the PNG back.

A restart is required (not just HMR) whenever a NEW file introduces Tailwind classes that were not
already in the generated CSS: the first render of variants F/G/H silently lost `lg:grid-cols-3`
because Tailwind had not rescanned, which cost a full wrong-looking screenshot and a re-shoot.

Two sharp edges worth encoding:
- The screenshot helper rejects `--plan` combined with `--screenshot`. In plan mode the screenshot
  step's output key is `out`, NOT `path`; using `path` reports `Saved: undefined` and writes
  nothing.
- Capture viewport width matters later. Screenshots taken at wildly different widths (500px up to
  1850px) looked fine individually but broke a summary deck, where `width: 100%` upscaled the
  narrow ones past their natural size. A skill should either standardise widths or record the
  capture width alongside the file.

## Approach

Add a skill (suggested name `/story-shot`) taking a story id, an optional viewport, and an optional
`--restart` flag. It should:

- Resolve the supervisor token/port and the running Storybook entry's CURRENT port. Do not hardcode
  42020; the port moved between sessions (a prior handoff recorded 42001).
- Restart only when asked, then always poll `/index.json` until it answers before capturing.
- Verify the story id exists in `/index.json` first and fail with the near-miss ids listed, rather
  than screenshotting a Storybook error page.
- Write to `.for_bepy/screenshots/` and print the path plus the capture dimensions.

Check `~/.claude/skills/screenshot/` first: this may be better as a Storybook-aware mode on the
existing screenshot skill than as a new one.

## Acceptance

- One invocation replaces the restart, the poll loop, and the helper call.
- Passing a story id that does not exist fails fast with a useful message.
- Never produces a screenshot of a not-yet-booted or error-state Storybook.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] Blocked by todo 58 (the skills-directory audit), which is itself waiting on your answer about how it should run. Nothing to decide here directly: answer 58 and this unblocks.

## Notes

Related existing memory: `fibo-storybook-render-sweep` (build-storybook does not render stories, so
a green build proves nothing) and `supervised-run-ports-reshuffle-verify-identity` (re-resolve the
entry port rather than assuming it). A render-sweep script was written this session at
`frontend2/.for_bepy/story-sweep.cjs` but never run; it may belong in the same skill, and todo 159
already tracks committing it.

**Confirmed again (2026-07-30, canonical-item icon-card mockup session):** a brand-new arbitrary
Tailwind value (`h-48`, `w-28` - not used anywhere else in the codebase) silently rendered as if
unstyled in an already-running Storybook dev server, even several minutes and multiple HMR saves
later - not just immediately after adding the file. Confirmed via injecting a debug `<pre>` into
the page listing `document.styleSheets` rules: `.h-48`/`.w-28` genuinely did not exist in any
loaded stylesheet. Workaround used instead of a restart: pass an inline `style={{width, height}}`
for one-off/debug-only sizing rather than a brand-new bracket utility class - sidesteps the whole
class ever needing to be scanned. If `/story-shot` gets built, it should probably auto-restart
whenever a story file references a Tailwind utility class not found via a quick grep of the rest
of `src/`, rather than requiring the human to notice the render looks wrong.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 172; renumbered to 30 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: new `/story-shot` skill, or a Storybook-aware mode on `/screenshot`, per the fully
  specified Approach - resolve the supervisor token, port and live entry port; a `--restart` flag
  that polls `/index.json` before capturing; verify the story id exists first and fail with
  near-miss suggestions; default output into `.for_bepy/screenshots/` with capture dimensions
  recorded. Blocked on the skill audit, todo 58. This was produced by a strict second-pass
  re-triage that specifically asked whether a defensible answer exists without the dev; it
  concluded yes. Not executed only because the session ended.
- Relocated to todo 258 in C:\Users\tecno\Desktop\Projects\fibo via /cleanup-todos 2026-08-19: the 58 audit ruled /story-shot a fibo-local skill, and the dev confirmed on 2026-08-19 that this ruling stands over the 2026-08-07 move into ~/.claude.
