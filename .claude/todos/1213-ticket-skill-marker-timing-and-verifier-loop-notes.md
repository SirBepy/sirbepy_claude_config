<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1097 (done) fixed the MSYS body-file path read in outbound-verify-guard; this todo is about marker timing, a GET false positive and verify-loop guidance, a different surface -->
# /ticket skill: marker timing, Bash curl GET misfire, and verifier-loop hygiene

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/ticket/SKILL.md` (and `refs/outbound-verify.md`) say what actually works when filing a Shortcut story through the outbound guards, so the next session does not rediscover three gotchas and a very slow verify loop. Surfaced in a zng-biller session on 2026-10-21 (filing sc-56468).

## Context

1. **Marker timing.** SKILL.md Create step 6 and `refs/outbound-ground-check.md` say to write the marker "immediately before the write call". Observed 2026-10-21: a single PowerShell call that ran `write-outbound-marker.ps1` and then `Invoke-RestMethod ... POST /stories` was blocked by `hooks/shortcut-create-guard.py` ("no fresh ground-check marker"), because the guard runs PreToolUse, before the marker script executes. Writing the marker in its OWN prior tool call, then POSTing in the next call inside the 120 s window, worked (sc-56468 created). The docs do not say the marker call must be separate.
2. **Bash curl GET blocked.** `hooks/outbound-verify-guard.py` blocked a Bash call that was a read-only `curl -s "https://api.app.shortcut.com/api/v3/stories/$id" -H "Shortcut-Token: $TOKEN" | node -e ...` inside a `for` loop, with "Shortcut REST write blocked: its text is not visible in the call". There was no `-d` or `-X`, so this looks like a false positive on a GET; the trigger is UNVERIFIED (candidates: the shell variable in the URL, or the pipe into an interpreter). `Invoke-RestMethod` GET from PowerShell was not blocked. `refs/shortcut-api.md` documents the curl recipe as the read path.
3. **Verifier loop cost.** Filing three long FE tickets as one batch took 4 failed verify rounds (3 sonnet verifiers each, about 150k tokens per verifier). Every verifier confirmed the code facts and failed on ship-review nits or newly discovered real facts (for example a BE PR merged mid-session, making the text stale). What converged: one ticket per round, about 20 lines, speculative or design-opinion sentences deleted, absence claims dated ("no BE ticket found as of <date> (title search)"), pointing verifiers at local Figma PNG renders instead of the rate-limited Figma API. The verify doc has no guidance on this, and the 3 identical prompts (about 8 KB each) are pasted by hand every round.

## Approach

- `skills/ticket/SKILL.md` Create step 6 and `refs/outbound-ground-check.md` "Writing the marker": state that the marker script must be its own tool call before the POST call (not chained in the same command), with the 120 s window starting at the marker call.
- `refs/shortcut-api.md`: add a note that a Bash `curl` GET can be blocked by `outbound-verify-guard.py` and that `Invoke-RestMethod` from PowerShell is the working read path; investigate the guard's trigger and fix the false positive if it is one (read `hooks/outbound-verify-guard.py` against the exact command above).
- `refs/outbound-verify.md`: add a short "Keeping the loop short" section with the converged practice above. Consider a small script or documented template-fill step so the 3 identical prompts are not pasted by hand each round.
- Rejected: loosening the 3-subagent requirement; the guard working is the point.

## Acceptance

- A cold session following SKILL.md files a Shortcut story on the first try without the marker-timing block.
- `refs/shortcut-api.md` read recipe does not send a session into the false-positive block unwarned.
- `refs/outbound-verify.md` carries the loop guidance in 10 lines or less.

## Notes

- Joe said (2026-10-21) he wants iteration until tickets verify; no appetite to bypass the guard.
- This is global `~/.claude` work, filed here from a project session per CLAUDE.md; do not edit these files from the zng-biller session.
- 2026-10-22 data point (zng-biller, sc-56476): a one-line PowerShell chain `... -InFile C:\tmp\ticket-be-change-role.json; "story $($s.id)" ...` was blocked by `outbound-verify-guard.py` with "cannot read the body file C:\tmp\ticket-be-change-role.json;" - the guard took the trailing `;` as part of the path. Quoting the path and ending the line there (`-InFile 'C:\tmp\x.json'` then a newline) passed. Either fix the path tokenizer or document "quote the -InFile path".
- Second hit, same day (zng-biller, sc-56481 comment): `-InFile C:\tmp\sc56481-comment.json;` blocked the same way. Moving `-InFile <path>` to the front of the cmdlet's arguments and ending that statement with a newline instead of `;` passed.
- 2026-10-23 (loop-todos cycle 1): the doc parts landed - marker-as-own-tool-call in `skills/ticket/SKILL.md` steps 3 and 6 and `refs/outbound-ground-check.md`, a "keeping the verify loop short" section in `refs/outbound-verify.md`, and the curl-GET pointer plus the quote-the-`-InFile`-path workaround in `refs/shortcut-api.md`. ONLY the `-InFile` trailing-`;` tokenizer fix in `hooks/outbound-verify-guard.py` (plus a regression case in `hooks/test_outbound_verify_guard.py`) remains; it writes to `hooks/`, so it waits for an attended session.
- 2026-10-22: the round-cap rule in `refs/outbound-verify.md` ("Any FAIL, round 2: stop") conflicted with Joe's explicit "iterate until all 3 agree"; all 3 tickets converged in 2 rounds each once round 1 findings were applied in one edit, so the converged practice above held.
