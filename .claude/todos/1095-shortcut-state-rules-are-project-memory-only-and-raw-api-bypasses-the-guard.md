<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=9, reconfirm-count=1, content-hash=20fc6441 -->
<!-- duplicate-checked: no live todo mentions the mutation guard, the Testing ceiling, or raw-API Shortcut writes (grep 2026-10-05) -->
# Shortcut state rules live only in zng-app/zng-admin memory, and raw-API writes skip the mutation guard

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-05

## Goal

Every zng-* session follows the same Shortcut state rules without depending on which project's memories it loaded, and Shortcut writes made through a script go through the same guard as MCP-tool writes.

## Context

- On 2026-10-05, a zng-biller session (FE ticket triage) moved sc-54263 straight to Complete with Joe's approval. That breaks the "Testing is the ceiling" rule: Joe/Claude go no further than Testing, QA moves Testing to Ready for deploy, and `/zirtue-release-backfill` closes from there. The rule lives only in `C:\Users\tecno\.claude-personal\projects\c--Users-tecno-Desktop-Projects-zng-app\memory\feedback_never_move_ticket_straight_to_complete.md`, so zng-biller never loaded it. The same session also left a pushed ticket (sc-54701) in In Progress and then asked Joe where to move it. Joe's reply: "ofcourse it should be testing ... how is this even up for debate". Commit 66734ce added a "Post-push ticket move" step to `skills/commit/SKILL.md`. That covers the push-time move, but not the ceiling for manual moves made outside a push.
- zng-admin's `feedback_shortcut_ticket_transitions.md` adds "never transition tickets filed by other people", and `hooks/shortcut-mutation-guard.py` enforces it, but only on Shortcut MCP mutation tools. The 2026-10-05 session made 34 state/owner changes through a Python `urllib` script against `/api/v3/stories/{id}`. 31 of those stories had johannachen as requester, and the hook never saw any of them. Joe had explicitly asked for each change, so no harm was done, but the guard was bypassed silently.

## Approach

1. Put the Shortcut state ladder (Testing is the ceiling for Joe/Claude; never PUT Ready for deploy `500018659` or Complete `500018258` by hand; Won't do is fine) in one global place that `/ticket` reads before any state change. Point the zng-app/zng-admin memories at it instead of restating it.
2. Decide how script-based Shortcut writes get guarded. Options: route all writes through `/ticket` (and say so in `/ticket` and in CLAUDE.md), or add a Bash/PowerShell PreToolUse matcher for `api.app.shortcut.com` PUT/POST that applies the same requester and ceiling check. A matcher on the command string can't see writes from a Python file, so state that limit if this option is chosen.
3. Reconcile the two rules about other people's tickets: the zng-admin rule says "only requester == Joe", but Joe explicitly told the 2026-10-05 session to change johannachen-requested stories. The likely shape is "requester == Joe, unless Joe names the ticket in this session". Confirm it with Joe before encoding it.

## Acceptance

- A fresh zng-biller session, asked to "mark sc-X done", moves it to Testing at most and says why.
- A Shortcut state or owner write made outside the MCP tools is either blocked or checked by the same rule as the hook, or the docs say plainly that it isn't and route writes through `/ticket`.
- The zng-app/zng-admin memories no longer carry their own copy of the rule.

## Notes

- Phase 0 answers (Joe): (1) others' Shortcut tickets: requester must be Joe, unless Joe names that ticket in the current session. (2) add the PreToolUse hook on raw `api.app.shortcut.com` PUT/POST from Bash/PowerShell, on top of the shipped docs. (2026-10-07, /loop-todos Phase 0)
- loop-todos cycle 2, 2026-10-06: Approach step 1 and the docs branch of step 2 shipped: `skills/ticket/shortcut.md` "State ladder" section (ids checked against refs/shortcut-api.md:25-30) is the one global home, and its Ownership paragraph points at it. Left open: step 3 and the mechanical-guard half of step 2 (see Open questions), and the zng-app/zng-admin memory files still carry their own copy; once step 3 is answered, replace each with a one-line pointer to the State ladder section.
