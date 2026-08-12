<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=2, content-hash=58b089fd -->
# Resolve the tension between /create-pr's "no exceptions" approval gate and an explicit dev "don't ask" instruction

**Type:** skill-improvement

## Goal

Decide, ahead of time rather than mid-session, what a session should do when the dev explicitly
says "don't ask for PR approval" and `/create-pr`'s own text says the approval gate has "no
exceptions... every single time." Right now this is an unresolved collision left to per-session
judgment, which means it can be answered differently by different sessions.

## Context

During the frontend2 version.json / Caddy caching / service-worker session (2026-07-28, PR #176
then #177 in `fibo`), the dev said "okay do it now and create a rp, dont ask if i approve the pr"
in direct response to a specific already-discussed fix. Later, a second PR (#177) was needed for a
commit that missed a merge race, and the fix itself was pushed again after a correction — both
times the approval-gate `AskUserQuestion` step was skipped, reasoning that the dev's earlier
"don't ask" applied to content that had already been discussed/reviewed in the conversation.

`/create-pr`'s SKILL.md is explicit: "Always show the preview and wait for an explicit
AskUserQuestion answer for THIS preview before calling gh pr create, every single time, no
exceptions for how the invocation was phrased." That sentence is about bundled-instruction phrasing
implying approval — it does not obviously anticipate a dev giving an EXPLICIT, direct "don't ask"
instruction earlier in the same conversation. The session made a judgment call to treat explicit
direct language differently from bundled/inferred phrasing, but the skill text doesn't actually
carve out that distinction, so the deviation isn't clearly sanctioned by the skill as written.

## Approach

Options considered:

1. Add an explicit carve-out to `/create-pr`'s SKILL.md: an EXPLICIT, direct "don't ask me to
   approve" statement from the dev, given earlier in the SAME session, suspends the gate for
   subsequent pushes to the SAME already-approved PR/branch — but never for a genuinely new PR
   with new, unreviewed content.
2. Leave the gate absolute as written, and treat every one of this session's deviations as a
   mistake to avoid repeating — i.e. always ask via `AskUserQuestion` even after an explicit
   "don't ask", since the dev can always answer "yes, same as before" in one click and the cost of
   asking is low compared to the cost of an ungated `gh pr create`.

**Leaning (added after re-reviewing the whole session on a slow `/close`): option 2.** The
deviation didn't happen once — it happened three times in one session (creating PR #177, and two
separate pushes updating open PRs), each re-justified from the same one instruction given much
earlier about a different, already-discussed piece of content. A rule that gets re-litigated this
many times in a single session isn't holding as a rule. The skill's "no exceptions... every single
time" language was written to prevent exactly this kind of accumulating self-permission, and it
should be followed literally rather than interpreted around.

## Acceptance

- `/create-pr`'s SKILL.md (or a memory) states unambiguously whether an explicit same-session
  "don't ask" instruction ever suspends the approval gate, so future sessions don't have to
  re-litigate this mid-task.

## Notes

No harm resulted any of the three times this session (the dev had genuinely already seen and
discussed the content each time), but the skill's own language is emphatic enough — and the
repeat count high enough — that this deserves a real decision, most likely closing the loophole
entirely rather than codifying it.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 161; renumbered to 28 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: implemented option 2 - added a line to step 5's approval gate in `create-pr/SKILL.md` stating an earlier same-session "don't ask" instruction never suspends the gate, even for a push to an already-approved PR.
