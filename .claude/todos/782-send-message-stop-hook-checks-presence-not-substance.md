<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=5, reconfirm-count=1, content-hash=af06eb8b -->
<!-- duplicate-checked -->
# send_message Stop hook checks that the tool was called, not that it carries the actual content

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "call send_message before ending your turn" Stop hook (referenced from global
`CLAUDE.md`'s Communication section, "Call send_message at least once before ending every turn")
catch a `send_message` call that is present but content-free - a decoy that just points at
invisible assistant prose instead of containing the substance.

## Context

Observed live 2026-08-25 in a zng-app session (`C:\Users\tecno\Desktop\Projects\zng-app`). Joe
asked to explain all `<script>` tags in `web/index.html` (author/ticket/validity per tag). Claude
wrote a full multi-section breakdown as regular assistant text, then called `send_message` with
only: "Answered inline: went through all 7 script tags... Full breakdown is in the chat reply."

The Stop hook fired (it always does) and was satisfied - `send_message` had been called. But per
`CLAUDE.md`: "Your assistant text and tool-call narration are never rendered in the chat view at
all - Joe cannot see any of it." So "the chat reply" Claude pointed to does not exist from Joe's
side; he got a message that referenced content he never received. Joe's next turn was literally
"i dont see it..", and Claude had to reconstruct and resend the entire breakdown through
`send_message` properly.

This is distinct from the general "draft content goes in send_message, not prose" rule (already
documented as project memory `feedback_draft_content_in_send_message_not_prose.md` in the zng-app
project, and distinct from `410-relay-only-turn-should-be-allowed-to-end-silent.md`, which is
about whether a turn should be allowed to send NO message at all for pure relays - the opposite
direction). That memory documents the rule; this todo is about the fact that an existing
enforcement mechanism (the Stop hook) technically ran and still didn't catch the violation,
because it only checks tool-call presence, not whether the call's `text` actually contains the
substantive answer rather than a pointer to nothing.

## Approach

Options to consider (pick one, or a combination):

1. **Heuristic content check in the hook.** Flag (warn, don't hard-block) when `send_message.text`
   is short (e.g. under some char threshold) AND the same turn's assistant text is long/contains
   multiple headers or list items - a shape strongly correlated with "wrote the real answer in
   prose, sent a stub pointer instead." False positives are acceptable for a warn-level nudge.
2. **Phrase-match check.** Flag `send_message` calls whose text contains phrases like "in the
   chat reply", "see above", "as I mentioned", "in my response" - these phrases only make sense if
   assistant prose were visible, which it never is in this harness. Cheap and high-precision
   (unlike option 1) but narrower coverage (misses a decoy phrased differently).
3. **Reframe the CLAUDE.md rule itself** to explicitly ban self-referential phrases like "see
   above"/"in the chat reply" in `send_message` content, and let the existing em-dash-style
   character-ban hook pattern (precedent: `done/59-enforce-no-em-dash-rule-with-hook.md`,
   `done/213-em-dash-enforcement-hook.md`) be extended to also scan `send_message` tool-call args
   for these phrases specifically.

Option 2 is the cheapest reliable first pass; option 1 catches more but needs threshold-tuning
to avoid nagging on legitimately short follow-up messages ("Waiting on your answer" is short and
fine, and does not reference nonexistent prior content).

## Acceptance

- A `send_message` call whose text contains a self-referential pointer phrase ("in the chat
  reply", "as shown above", "see above") without accompanying substantive content triggers a
  Stop-hook warning (or block) telling Claude to inline the actual content instead.
- A normal short send_message ("Waiting on your answer to that quick audience check.") does NOT
  trigger the check - it doesn't claim content exists anywhere else, it just states current status.

## Notes

Related project memory (zng-app only, not this repo): `feedback_draft_content_in_send_message_not_prose.md` - documents the rule but not the enforcement gap; this todo is the enforcement half.
