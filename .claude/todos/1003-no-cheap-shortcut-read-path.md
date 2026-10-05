<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: searched this backlog for shortcut/ticket read helpers; this is about a
     missing READ path for Shortcut specifically, not about /ticket's write/ground-check flow -->
# 1003 - No cheap read-only Shortcut lookup path, so sessions hand-roll curl

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-24

## Goal

Give Shortcut the same read-only affordance Linear already has, so a session that just needs to
read a story stops reinventing a token-extract + curl + python-parse one-liner.

## Context

- `skills/ticket/SKILL.md:217` states that Linear reads (search, list, lookup) are owned by
  `/linear` along with its `Invoke-Linear` helper. There is no Shortcut equivalent named anywhere
  in that file. `/ticket`'s only read-ish path is pickup (`SKILL.md:42`, "Ambiguous between update
  and pickup on a bare id: pickup. It is the read-only one"), which is framed as picking up a story
  to work on, not as a plain lookup.
- Observed 2026-09-24 in a zng-admin session: four separate hand-rolled lookups in one session
  (stories 54841, 54746, 54515, 53656, 55910, plus a `/search/stories` call), each rebuilding the
  same shape:
  `TOKEN=$(grep -a '^SHORTCUT_API_TOKEN=' ~/.claude/.env | sed ... | tr -d '\r"')` then
  `curl -s -H "Shortcut-Token: $TOKEN" https://api.app.shortcut.com/api/v3/stories/<id>` piped into
  an inline `python -c`.
- Two concrete costs, both hit in that one session:
  1. The `tr -d '\r"'` is load-bearing. `.env` has a BOM / CRLF issue already recorded in the
     `feedback_shortcut_ticket_transitions` memory of that project, and a naive `grep '^KEY='`
     fails. Every ad-hoc caller has to rediscover it.
  2. Printing a story description crashed with
     `UnicodeEncodeError: 'charmap' codec can't encode character '\u202f'` because Windows Python
     defaults to cp1250 and Shortcut descriptions contain narrow no-break spaces. Needed
     `PYTHONIOENCODING=utf-8` plus `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.

## Approach

Pick one, cheapest first:

1. Add an `Invoke-Shortcut` helper next to whatever `/linear` uses for `Invoke-Linear`, handling the
   BOM-safe token read and the UTF-8 stdout setup once. Then reference it from `skills/ticket/SKILL.md`
   the same way line 217 references the Linear one.
2. Or, if a whole helper is overkill, add a short "Shortcut reads" section to `skills/ticket/SKILL.md`
   with the exact working one-liner including the `tr -d '\r"'` and `PYTHONIOENCODING=utf-8` bits, so
   the gotchas are copy-pasteable rather than rediscovered.

Option 2 is the honest minimum. Do not build a full read skill unless the pattern shows up again.

## Acceptance

- A session needing to read a Shortcut story has one documented path it can follow without
  rediscovering the BOM strip or the cp1250 crash.
- `skills/ticket/SKILL.md` names that path, so the Linear/Shortcut asymmetry at line 217 is gone.

## Verify

- [ ] `grep -n -i "shortcut" C:\Users\tecno\.claude\skills\ticket\SKILL.md` - a reads section or helper is named
- [ ] Run the documented path against story 55910 and confirm the description prints without a UnicodeEncodeError

## Notes

- Low priority. This is friction, not breakage; every hand-rolled call did eventually work.
- Do not fold this into `/ticket`'s write flow or its ground check. Those are guarded by
  `hooks/shortcut-create-guard.py` for good reasons and are out of scope here.
