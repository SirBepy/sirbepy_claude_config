<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=b6c17ff7 -->
# "Don't state unverified mechanism as fact" rule - third recurrence, same as the em-dash enforcement gap

**Type:** skill-improvement


## Goal

Decide whether `feedback_dont_state_unverified_mechanism_as_fact.md`'s rule needs something stronger than "remember it," now that it's failed a third time across three separate sessions.

## Context

Global auto-memory rule (`feedback_dont_state_unverified_mechanism_as_fact.md`, `type: feedback`): before asserting "X causes Y," check available ground truth; label untested guesses as guesses.

Recurrence log (all three now written into the memory file itself, see its "Repeat" entries):

1. Original incident: claimed a CLI mechanism was confirmed when Joe's own usage counter falsified it on the spot.
2. 2026-07-15 (/iterate-it hook design): claimed a `WorktreeRemove` hook event was "VERIFIED" from finding its name in a schema enum, not from observing its actual runtime behavior.
3. **2026-07-22 (this project, screenshot echo report):** Joe reported "you show my own screenshot back to me." Wrote a `feedback`-type memory framing it as a Claude behavioral choice, with zero code investigation, before Joe pushed back twice and forced an actual grep of `turn-collapse.ts`. Root cause was a rendering bug (the screenshot-row feature swept up Claude's own `Read` of Joe's just-uploaded attachment), unrelated to anything Claude was choosing to do.

This is structurally identical to `251-em-dash-rule-no-enforcement-mechanism.md` (done/, already closed as "self-discipline rule, strengthen wording") - a memory-documented rule that keeps failing despite being memory-documented, because there's no mechanical check between "about to assert a mechanism" and "message sent."

4. **2026-07-22 (this project, shutdown-blocker diagnosis), fourth recurrence:** diagnosing "the app blocks PC shutdown," asserted that `ipc/window.rs`'s `api.prevent_close()` was refusing a shutdown-driven close, and put that mechanism into an AskUserQuestion option Joe answered. Reading tao's `platform_impl/windows/event_loop.rs` before writing code falsified it (tao leaves `WM_QUERYENDSESSION` to `DefSubclassProc`; session-end never becomes a `CloseRequested`). Materially milder than 3: hedged as "suspect," self-caught, retracted unprompted, and no wrong code or memory was written. But the failing pattern is identical - a mechanism that depends on a *dependency's* behavior was named before that dependency's source was read.

5. **2026-08-10 (this project, /mega-todos design), fifth recurrence:** asserted in an AskUserQuestion card that "Workflow agents cannot invoke skills, so none of them can run `/commit`," and built the entire question on it, without ever opening `commit/SKILL.md`. Joe falsified it in one line ("what if we injected the skill into them?"). The skill is pure procedure and its step 8 is explicitly documented as index-safe for concurrent sessions. Caught by Joe, not self-caught; no wrong artifact shipped, but it would have produced a materially worse design. Distinct sub-class: the unverified thing was a **rule's stated rationale** treated as a binding constraint, not a guessed causal mechanism.

**The escalation trigger this file itself defined ("if a 4th recurrence happens, that's the signal to escalate to option 2") is now met.** Joe decides whether it fires - option 3's own terms arguably survive a self-caught recurrence, since nothing shipped wrong. Recurrence 5 weakens that defence: it was dev-caught, and the sub-class it revealed (rule rationales going stale) is not addressed by option 1's wording fix, which targets mechanism-guessing only.

## Approach

Same option space as 251, but note 251 closed with "won't fix, wording only" after 2 recurrences and did NOT actually stop this rule's recurrence (different rule, same shape of failure) - weigh whether the wording-only fix is proven insufficient for this class of rule in general, not just for em-dash.

1. Accept self-discipline-only, but add a sharper trigger clause to the memory: specifically call out "reporting something '**you**' (Claude) appear to do inside a Claude-hosted app" as a case requiring a code-grep before any explanation or memory write - not just "check ground truth" in the abstract.
2. Investigate whether a `Stop`-hook transcript scan (same mechanism 251 considered for em-dash) could pattern-match on assertive-mechanism phrasing ("the reason is...", "this happens because...", "X causes Y") in an outbound message immediately followed by a memory-write tool call, and warn/require a citation. Higher engineering cost, unproven feasibility - confirm hook visibility into outbound text first (251 already scoped this question, reuse its research if it exists).
3. Do nothing further beyond the memory update already made this session - if a 4th recurrence happens, that's the signal to escalate to option 2.

## Acceptance

- A decision recorded (in this file's Notes, or by closing as won't-fix) on which option was taken.
- If option 2 is pursued: a hook that fires on a deliberately-planted "confirmed"/"verified" claim in an outbound message and either blocks or logs it, verified against a real test case.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] [ARCH] The "do not state an unverified mechanism as fact" rule has now failed 5 times despite being documented in memory, and this todo's own escalation trigger says you decide from recurrence 4 onward. Options: (a) sharpen the wording once more, cheap, but the same shape of fix already proved insufficient for the em-dash rule; (b) spike a Stop hook that pattern-matches assertive-mechanism phrasing in outbound messages, higher cost and unproven feasibility since it first needs confirming a hook can even see response text; (c) do nothing until a 6th recurrence. Recommended: (a) now, holding (b) as a fallback spike only if it recurs again.

## Notes

- Relocated from the claude_usage_in_taskbar backlog (was todo #315) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
