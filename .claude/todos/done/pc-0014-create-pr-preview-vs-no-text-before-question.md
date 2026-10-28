<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=710a56d4 -->
# Resolve /create-pr preview conflicting with the no-text-before-question rule

**Type:** skill-improvement
**Origin:** ai

## Goal

Reconcile `/create-pr`'s "render the preview inline, then ask for approval" flow with the standing memory rule that says text emitted before an `AskUserQuestion` call can be invisible to Joe.

## Context

Skill file: `C:\Users\tecno\.claude-personal\skills\create-pr\SKILL.md`, steps 7 and 8.

Memory: `feedback-no-text-before-question-tool` ("pre-tool-call text can be invisible to Joe; deliverables go in the turn's final message, tools first").

Step 7 tells Claude to render the PR body inline in chat. Step 8 tells Claude to then call `AskUserQuestion` to get approval. Anything printed in step 7, plus any caveat added just before the question (on 2026-07-10 this was a note that no lint/typecheck had run, because the diff was a single binary PNG), sits in the pre-tool-call position the memory warns about. Joe may never see it, yet step 8 asks him to approve *that specific body*.

This is a genuine skill-vs-memory conflict, not an execution slip. It recurs on every `/create-pr` invocation.

## Approach

Pick one and encode it in the skill file:

- **Option A (preferred):** move the human-facing preview into the `AskUserQuestion` call itself, using the per-option `preview` field so the body renders inside the question UI where Joe definitely sees it. Question text carries the caveats.
- **Option B:** split into two turns. Turn 1 ends with the rendered preview as the final message and no tool call. Turn 2 (after Joe responds) opens with the `AskUserQuestion`. Costs a round trip.
- **Option C:** narrow the memory to exclude skill-mandated previews, if Joe confirms the `cc-pr-*` marker card already surfaces the body reliably in the host app.

Check first whether the `<cc-pr-title:...>` / `<cc-pr-body:...>` markers already render a visible card in Claude Conductor. If they do, Option C may be correct and the whole conflict is theoretical. Ask Joe rather than assuming.

**Evidence 2026-07-13 (PR #120 session):** the conflict is real, not theoretical.
Claude emitted the preview inline AND the `cc-pr-*` markers, then called
`AskUserQuestion`; Joe answered "i dont see the body thats meant to have shown
me the PR... but fuckit... create it". So neither the pre-tool-call text nor
the marker card reached him. Option C is ruled out; Option A (preview inside
the AskUserQuestion option's `preview` field) looks like the fix.

## Acceptance

- `create-pr/SKILL.md` steps 7-8 no longer instruct Claude to place approval-critical text in the pre-tool-call position, OR the memory `feedback-no-text-before-question-tool` carries an explicit carve-out naming this skill.
- A subsequent `/create-pr` run shows Joe the body and any caveats in a position he reliably sees.

**Correction (2026-08-03):** the "Option C is ruled out" conclusion above is now contradicted by
newer, confirmed evidence â€” treat it as superseded, not current. On 2026-08-03 Joe confirmed
unprompted, in a turn with NO question tool in it: "btw, now the preview is showing up lol". The
`<cc-pr-title/body/commits>` marker card DOES render reliably now (memory
`feedback-pr-preview-cards-dont-render.md` was corrected accordingly the same day). The real,
still-live failure mode that day was different: emitting the PR body in the SAME turn as an
`AskUserQuestion` approval call caused Joe to see nothing â€” sent again in its own turn with no
question tool, it rendered fine. So Option C (the marker card is sufficient) looks correct after
all, PROVIDED the body is never emitted in the same turn as the approval question â€” that ordering
constraint is the actual gap this todo should close, not a card-rendering failure.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 80; renumbered to 14 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise holds. Its Acceptance cites "steps 7-8" of `create-pr/SKILL.md`;
  the real anchors are now step 4 (renders the preview and emits the `<cc-pr-*>` markers, around line
  141) and step 5 (the approval `AskUserQuestion`, around line 174). The file greps clean for "same
  turn" / "separate turn", so the ordering constraint is genuinely unencoded. Also note the todo's own
  2026-08-03 correction already superseded its earlier "Option C ruled out" conclusion, so only the
  ordering fix remains open.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: between step 4, which renders the preview and emits the markers, and step 5, which
  asks for approval, add an explicit instruction that step 4 must be the FINAL action of its turn -
  no tool call after it - and that step 5's `AskUserQuestion` opens a new turn. The file greps clean
  for "same turn" and "separate turn", so this constraint is genuinely unencoded. This was produced
  by a strict second-pass re-triage that specifically asked whether a defensible answer exists
  without the dev; it concluded yes. Not executed only because the session ended.
- completed, commit 00737e5
