<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=8, reconfirm-count=1, content-hash=580e9fe3 -->
# /cleanup-memory's confirm gate is the wrong shape: auto-apply, offer a second opinion

**Type:** skill-improvement
**Origin:** dev

## Goal

Replace `/cleanup-memory`'s per-item plain-text confirm list with an auto-apply default, fronted by
a single structured question. Joe's words, 2026-08-13: "i hate this way of using cleanup memory ...
i will always want you to auto archive/reindex/fix/whatever".

## Context

Filed from a zng-app session that ran `/cleanup-memory` over a 182-file corpus. The skill's Step 5
produced a long report ending in the mandated plain-text prompt ("Reply with names to confirm ...
`fix links only` ... or `keep all`"). Joe did not want to hand-pick names out of a wall of text, and
does not want to be asked per-item at all.

**The mechanism causing this is a specific rule in the skill.** `cleanup-memory/SKILL.md` Step 5
says: "Deliver as the turn's FINAL message, no tool call after it - a same-turn `AskUserQuestion`
would swallow the preceding text in this harness." That constraint is what forces the typed-reply
list. It is worth re-testing rather than inheriting: in the Claude Conductor app the
`mcp__cc_conductor__ask_user_question` tool renders as a separate floating card and does NOT swallow
preceding chat text, and that app also supports free-text entry alongside the options. If that holds,
the whole reason for the plain-text gate disappears.

What Joe asked for instead, concretely:

1. **Default to auto-applying** every suggestion the audit produces (archive, re-index, fix links,
   fold dedupe losers) without enumerating them for approval.
2. **One question up front, not a gate at the end**, offering roughly: `apply all suggestions` /
   `get a second opinion` / free-text for anything else.
3. **The second-opinion path**: dispatch 2 verification subagents; if they agree with the audit on
   everything, proceed with the apply. Joe used this path on 2026-08-13, so it is the proven shape,
   not a guess. One adversarial refuter plus one independent reviewer worked well: the refuter was
   pointed at the destructive proposals (archives, drops) and told to default to "do not act" when
   uncertain, the reviewer at the additive and structural claims.

The existing protections should survive this change, since they are what makes auto-apply safe:
archive to `<memory-dir>/archive/` instead of deleting, and honour explicit exclusions (Joe's were
"nothing lenderless-related, nothing too recent" - the run treated "too recent" as any file modified
within the current month).

## Interaction with todo 320 - do not let these two silently disagree

`320` (memory-index size warning) argues the index is near the 200-line silent-truncation limit,
rejects merging memory files to shrink it, and floats having `/cleanup-memory` prune the index.

This run pushes the OTHER way: it found 23 of 182 files missing from `MEMORY.md` entirely (so they
never load into any session) and proposed re-indexing 18 of them, taking the index from 160 to 178
and leaving 22 lines of headroom. Both findings are real - the corpus is large AND has invisible
entries - but whoever implements either todo has to reconcile them. The likely resolution is `320`'s
own option 3 (group index lines under `##` headings, which costs a few lines but makes 178 scannable)
plus accepting that the ceiling is a harness limit to be surfaced, not silently satisfied by dropping
knowledge.

## Also fix: Step 5 hides the fold-first requirement

Step 6 correctly says that before archiving a dedupe loser you must fold any detail the keeper lacks
into the keeper first. **Step 5's confirm list has no slot for that**, so the 2026-08-13 run listed
`feedback_no_comments_default` as a plain archive and only caught the omission when a verification
subagent pointed out the file held a `DELETE /users/self/archive` example present nowhere else. The
skill's rule was right and the report format lost it.

Fix: every dedupe-loser entry in the confirm list (and in the auto-apply summary) must state either
"nothing unique to fold" or the exact detail being folded and where it lands. Under auto-apply this
matters more, not less, since nobody is reading a list before the write happens.

## Approach

1. Re-test the swallowing claim in Step 5 before anything else. If `ask_user_question` (or the
   built-in AUQ) can coexist with report text in the current harness, delete that constraint and note
   what was tested.
2. Restructure the skill: run Steps 1-4 (read-only audit) as now, then ask the single question, then
   apply. Keep the audit read-only and keep `archive/` as the destination.
3. Add the second-opinion mode as a real documented phase, with the two-lens split above and the rule
   that any REFUTED destructive item drops out of the apply set while the rest proceeds.
4. Keep a short post-apply summary of what moved, so auto-apply is still auditable after the fact.

## Acceptance

- `/cleanup-memory` on a dirty corpus asks exactly one question, then applies without further prompting.
- Choosing the second-opinion option dispatches 2 verifiers and proceeds only on agreement, with any
  refuted item excluded and named.
- Nothing is ever hard-deleted; `archive/` still receives everything.
- Joe never has to type a list of memory names.
