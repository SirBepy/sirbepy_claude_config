<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=2, content-hash=1041ca4e -->
<!-- duplicate-checked -->
# /commit's unpushed-overlap check asks a question a phase sweep has already answered

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/commit` step 8's unpushed-overlap check from demanding a question on every commit of a
planned multi-commit sweep that legitimately touches one file more than once.

## Context

Hit twice in one session, 2026-08-22, during harvest phase 4 (todos 424, 429, 442, all of which
edit `CLAUDE.md` by design - `PLAN.md` labels the phase "Same file, so sequential").

Step 8's check is hunk-level and it worked exactly as specified: `CLAUDE.md` line 61 blamed to
`2b49016`, this session's own immediately-preceding commit, so the file-level pre-filter survived
and a real hunk-level hit was produced. The check then says:

> **interactive session** - STOP, name the overlapping commit and the blamed lines, ask via
> `AskUserQuestion` whether this is follow-up on the same unit of work ... or genuinely separate

The problem is that the answer was already settled before the sweep started, twice over: the dev
had explicitly approved a four-commit plan, and `PLAN.md`'s own tip 2 states the rule the check is
asking about - *"One commit per todo, never batched, so a revert is surgical."* Asking would have
re-litigated a decision made minutes earlier, so the run took the genuinely-separate branch and
surfaced the overlap in its report instead, which is the behaviour the check defines for
**unattended** runs only. That was a judgement call outside the skill's letter, and the skill
should either sanction it or not.

This is not an argument that the check is wrong. It catches a real failure (patching a commit you
just made instead of folding it) and 368 already narrowed it once from file-level to hunk-level to
kill exactly this kind of noise. The remaining gap is narrower: **the check has no notion of a
pre-declared multi-commit plan**, so a phase that is *designed* to touch one file N times pays N-1
interruptions for a question with a known answer.

## Approach

1. Confirm the frequency before changing anything, per this repo's hook doctrine. Count how often a
   real hunk-level hit lands on a commit from THIS session versus one from another session or an
   older run. Only the same-session, same-sweep case is in scope; an overlap with someone else's
   unpushed work is exactly what the check is for and must keep asking.
2. Prefer inverting the problem over loosening the check, which is this repo's stated preference
   (`PLAN.md` hook doctrine: "prefer inverting the problem - require an explicit marker on the
   legitimate case - over detecting the violation"). The natural marker already exists: a claimed
   todo id. A commit whose pathspec belongs to a different claimed todo than the overlapping commit
   is by definition a separate unit of work.
3. Consider the cheapest version first: allow the caller to declare a sweep once ("these N commits
   are one approved plan"), and have the check report rather than ask for overlaps *within* that
   declared set, while still stopping hard for anything outside it.
4. Do not widen the unattended branch to cover interactive runs generally. The distinction between
   "nobody can answer" and "the answer is already on record" is the whole point.

## Acceptance

- A real measurement of same-session overlap frequency exists before the skill is edited.
- Whatever ships still STOPS on an overlap with another session's unpushed commit, proven by a case
  rather than by reading the diff.
- The skill no longer requires a question whose answer the dev gave when approving the plan, or the
  decision not to change it is recorded with the reasoning.

## Notes

Related but distinct from 368, which fixed the file-level false-positive rate. This is about the
surviving true positives being uninteresting in one specific, predictable situation.

**Sibling: todo 474, and they are NOT duplicates - check both before touching step 8.** 474 says the
overlap check should be a script instead of prose, because the algorithm was hand-written four times
in one run and silently mis-compared 7-char against 8-char shas twice. That is a correctness defect:
the check reports clean when it should not. This todo is a policy defect: the check reports a real
hit correctly and then asks a question the dev already answered. Fixing either one leaves the other
standing, and whoever scripts 474 should decide there whether the sweep-aware behaviour from this
todo belongs in the same script.

Do not treat this as licence to skip the check. Two commits in this session took the
genuinely-separate branch and both said so explicitly in their report; the silent version of that is
the actual hazard.
- Completed in wave 2 with no commit of its own: the sweep-aware marker this todo asked for was already delivered by two lane siblings that ran first - commit 1d987dd (todo 860) added an own-commit flag to overlap-check.sh so a same-run sha never stops the sweep, and commit 22bc405 (todo 862) added the session answer memory. Verified by its own builder rather than reimplemented.
