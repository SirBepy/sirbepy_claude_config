<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=9e2e72ef -->
# shortcut-priorities: port bash pagination loop to python, widen git cross-check to all 4 ZNG repos, add step-0 SHORTCUT_SID liveness probe

**Type:** skill-improvement

## Goal

Three independent improvements to `skills/shortcut-priorities/SKILL.md`:
1. Rewrite the bash `while true` pagination loop (Step 1) in Python - port the logic
   carefully, this is fiddly cursor-based pagination with real edge cases already
   documented inline.
2. Widen the git cross-check (Step 5) from `zng-app` only to all four ZNG repos
   (`zng-app`, `zng-admin`, `zng-api`, `zng-biller`).
3. Add a Step-0 liveness probe for `SHORTCUT_SID` (the session cookie) with the exact
   DevTools refresh instructions surfaced immediately on a 401/403, instead of only
   discovering the cookie is dead mid-pagination.

## Context

`skills/shortcut-priorities/SKILL.md` (as of 2026-08-01):

**1. Pagination loop (Step 1, lines 57-84)** is currently raw bash:
```bash
COOKIE='sid=...'
ORG='...'
WS='...'
before="<recent-known-good-ISO-timestamp>"
CUTOFF="<today - lookback_days, ISO>"
i=0
while true; do
  i=$((i+1))
  resp=$(curl -s -X POST 'https://app.shortcut.com/backend/api/private/permission/activity' \
    -H 'accept: */*' -H 'content-type: application/json; charset=UTF-8' \
    -H "tenant-organization2: $ORG" -H "tenant-workspace2: $WS" \
    -H 'x-requested-with: XMLHttpRequest' -H "cookie: $COOKIE" \
    -d "{\"before\":\"$before\"}")
  echo "$resp" > "C:/tmp/shortcut_notif/page_$i.json"
  start=$(echo "$resp" | grep -o '"start":"[^"]*"' | head -1 | cut -d'"' -f4)
  [ -z "$start" ] && break        # error/empty â€” stop, surface the raw response to Joe
  [[ "$start" < "$CUTOFF" ]] && break
  before="$start"
  [ $i -gt 60 ] && break          # safety stop
done
```
The skill already uses Python elsewhere in the same flow (Step 2 explicitly: "python, not
jq - not installed"), so a bash `curl`+`grep -o`+string-comparison loop for JSON
pagination is an inconsistency and a fragility risk (the `grep -o '"start":"[^"]*"'` JSON
field extraction is brittle - breaks if the field ever appears elsewhere in the payload,
or if whitespace/escaping changes). Port it to Python using `requests` or `urllib`,
preserving every documented edge case:
- Backwards-in-time `before` cursor semantics (line 59).
- The "before must not be in the future" 400 error and why (line 59, don't seed with a
  computed "now").
- The `i > 60` safety stop (line 80).
- Writing each page to `C:/tmp/shortcut_notif/page_$i.json` for debugging (line 61,
  scratch dir per line 53 - "ephemeral, fine to overwrite/clean each run").
- The "if the very first call errors, don't retry blindly - read the error" guidance
  (lines 84).

**2. Git cross-check (Step 5, lines 107-114)** currently only checks `zng-app`:
```bash
git -C C:/Users/tecno/Desktop/Projects/zng-app log --oneline -10 --grep="<ticket-id>"
```
`~/.claude/refs/shortcut-api.md` lines 34-37 lists all four ZNG repos (`zng-app`,
`zng-admin`, `zng-api`, `zng-biller`) as the fixed identity/constants reference this
skill already points to (SKILL.md line 51). A QA-rejected fix could land in any of the
four repos, not just `zng-app` - the current check would miss a same-day fix commit in
`zng-admin` or `zng-biller` and wrongly report the issue as still-open.

**3. SHORTCUT_SID liveness probe:** currently the skill only discovers a dead cookie
reactively, mid-Step-1, when a call returns 403/401 (documented at lines 33-35: "Only
`SHORTCUT_SID` expires. If the first call returns `403` / `401` / `"tag":
"...unauthorized"`, THEN ask Joe for a fresh one: open Shortcut -> DevTools -> Network ->
reload the Stories view -> right-click the `activity` request -> Copy as cURL -> paste.
Extract the `sid=` value, overwrite `SHORTCUT_SID` in `~/.claude/.env`, retry."). There's
no explicit Step 0 that probes liveness BEFORE committing to the full pagination run -
the dev only gets the DevTools instructions after burning at least one failed page fetch
attempt (or discovers it mid-loop after several successful pages if the cookie expires
between calls).

## Approach

1. Read `skills/shortcut-priorities/SKILL.md` in full before editing.
2. **Python pagination:** rewrite Step 1's bash block as a Python script/inline block,
   preserving every behavior listed above exactly. Test the ported loop's cursor logic
   carefully against the documented edge cases (future-timestamp 400, empty `start`
   meaning stop, the 60-iteration safety cap) - a subtle off-by-one or wrong break
   condition here silently truncates the activity feed, which is hard to notice after the
   fact.
3. **Git cross-check widening:** change Step 5's single `git -C ... zng-app log` command
   into a loop (or four explicit commands) across all four ZNG repos from
   `~/.claude/refs/shortcut-api.md`. Update the surrounding prose ("check git before
   flagging") to say "across all four ZNG repos" instead of implying just zng-app.
4. **Step 0 liveness probe:** add a new Step 0 before the current Step 1 ("Paginate the
   private activity feed") that makes ONE cheap probe call against the private activity
   endpoint (e.g. a single-page request with the cached `SHORTCUT_SID`) before committing
   to the full pagination loop. On 401/403, immediately surface the exact DevTools
   instructions already documented at lines 34 (Shortcut -> DevTools -> Network -> reload
   Stories view -> right-click `activity` request -> Copy as cURL -> extract `sid=` ->
   overwrite `SHORTCUT_SID` in `~/.claude/.env`) rather than waiting for Step 1's loop to
   discover it. Renumber subsequent steps (current Steps 1-6 become 2-7).

## Acceptance

- Step 1 (now Step 2 after renumbering) is Python, not bash, and reproduces every
  documented edge case from the original bash version (verify by re-reading the ported
  code against each bullet listed in Context above).
- Step 5 (renumbered) checks commits across all four ZNG repos, not just zng-app.
- A new Step 0 exists that probes `SHORTCUT_SID` liveness before the main pagination run
  and prints the exact DevTools refresh instructions on failure.
- Re-read the full file after editing to confirm step numbers referenced elsewhere in the
  file (e.g. "Step 4" dispatch-volume-gate cross-references) still point at the correct
  renumbered step.

## Notes

- completed, commit c3b880b
