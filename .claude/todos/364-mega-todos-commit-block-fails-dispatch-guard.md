<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Following /mega-todos verbatim gets your dispatch rejected by dispatch-preamble-guard

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/mega-todos`'s injected commit block pass `hooks/dispatch-preamble-guard.py` on the first try,
instead of every builder dispatch being rejected until the author hand-patches in two marker strings
the skill never mentions.

## Context

Hit twice in one `/mega-todos` run on 2026-08-17 (claude_usage_in_taskbar).

`skills/mega-todos/SKILL.md` says to paste its injected commit block "verbatim into every builder
prompt", and separately says every dispatch "still carries the doctrine's canonical preamble minus
its stage-don't-commit line". Do exactly that and the dispatch is BLOCKED:

```
[dispatch-preamble-guard] Dispatch prompt is missing required preamble marker(s):
staging line ("Stage your changes but do NOT commit" or "Leave all changes unstaged");
.for_bepy/screenshots/ id line (or the READ-ONLY DISPATCH opt-out).
```

Two independent problems:

1. **The staging line is a hard-required marker, and `/mega-todos` explicitly tells you to remove it.**
   That is a direct contradiction between the skill and the hook. The workaround that actually works
   is absurd: quote the banned sentence anyway, then immediately say it is overridden, purely so the
   substring exists for the guard. That is what shipped in all six builder dispatches of that run.
2. **The screenshot-id line is required even on dispatches that obviously capture nothing** (a Rust
   refactor, a string edit). `refs/builder-preamble.md` offers `READ-ONLY DISPATCH` as the opt-out,
   but a builder that WRITES code and captures no screenshots fits neither branch, so the only route
   is to paste an irrelevant screenshot path into every prompt.

Cost that run: two rejected dispatches, each a full round trip, plus every subsequent prompt carrying
two lines of pure hook-appeasement noise that actively confuses the subagent (it is told not to
commit, then told that instruction is void).

The workaround is also fragile in a way worth naming: the guard matches SUBSTRINGS, so a dispatch can
satisfy it while telling the agent the opposite of what the marker says. The check passes; the intent
does not survive.

## Approach

Pick one, roughly in order of preference:

1. **Teach the guard about the commit-mode case.** Add a third accepted marker alongside the two
   staging phrasings, e.g. `COMMITTING IS PART OF YOUR JOB` (the literal heading `/mega-todos`'s block
   already uses). Then the skill's own text passes as written and nobody quotes a banned sentence.
   Also accept a `NO SCREENSHOTS` marker for write dispatches that capture nothing, so the read-only
   opt-out is not the only escape.
2. If the guard must stay as-is, fix the SKILL instead: make `/mega-todos`'s injected block include
   both required markers itself, with an inline note explaining they exist for the guard. At least
   then the contradiction is in one place and pre-resolved, rather than discovered per-run.
3. Whichever is chosen, `refs/builder-preamble.md`'s placeholder table should state which markers the
   guard actually enforces. Today it documents the block but not the enforcement, so an author has no
   way to know what is load-bearing until a dispatch is rejected.

Do NOT resolve this by loosening the guard to warn-instead-of-block. It caught real omissions; the
problem is that one of its required strings is one the sibling skill forbids.

## Acceptance

- A `/mega-todos` builder dispatch, written by following the skill exactly with no hand-patching,
  passes `dispatch-preamble-guard.py`.
- No dispatch prompt contains a quoted instruction it immediately contradicts.
- `refs/builder-preamble.md` names which markers are hook-enforced.
- The guard still blocks a dispatch that genuinely omits the working-dir / off-limits / staging
  information (verify with a deliberately incomplete prompt).

## Notes

- Related: `refs/delegation-doctrine.md`'s "Canonical builder preamble" section, which exists
  precisely so this block is copied rather than retyped. The 2026-08-17 run retyped it from memory in
  six dispatches, which is how the drift was noticed at all.
- The same run also found `/mega-todos` has no guidance on what to do when the target repo's working
  tree already holds another session's uncommitted files. That was handled ad hoc (hard-exclude the
  paths from every lane, announce on the repo channel). Worth a sentence in the skill's Step A, but
  it is a separate, smaller edit than this one.
