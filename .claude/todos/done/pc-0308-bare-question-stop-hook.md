<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Stop-hook to catch bare open-ended questions that bypass AskUserQuestion

**Type:** skill-improvement
**Origin:** ai

## Goal

Enforce the global CLAUDE.md rule "Every question: use the AskUserQuestion tool with 2-4 options. Never a bare open-ended question" with a `Stop` hook, the same way `307-em-dash-stop-hook.md` proposes enforcing the em-dash ban.

## Context

Violated three times in a single short session (2026-07-10, biller-portal status thread). Claude ended turns with plain-text "Want me to check?", "want me to trace the endpoint in zng-api?", and "Want me to check the admin side?" instead of routing them through AskUserQuestion.

The rule is stated plainly in `~/.claude-personal/CLAUDE.md` under Communication and was still missed, which makes it an enforcement gap rather than a comprehension one. Reading the rule harder is not a fix. Note the interaction with `user_mouse_clicks_disabled.md`: AUQ misclicks are a real annoyance, which may be *why* the bare-question habit reasserts itself, so the fix should not make AUQ more painful to answer.

## Approach

- Mirror the mechanism `307-em-dash-stop-hook.md` lands on. Do that one first; this is the second consumer of the same machinery.
- Hook on `Stop`, inspect the final assistant message.
- Heuristic: message ends with a `?` on the last non-marker line, AND no `AskUserQuestion` tool call occurred in that turn. Interrogatives embedded mid-paragraph are fine (rhetorical framing, restating the user's question), so anchor on the trailing line.
- Exempt turns where the trailing question is inside a blockquote (those are draft messages *for Joe to send*, not Claude asking Joe, and this session produced several).
- On match: block, and tell Claude to re-emit via AskUserQuestion.

## Acceptance

- A turn ending in `Want me to check the admin side?` with no AUQ call is blocked.
- A turn ending in a blockquoted draft Slack reply that happens to end in `?` passes.
- A turn ending in a real AskUserQuestion call passes.
- Rule text in `~/.claude-personal/CLAUDE.md` gains a pointer to the hook so the two stay in sync.

## Notes

Relocated from 38 in zng-biller via /cleanup-todos 2026-08-13: hook targets global ~/.claude/settings.json, not zng-biller.
- Done 2026-08-13 as a MEASURED NO. Built as hooks/EXPERIMENTAL-bare-question-detector.py, deliberately NOT wired into settings.json. Measured against a real corpus: ~4025 turn-final assistant messages pulled from this machine's own transcripts across ~15 projects, each reconstructed with whether AskUserQuestion fired that turn. The heuristic (trailing line ends in ?, not a blockquote, no AUQ since the last user turn) flagged 65 turns, about 1.6 percent, and all 65 were read by hand: clear false positives are only 1-2 percent. The killer is the other direction. Of ~93 turns containing a ? that were NOT flagged, hand review of 80 found roughly 20-25 percent are genuine violations, because Claude usually closes a decision with a bulleted list and then a non-question status line rather than literally ending on a question mark. A hard-block Stop hook that silently misses a fifth of real cases gives false confidence, which is the same failure shape that killed the phrase-based spike earlier the same day. Two corpus-derived KNOWN MISS cases are baked into hooks/test_bare_question_detector.py so the gap cannot be forgotten; 11 tests pass. Recorded next steps if ever revisited: the exemption list does not cover open greeting turns where AskUserQuestion's fixed 2-4 option shape genuinely does not fit, and a smarter regex is the wrong direction. The promising alternative is inverting it, requiring an explicit no-question-needed marker on turns that legitimately end without one, rather than trying to detect the violation.
