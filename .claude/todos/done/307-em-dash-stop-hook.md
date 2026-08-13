<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Add a Stop hook that catches em dashes in Claude's output

**Type:** skill-improvement
**Origin:** ai

## Goal

Global CLAUDE.md forbids the em dash character outright. Claude breaks the rule anyway, repeatedly, in sessions where the rule is loaded and visible. Add mechanical enforcement instead of relying on the instruction.

## Context

Global rule, `~/.claude-personal/CLAUDE.md`, Communication section:

> Never use the em dash character anywhere, ever. Use a comma, colon, or hyphen instead.

On 2026-07-09, in a session where that rule was in context the whole time, Claude emitted em dashes across at least five separate responses (a `/rate-it` verdict, a Shortcut board summary, a four-ticket audit report). Claude caught the violation itself, mid-session, while writing files, and still shipped em dashes in the surrounding prose. That is the tell: this is not an attention problem that a stronger instruction fixes.

The rule is unusual because it is purely lexical. Unlike most style rules, it can be checked exactly: it is the single codepoint U+2014. That makes it one of the very few CLAUDE.md rules that a hook can enforce with zero false positives.

Related: the same session had the `caveman` SessionStart hook active, and Claude drifted out of caveman prose within two messages. That drift is NOT mechanically checkable and should not be bundled into this todo. Only the em dash is.

## Approach

1. Read the `update-config` skill first. It owns `settings.json` hook wiring and knows the current schema.
2. Add a `Stop` hook to `~/.claude/settings.json`. On stop, read the last assistant message from the session transcript and grep for U+2014 (`â€”`, literal `â€”`).
3. On a hit, block with a message naming the offending substring, so Claude sees its own violation and rewrites. `Stop` hooks can return a block decision with a reason, which re-invokes the model - that is the enforcement mechanism.
4. Guard the obvious false positive: a diff, file content, or quoted user text may legitimately contain an em dash (e.g. reading a file that has one). Scope the check to prose Claude authored, not tool results. If that distinction is not cleanly available in the transcript shape, prefer a warning over a hard block, and reassess after a week.
5. Consider extending to the sibling characters if they turn out to be a problem too: en dash U+2013, horizontal bar U+2015. Do not add them speculatively. Em dash is the one Joe called out.

Rejected alternative: restating the rule more forcefully in CLAUDE.md, or adding it to a per-project CLAUDE.md. The rule is already unambiguous and already global. Repeating it is the "be more careful" non-fix.

Rejected alternative: a `PostToolUse` hook. The violation is in assistant prose, not tool input, so `PostToolUse` never sees it.

## Acceptance

- A response containing `â€”` in Claude-authored prose triggers the hook and gets rewritten before reaching Joe.
- A response containing `â€”` only inside a tool result, a quoted file, or Joe's own words does not trigger it.
- The hook adds no visible latency to normal turns.
- Verify by deliberately writing an em dash in a test session and confirming the block fires, then confirming a `Read` of a file containing one does not.

## Notes

Relocated from 36 in zng-biller via /cleanup-todos 2026-08-13: hook targets global ~/.claude/settings.json, not zng-biller.
- Done 2026-08-13, WIRED. hooks/em-dash-guard.py reads the Stop payload via _hooklib.read_payload(), honours stop_hook_active as a loop guard, does a literal chr(0x2014) match on last_assistant_message, and returns decision=block with a snippet around the offending character. Fails open on import error. No extra scoping was needed because last_assistant_message only ever carries Claude's own composed text: tool_use and tool_result are separate content blocks. Appended to settings.json's Stop array, nothing replaced; verified the file still parses as JSON with no UTF-8 BOM. 11 test cases in hooks/test_em_dash_guard.py, unit plus real stdin/stdout subprocess integration, all passing. This is the case the earlier phrase-detector spike was NOT: an exact codepoint has essentially zero false-positive surface, which is why the rejection of that spike did not transfer.
