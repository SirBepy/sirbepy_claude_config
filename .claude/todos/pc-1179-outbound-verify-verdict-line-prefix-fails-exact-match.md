<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1175 covers a different outbound-verify gap (shared-state DB writes); this one is about the verdict-line format itself -->
# outbound-verify: a numbered-list verdict line ("4. OUTBOUND-VERDICT: PASS") fails the hook's exact-line match, burning a wasted round

**Type:** skill-improvement
**Origin:** ai
**Summary:** The outbound-verify template makes the verdict line unmissable so a verifier never wraps it in numbering the hook cannot match.

## Why

On 2026-10-15 all three verifiers said PASS, but one wrote "4. OUTBOUND-VERDICT: PASS", the hook counted no verdict, and a fourth verifier had to be dispatched.

## Goal

`refs/outbound-verify.md`'s verifier template should make the verdict-line requirement unmissable enough that a sonnet verifier never wraps it in its own numbering/prose, since the hook treats anything other than the bare line as "no verdict" and silently discards that vote.

## Context

2026-10-15, zng-app session, verifying a Shortcut comment reply for sc-56117. Dispatched 3 identical verifiers per the template (ending instruction: "End your report with exactly one of these lines, alone on its own line: OUTBOUND-VERDICT: PASS / OUTBOUND-VERDICT: FAIL"). All 3 independently returned PASS, but when the `curl` POST ran, `hooks/outbound-verify-guard.py` blocked it with "2 PASS, 0 FAIL, 1 without a verdict". One verifier had closed its step-4 section with `4. OUTBOUND-VERDICT: PASS` (its own numbered-list style continued onto the verdict line), which reads as a real PASS to a human but apparently isn't matched as the literal line by the hook.

Had to dispatch a 4th verifier with a tightened prompt ("End your ENTIRE report with exactly one line, and that line must contain NOTHING else - no numbering, no prefix, no trailing text") before the hook accepted 3/3. That extra round cost a full verifier dispatch for a formatting miss, not a real factual disagreement.

## Approach

In `refs/outbound-verify.md`'s template (the numbered step 4), replace the current wording:
```
4. Verdict: PASS only if every factual claim is CONFIRMED and step 3 found nothing. Any WRONG,
   UNVERIFIABLE, or ship-review finding is a FAIL. End your report with exactly one of these
   lines, alone on its own line:
OUTBOUND-VERDICT: PASS
OUTBOUND-VERDICT: FAIL
```
with something closer to the tightened wording that worked on retry: explicitly ban numbering/prefixes/trailing text on that line, e.g. "End your ENTIRE report with exactly one line containing nothing but one of the two literal strings below - no leading number, no bullet, no trailing punctuation or commentary on that same line:". Consider also hardening `hooks/outbound-verify-guard.py` itself to tolerate a leading list-marker (regex strip of `^\s*\d+[.)]\s*` before matching) so a near-miss format doesn't cost a full round - belt-and-suspenders, since prompt wording alone won't catch every model's formatting quirk.

## Acceptance

- The template's step-4 wording explicitly forbids numbering/prefixes on the verdict line.
- Either the guard script tolerates a stripped leading list-marker, or a code comment in the hook explains why it intentionally doesn't (so the next person doesn't "fix" it into a false-accept).

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
