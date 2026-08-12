<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Ship ONE parameterised Playwright measure + screenshot helper, instead of re-authoring it every round

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop hand-writing the same Playwright preamble (launch, viewport loop, navigate, wait, measure
overflow, save PNG to the right folder) at the start of every UI round. Ship it once as a real,
committed script that `/screenshot`, `/mockup`, and any responsive sweep all call with arguments.

## Context

This todo is a merge of three fibo-backlog todos, confirmed by the dev on 2026-08-07 during an
`/auto-do-todos` run. All three independently asked for the same artifact from a different angle:

- **fibo 189** (`189-frontend2-screenshot-sweep-skill.md`) - the ad-hoc frontend2 responsive
  screenshot + overflow-measurement harness gets rebuilt from scratch every session; make it a
  reusable skill (either extend `/screenshot` or add a new one).
- **fibo 219** (`219-mockup-skill-should-ship-its-own-scaffold-and-measure-script.md`) - `/mockup`
  should ship its own staging-chrome scaffold (`Watermark` / `MockupSection` / `Stage` / `StageRow`)
  AND a parameterised measure script, rather than the skill describing them in prose and every run
  re-authoring both.
- **fibo 220** (`220-scratch-screenshots-ignored-the-per-session-subfolder-rule.md`) - whatever
  script ships must auto-resolve and DEFAULT to the per-session
  `.for_bepy/screenshots/<claude-ancestor-pid>-<ancestor-start-ticks>/` subfolder, because the
  convention is currently followed ad hoc and gets skipped under time pressure.

The originals are archived in `fibo/.claude/todos/done/` with a pointer to this file; read them
there for the full incident detail, especially 219's scaffold component list.

Related, deliberately NOT merged: **fibo todo 206**
(`206-reusable-local-app-driver-for-frontend2.md`) stays in the fibo backlog. It wants a
frontend2-local app driver (bring the dev server up, log in, land on a route) under
`frontend2/scripts/`. It is the project-side half of the same "stop rewriting the preamble" theme:
206 gets you a logged-in page, this todo measures and shoots it. Whoever picks up either one should
read the other first so the seam between them is one function boundary, not two overlapping scripts.

Known repo gotchas the helper must already encode (all previously learned the hard way, see the
fibo project memories):

- Connect over CDP to a **supervised** dev server via `localhost`, not `127.0.0.1`, and bypass the
  MCP browser with `playwright-core` when the extension is unavailable.
- `main` is the scroll container in the Fibo frontends, not `document.body` - measure overflow on
  `main`.
- `animate-page-in` leaves a transform behind, which breaks `position: fixed` descendants; a
  measurement pass has to account for that or portal the element to `body`.
- The existing `/screenshot` helper takes no `--width`/`--height`; tall pages are captured via URL
  fragments. Any new flag surface should be additive, not a silent redefinition.

## Approach

1. Decide the home: extend the existing `/screenshot` helper script vs a new sibling script the
   three skills share. Prefer extending, so there is one entry point, unless its current flag
   surface makes that awkward.
2. Write the script with real arguments: URL (or route + base), a viewport list, an output folder
   that DEFAULTS to the resolved per-session subfolder, an optional overflow-measurement mode, and
   an optional CDP endpoint for attaching to a supervised server.
3. Make the per-session folder resolution a function in the script, not a documented convention:
   resolve the Claude ancestor PID + start ticks, create the folder if missing, return the path.
   Callers that pass nothing get the correct folder for free.
4. Port `/mockup`'s staging-chrome scaffold (per fibo 219) into shipped files the skill copies in,
   rather than prose the model re-implements.
5. Update `/screenshot`, `/mockup`, and the docs that describe the ad-hoc harness to call the
   script instead of describing it.

## Acceptance

- A responsive sweep across 3+ viewports with overflow measurement runs from ONE command with no
  inline JS authored that session.
- Passing no output path lands the PNGs in the correct per-session subfolder, verified by listing it.
- `/mockup` produces its staging chrome from shipped files, not regenerated markup.
- Nothing regresses in `/screenshot`'s existing invocation shape (no `--width`/`--height` reappearing
  as a required flag, fragment-based tall captures still work).

## Notes

- Merged from fibo todos 189 + 219 + 220 by `/auto-do-todos` on 2026-08-07, confirmed by the dev.
  The three were tracked separately only because each surfaced in a different session.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: extend `skills/screenshot/screenshot-helper.cjs` with a viewport-list flag,
  overflow measurement, and a CDP-attach flag, with output defaulting to the resolved per-session
  screenshots folder. Port `/mockup`'s staging-chrome scaffold into shipped template files and
  update both skills to call it. "Prefer extending over a new script" is the todo's own stated
  default. Blocked on the skill audit, todo 58, though it is arguably surface-reducing since it
  merges logic duplicated across `/screenshot` and `/mockup`. This was produced by a strict
  second-pass re-triage that specifically asked whether a defensible answer exists without the dev;
  it concluded yes. Not executed only because the session ended.
- 2026-08-08 (hubbub /mockup round): fresh evidence, one more requirement for the helper -
  `screenshot-helper.cjs` line ~98 runs `await page.evaluate(step.js)` and DISCARDS the return
  value, so /mockup's mandatory computed-style/getBoundingClientRect verify steps produce nothing;
  the session had to hand-roll a one-off Playwright script (requiring the helper's hardcoded
  npx-cache playwright path) just to read the check values. The shipped helper must print
  evaluate results (console.log JSON) for plan mode to satisfy /mockup's verify contract.
- Duplicate of 63 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
