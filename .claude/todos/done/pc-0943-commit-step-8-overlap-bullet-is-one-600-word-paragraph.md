<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=6, reconfirm-count=1, content-hash=1064bc30 -->
<!-- duplicate-checked: 368/474/498/500/941 are all in done/ and all changed this bullet's BEHAVIOUR. This one changes only its SHAPE - no rule gains, loses, or shifts meaning. Filed as the structural debt those five each added to. -->
# /commit step 8's unpushed-overlap bullet is a single ~600-word paragraph carrying five branches

**Type:** task
**Origin:** ai

## Goal

Make step 8's unpushed-overlap decision readable at a glance, without changing a single rule it
encodes. It is the bullet a session must parse correctly under time pressure on every commit, and it
is currently the least parseable prose in the file.

## Context

Offered to Joe on 2026-09-05 immediately after commit `bf61555` and not executed - he was not asked
to decide, so this is the parked half of that offer.

`skills/commit/SKILL.md` step 8, the `Unpushed-overlap check` bullet, is now one unbroken paragraph
of roughly 600 words. It carries, in reading order: the script invocation and its `--own` flag, a
runtime/timeout caveat, an explanation of what the script owns, three exit codes, and then **five
distinct outcome branches** for exit 1 alone:

1. `commit-style.md` forbids cross-ticket sharing -> never ask (todo 849)
2. personal repo (`SirBepy` origin or no remote) -> never ask (todo 941, added the same day)
3. client/employer repo, interactive -> queue, then ask once at end-of-queue
4. session fold-policy already recorded and covers every queued item -> reuse it, do not re-ask (todo 862)
5. unattended run -> never ask, record in the run summary

Each of those arrived as a separate fix (849, 862, 941, plus 368/474/498/500 reshaping the check
itself), and each was appended into the same sentence-stream rather than given structure. The
content is correct; the shape is the debt.

`bf61555` made it worse by one branch and said so at the time.

## Approach

1. Keep the bullet's opening (script invocation, `--own`, timeout caveat, exit 0 / exit 2) as prose.
2. Turn the exit-1 outcomes into a nested list under a single `Exit 1` lead-in, one sub-bullet per
   branch above, in the order they must be evaluated - the commit-style ruling-out check is first
   today and that ordering is load-bearing, so preserve it explicitly rather than by paragraph
   position.
3. Move each branch's rationale and todo reference to the end of its own sub-bullet, so the decision
   is readable before the justification.
4. **Change no rule.** Verify by reading the before and after side by side and confirming every
   branch, its trigger, and its action survive verbatim in meaning. A behaviour change here is a
   regression, not an improvement.
5. Re-check `check_instruction_budget.py` afterwards - `skills/commit/SKILL.md` is not in the
   always-loaded set, but the file is read in full once per session by every commit-bearing run, so
   the restructure should not grow it materially.

## Acceptance

- The exit-1 branches are individually addressable (a future todo can say "the personal-repo
  sub-bullet" and a reader can find it).
- Every branch present before is present after, with the same trigger and the same action. Diff the
  two versions branch by branch and say so in the completion note.
- `python ci/run_all.py` clean.

## Notes

- Filed from a `windows_taskbar_widgets` session per root `CLAUDE.md`: the fix edits
  `~/.claude/skills/commit/SKILL.md`, so it belongs here.
- Worth doing BEFORE the next behaviour change to this bullet, not after. Six edits have now landed
  into one paragraph; the seventh is where a rule gets lost in the stream.
- DONE 2026-09-10 via /loop-todos cycle 2, as a restructure and not a rewrite. skills/commit/SKILL.md step 8 unpushed-overlap check is now an intro plus the command, then labelled Runtime, What the script owns and Exit codes lead-ins, then a numbered list of the five outcome branches, each with its trigger bolded and its action, rationale and originating todo number kept inline. The safeguard that mattered here was the semantic diff: every branch, trigger, action and todo reference (368, 474, 498, 500, 849, 860, 862, 941) was enumerated old versus new in a table and matched one to one, with evaluation order preserved so branches 1 and 2 still rule out everything below them and branches 3 and 4 still resolve at the same end-of-queue moment. The only prose changes are splits at existing clause boundaries and turning one inline nested if-else into an explicit forward pointer. Nothing was simplified away on a judgement that it was redundant, which was the specific risk in restructuring a paragraph every commit in every repo reads. python ci/run_all.py exits 0.
