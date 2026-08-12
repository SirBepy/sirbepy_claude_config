<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=2dca3755 -->
# work-recap should infer the zirtue group from cwd instead of always asking

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude/skills/work-recap/SKILL.md` Step 1 should infer `<group>` from the invoking session's
cwd when it's omitted and the repo unambiguously maps to one group, instead of unconditionally
asking via AskUserQuestion.

## Context

On 2026-08-11, `/work-recap weekly i just need the description/summary` ran from inside `zng-app`
(a zirtue repo). Step 1 currently says: "If `<group>` or `<variant>` is missing, ask the dev which
recap to run via AskUserQuestion." The session asked "zirtue or fibo?" while already running
inside zng-app, and Joe pushed back: "you know that i want zirtue... we are in the zirtue
repo... so... idk whats going on here." See zng-app repo's own memory
`feedback_work_recap_group_no_ask_in_zng_app.md` for the live incident.

## Approach

In `~/.claude/skills/work-recap/SKILL.md` Step 1, before asking, check the invoking session's cwd
against known repo-to-group mappings:

- `zng-app`, `zng-admin`, `zng-api`, `zng-biller` -> `zirtue`
- any fibo-named repo -> `fibo`

If cwd matches exactly one group, use it directly, skip the question. Only fall back to
AskUserQuestion when cwd doesn't map to a known repo (e.g. run from `~` or an unrelated folder),
or when `<variant>` (weekly/daily) is also missing - variant still always needs asking since cwd
can't disambiguate that.

## Acceptance

- Running `/work-recap weekly` (or `daily`) from inside zng-app/zng-admin/zng-api/zng-biller no
  longer prompts for group; it proceeds straight to the zirtue variant.
- Running the same from an unmapped cwd still asks, unchanged.
- Fibo repos still map to `fibo` without asking.

## Notes

- completed, commit 937f802
