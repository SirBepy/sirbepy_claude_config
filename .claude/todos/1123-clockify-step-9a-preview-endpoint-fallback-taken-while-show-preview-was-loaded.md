<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=863a0ded -->
<!-- duplicate-checked: grepped active + done/ for "hooks/preview", "show_preview". done/961 is about
skipping the visual entirely, done/997 about generating the calendar, 1036 about visual critique
findings. None covers choosing the HTTP fallback while the MCP tool is available. -->
# clockify-reconciliator step 9a: the run POSTed to the preview endpoint while `show_preview` was available, and the dev never saw the card

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-07

## Goal

Make sure step 9a's card always reaches the dev through `show_preview` whenever that tool exists,
so the HTTP fallback can't be picked to save tokens.

## Context

2026-10-07, zng-app session, `/clockify-reconciliator` for Zirtue week of 2026-10-05. The
`show_preview` schema was already loaded. To avoid pasting the ~16KB rendered HTML inline as the
tool's `html` argument, the run read `render_week.cjs`'s output file and POSTed it from node to
`http://127.0.0.1:27182/hooks/preview`. The endpoint answered with `{"id": "..."}` (HTTP 200). The
run then told the dev the card was up. The dev: "i dont see the preview man... u must not have read
the skill properly". Re-pushing the same slug through `show_preview` worked right away.

Two separate gaps:
1. SKILL.md step 9a does say the endpoint is a fallback only when the tool is unavailable, but the
   cost of inlining 16KB through `show_preview` is a standing temptation to skip it.
2. The endpoint's success response is not proof the dev saw anything, so a 200 from it gave a
   false "card is up".

## Approach

In `C:\Users\tecno\.claude\skills\clockify-reconciliator\SKILL.md` step 9a:
- State plainly: if `show_preview` is in the tool list (deferred or loaded), it is the only allowed
  transport. Its token cost is accepted on purpose. The endpoint is ONLY for sessions where the tool
  does not exist.
- Add the 2026-10-07 incident (endpoint 200, nothing in chat) as the reason.
- Optional, check whether it's worth doing: have `render_week.cjs` emit a smaller HTML (minified
  CSS, shorter block styles, rounded px values) so inlining it costs less.

## Acceptance

- Step 9a forbids the endpoint whenever `show_preview` exists and cites this incident.
- If the minify option is taken, the rendered card is visually unchanged (check it once via
  `show_preview`).
