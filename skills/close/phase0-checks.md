# /close Phase 0: screenshot id and the visual-work and orphaned-probe checks

Read on demand from `skills/close/SKILL.md` Phase 0. Full wording and incident history; SKILL.md carries the rule in one line each.

Resolve this session's screenshot-subfolder id now: run `rename-session.ps1 -GetId` (or `.sh
--get-id`), which prints `<pid>-<procStart-ticks>` - resolved via `$env:CLAUDE_CODE_SESSION_ID`
matched against `~/.claude/sessions/*.json`, not a process-tree walk (todo 60: the walk resolved
to two different PIDs at two points in the SAME session; the sessionId match is stable). The
start-time suffix is load-bearing, not decoration: Windows recycles PIDs, so a bare PID can
collide with a dead session that left files behind; PID plus start time cannot. Also note two
separate flags, which answer different questions and must never collapse into one: whether this
session captured any screenshots at all (the **zero-writes flag**), and whether any capture was
actually put in front of Joe (the **shown-to-Joe flag**, see the visual-work check below). Phase 3
step 3 uses the id and the zero-writes flag only: the id locates this session's own subfolder for
Phase 4's screenshot count, and the zero-writes flag sets that count to 0 without touching the
filesystem.

**Visual-work check.** If any file changed this session matches `.css`/`.scss`/`.less`, or is otherwise a user-facing visual/layout change, and the shown-to-Joe flag above is false, add "show Joe a live screenshot of the visual change" to the unfinished-commitments list in `SKILL.md` Phase 0. The shown-to-Joe flag is true only if the transcript shows a frame actually reaching Joe this session - a `SendUserFile` call, `/preview`'s image branch, or equivalent - naming a screenshot tied to this change; it is NOT satisfied by files merely existing under `.for_bepy/screenshots/<id>/`. A `/e2e` or `/flutter-e2e` run (or any other automated harness) writes PNGs there that nobody ever looks at - that sets the zero-writes flag false while the shown-to-Joe flag stays false too, and it is the shown-to-Joe flag this check must read (todo 1027: a session that ran `pnpm run test:view` had the zero-writes flag read FALSE from 29 harness-written PNGs and the check never fired, though Joe saw none of them). CLAUDE.md's UI & visual changes section already requires this; a green headless/e2e test pass is not a substitute, since it cannot detect "this looks wrong" (2026-08-01: an AUQ card-height CSS fix shipped on a passing Playwright regression test alone, never shown live).

**Orphaned-probe check (todo 968).** If this project has any file under a `verify/`, `e2e/`,
`tests/`, `test/`, `__tests__/`, `cypress/`, `playwright/`, or `spec(s)/` directory, run
`python ~/.claude/tools/dead-probe-check.py --root <project root> --against HEAD` (uncommitted
changes), and if `git rev-parse --abbrev-ref --symbolic-full-name '@{u}'` resolves, also run it
`--against '@{u}..HEAD'` (this session's unpushed commits). It greps removed `title=`/`aria-label=`
(colon-truncated) and `id=`/`data-testid=`/`name=` (exact) literals against those directories for
a selector a deleted or renamed UI surface left dangling - no browser, seconds not minutes. Exists
because `/e2e` is deliberately opt-in per CLAUDE.md's testing floor, so nothing else re-checks a
tracked probe after the surface it drives changes; the incident (five commits shipped "verified"
on a dead `title^="Projects:"` selector, caught only because the dev happened to run `/e2e` by
hand) is in the todo file. Exits 0 always - it never blocks - but any finding it prints is a real
warning, not noise: it was measured against 143 real commits before being wired in and produced
exactly one hit, the one real incident, zero false positives (a bare-word version of the same idea
measured 9 false positives to 1 true positive on the same corpus and was rejected for that). Add
any finding to the unfinished-commitments list in `SKILL.md` Phase 0 exactly like a visual-work item, so it goes
through the same Phase 0 finish-or-file handling rather than getting silently
dropped if nobody reads the raw script output.
