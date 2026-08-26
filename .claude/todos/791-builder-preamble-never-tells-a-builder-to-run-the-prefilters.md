<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The builder preamble never tells a builder to run the commit prefilters

**Type:** skill-improvement
**Origin:** ai

## Goal

Put the prefilter requirement into `refs/builder-preamble.md`, so a builder cannot ship an em dash
or a comment-cap breach just because the orchestrator's dispatch prompt forgot to ask for it.

## Context

Hit live 2026-08-25 in `~/.claude`. A builder dispatched for todo `392` edited 11 skill files and
introduced **three em dashes**. Its verify floor was `python ci/run_all.py`, which passed, because
CI checks hook self-tests, skill frontmatter and the CLAUDE.md token budget and does NOT check for
em dashes. The orchestrator caught them only because it ran `prefilter-gate.sh` by hand before
committing.

**The gap is structural, not carelessness.** `refs/delegation-doctrine.md`'s full-orchestrator
section already requires it, describing "the comment-noise prefilter every builder runs on its own
diff before reporting". But `refs/builder-preamble.md` - the literal paste block that every dispatch
embeds, and the file the doctrine points at precisely so nothing gets hand-retyped and drifted -
contains **zero** mentions of `prefilter`, `comment-noise` or `em-dash` (grepped 2026-08-25). So the
requirement lives only in prose an orchestrator may not have read, while the paste block that would
enforce it stays silent.

`hooks/dispatch-preamble-guard.py` string-checks three markers in every dispatch prompt, none of
which covers this. That guard is why the preamble is the right home: whatever lands in the block is
what actually reaches builders.

Note the asymmetry that makes this worth fixing rather than tolerating: `/mega-todos`' injected
commit block DOES instruct its builders to run all three prefilters, because those builders commit
their own work. A builder in the ordinary stage-only mode never sees that instruction, so the
stricter path is the one that already works and the common path is the one that leaks.

## Approach

1. Add a short paragraph to the canonical block in `refs/builder-preamble.md`: before reporting, run
   `bash "C:/Users/tecno/.claude/skills/commit/prefilter-gate.sh" <your changed files>` and fix what
   comment-noise and em-dash flag; a secret-scan hit STOPS you and gets reported, never auto-fixed.
   Mirror the treatment split already written in `/mega-todos`' injected commit block rather than
   inventing new wording.
2. Decide whether this belongs in the block unconditionally or as a `<PREFILTER>` placeholder in the
   placeholder table. Unconditional is probably right - a read-only dispatch changes nothing, so the
   gate is a no-op there rather than a burden - but check the read-only opt-out interaction before
   choosing, and write down which and why.
3. Consider whether `hooks/dispatch-preamble-guard.py` should string-check a fourth marker for it.
   **Lean no**: the guard's existing three are cheap literal checks, and a fourth raises the
   rejection surface for every dispatch in every repo. Record the decision either way.
4. Check whether the paths in the block need to be absolute. `/mega-todos`' version says they do,
   because a builder's repo root is usually not `~/.claude`, and a repo-relative path silently fails
   to resolve. The same reasoning applies here.

## Acceptance

- `refs/builder-preamble.md` names the prefilter step, with the per-script treatment (trim / fix /
  STOP-on-secret).
- A dispatch that pastes the block verbatim carries the requirement with no extra orchestrator work.
- The read-only-dispatch interaction is settled explicitly, not left ambiguous.
- `python ci/run_all.py` passes.

## Notes

Related but distinct: `447` covers `prefilter-gate.sh` having no repo target, which is the same
script failing in a cross-repo commit. If both are being worked, do `447` first - a builder told to
run a script that cannot resolve its repo is worse than one never told at all.
