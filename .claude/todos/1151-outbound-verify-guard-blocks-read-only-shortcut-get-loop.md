<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1097 is msys body-file path resolution for real writes, 1088 is the transcript-tally split; this is a false positive on a read-only GET -->
# outbound-verify-guard blocks a read-only Shortcut GET inside a for-loop

**Type:** skill-improvement
**Origin:** ai

## Goal

A read-only `curl` GET against `api.app.shortcut.com/api/v3/stories/<id>` should never be blocked by `hooks/outbound-verify-guard.py`, even when the story id comes from a shell loop variable.

## Context

- 2026-10-08, zng-admin session (todo 81 / sc-56270): this Bash command was denied with `[outbound-verify-guard] Shortcut REST write blocked: its text is not visible in the call (a variable, --fill, or an editor)`:
  `TOKEN=$(sed ... ~/.claude/.env | grep -a '^SHORTCUT_API_TOKEN=' | cut -d= -f2 | tr -d '\r"'); for s in 54369 54384; do curl -s -H "Shortcut-Token: $TOKEN" https://api.app.shortcut.com/api/v3/stories/$s | PYTHONIOENCODING=utf-8 python -c "import sys,json; d=json.load(sys.stdin); print(d['id'], ...); print(d['description'][:500])"; done`
  It is a pure GET (no `-X`, no `-d`). The same command with a literal URL (`.../stories/54369`, no loop) went through.
- `detect_rest` (`hooks/outbound-verify-guard.py:325-349`) only gates when `is_http_write` (`:301-304`) is true: `WRITE_VERB_RE` matches, or `DATA_FLAG_RE` matches without `GET_FLAG_RE`. UNVERIFIED which of the two fired on this command; would check by running the guard's own detector on the exact string above. Plausible suspects: `DATA_FLAG_RE` matching something inside the `python -c "..."` payload or the `sed`/`tr` args, or `$s` making `SHORTCUT_URL_RE`'s `rest` group empty so `requires` goes true.
- Workaround used: one literal URL per curl call. Cost was one wasted call, but the error text ("write blocked") is misleading for a read.
- **2026-10-13, zng-app session (shortcut-done-audit, Ready-for-deploy scan): reproduced again, and this confirms the second suspect above, not the first.** Command: a `for id in 54304 54866 ...; do curl -s "https://api.app.shortcut.com/api/v3/stories/$id" -H "Shortcut-Token: $TOKEN" -o /c/tmp/story_$id.json; done` loop, no `-X`, no `-d` anywhere. Denied with the same "write blocked... its text is not visible" message. `SHORTCUT_URL_RE` is `r"api\.app\.shortcut\.com/api/v3/stories(?P<rest>(?:/[\w-]+)*)"` (`hooks/outbound-verify-guard.py:75`) - the `rest` group's char class `[\w-]` does not include `$`, so against the literal, unexpanded command STRING `.../stories/$id`, the regex engine cannot consume `/$id` as a path segment and `rest` captures `""`. `detect_rest` then sets `requires = (rest == "" or re.fullmatch(r"/\d+/comments", rest))` (`:336`) - with `rest == ""` this is True, so a plain GET to `/stories/$id` is treated exactly like a bare `POST /stories` (create-with-prose) call, which is why it demands verified prose that was never going to exist. Confirmed by testing side-by-side in the same session: the identical curl with a **literal numeric id** substituted in for each loop iteration (unrolling the loop by hand into one curl call per id) passed clean every time; only the `$id`-variable form tripped the guard. So: hypothesis 2 from the original Context ("`$s` making `SHORTCUT_URL_RE`'s `rest` group empty so `requires` goes true") is the confirmed, reproducible cause - not hypothesis 1 (`DATA_FLAG_RE` matching something in a `python -c`/`sed`/`tr` payload), since this session's repro had neither. This also means the bug isn't specific to a loop per se - any curl whose URL embeds an unexpanded shell variable (`$x`, `${x}`) anywhere after `/stories` trips it, loop or not, because the hook reads the command STRING before the shell expands it. Fix direction: in `detect_rest`/`SHORTCUT_URL_RE`, treat a `rest` that fails to fully match specifically because of a `$`/`{`/`}` (an unexpanded variable reference) as "unknown, not empty" rather than coercing it to the `rest == ""` create-shape - distinct from the real bare-`/stories` case, which has no `$` in it at all.

## Approach

1. Reproduce: feed the exact command above to the guard (its self-test harness, if present) and confirm which predicate returns true.
2. Narrow that predicate so it only considers curl's own argv (the tokens of the `curl` invocation), not the whole compound command string.
3. Add a regression case to the guard's self-test for this GET-in-a-loop shape, plus a positive case that a real `-X POST -d @file` in a loop is still gated.

## Acceptance

- The command above passes the guard.
- A Shortcut `POST /stories` or `PUT /stories/<id>` with prose, in or out of a loop, is still blocked without 3 verifier PASSes.
- `python ci/run_all.py` green.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.

## Notes
- 2026-10-14 recurrence (zng-app session ed37142a): a plain Shortcut GET for 2 stories was blocked as a REST write because the token-extraction pipe used `tr -d '
'`, which DATA_FLAG_RE (`(?:^|\s)-d\b`) matches. Adding `-X GET` did not help. Workaround that passed: extract the token with a python one-liner, no `tr -d` in the command.
- 2026-10-22 recurrence (zng-biller, PowerShell): one call with a `foreach` POSTing `story-links` (body from `@{subject_id=...; verb=$l.verb} | ConvertTo-Json`, no prose) followed by a `foreach ($id in 56481, 56482) { Invoke-RestMethod -Uri "https://api.app.shortcut.com/api/v3/stories/$id" }` GET loop was blocked with "its text is not visible in the call". An earlier call with the same link loop but a literal GET URL passed, so the variable-URL GET is the likely trigger (UNVERIFIED). Splitting into literal-JSON link POSTs and a separate GET call passed.

## Notes

- 2026-10-23, zng-app session (sc-56414): both halves are needed, not just the `$id` one. `is_http_write` only went true because `DATA_FLAG_RE` (`(?:^|\s)-d\b`) matches `cut -d=` in the canonical token recipe from `refs/shortcut-api.md` ("Token extraction"). So every GET built from that recipe counts as an HTTP write, and the `$id` empty-`rest` bug then makes it demand prose. Proof from the same session: the identical `for id in 56414 56411` loop with `$id` in the URL passed once `-G` was added (GET_FLAG_RE cancels the data-flag match). Workaround: add `-G` to read-only curls, or use `cut -f2 -d=`. Fix direction: match data flags only inside the curl invocation's own argv, as Approach step 2 already says.
