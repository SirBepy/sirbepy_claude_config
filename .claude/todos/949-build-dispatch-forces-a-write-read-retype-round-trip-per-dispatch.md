<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=6, reconfirm-count=1, content-hash=379344c9 -->
<!-- duplicate-checked: grepped the backlog and done/ for "build-dispatch", "mega-todos" and "dispatch prompt"; the only build-dispatch.ps1 hit is done/472, which CREATED the script. This is about the orchestrator-side cost of consuming its output, a surface 472 never addressed. -->
# build-dispatch.ps1 forces a write-read-retype round trip per dispatch

**Type:** skill-improvement
**Origin:** ai

## Goal

Remove the ~32KB-per-dispatch context round trip that `/mega-todos`'s builder-prompt helper
currently imposes on the orchestrator, without giving up the drift protection that made the script
worth having.

## Context

Measured 2026-09-05 during a `/mega-todos` run in `roblox-trend-pipeline` that dispatched 7
builders across 4 batches.

`~/.claude/skills/mega-todos/build-dispatch.ps1` (added by todo 472) correctly solves prompt DRIFT:
it reads the canonical preamble from `refs/builder-preamble.md` and the injected commit block from
`skills/mega-todos/SKILL.md`, so neither gets retyped from memory. That part works and should stay.

But the orchestrator cannot hand the script's output to the `Agent` tool directly. The actual loop,
per dispatch, is:

1. Run the script, writing ~15-17KB to a temp file.
2. `cat` the temp file to pull those bytes INTO the orchestrator's context.
3. Retype all of it into the `Agent` tool's `prompt` parameter.

So every dispatch costs roughly 15KB in plus 15KB out of the main context, for a prompt whose
static block is byte-identical across all of them. Across 7 dispatches that is on the order of
200KB of context spent re-reading text the orchestrator had already read on dispatch 1. The whole
point of `/mega-todos` is that "the main thread only ever holds lane assignments, barrier results,
and the summary" (SKILL.md's opening quote), and this is the one place that promise leaks.

Worse, step 3 quietly reintroduces the exact risk the script exists to remove: the orchestrator is
transcribing the static block by hand again, just from a fresher source. It happened to stay
faithful this run, but nothing checked it.

Observed side effect worth keeping in mind for any fix: passing prose in `-Owned` (e.g.
`'templates/ (the entire tree, all files under it)'`) is substituted verbatim into the literal
`git commit -- <FILES>` line in the emitted prompt, producing a command that cannot run. The
prose belonged in `-Task`. A fix that validates `-Owned` entries look like paths would catch that
class of error too.

## Approach

Options, roughly in order of appeal. Each needs checking against what the harness actually allows
before committing to it:

1. **Verify whether a dispatch prompt can reference a file instead of inlining it.** If a builder
   subagent can be told "your full brief is at `<abs path>`, read it first", the orchestrator
   writes the file and passes a ~200-byte pointer. This is the big win if it holds. Test it with
   one real dispatch before rewriting the skill: a subagent that ignores the pointer and starts
   improvising is worse than the current cost.
2. **Split the prompt.** Keep the per-dispatch parts (task, owned files, off-limits, verify floor)
   inline where the orchestrator genuinely needs to think about them, and move only the invariant
   static block behind a pointer. Smaller win, but it degrades safely: if the pointer is ignored,
   the builder still has its actual task.
3. **If neither works, say so in the skill.** Document that the round trip is the known cost and
   that the orchestrator should read the script's output ONCE (dispatch 1) and reuse the static
   block from context for later dispatches in the same run, rather than re-`cat`ing each time.
   That is what the 2026-09-05 run ended up doing by judgment; it should be written down instead
   of rediscovered.

Also, independent of which option lands: make `build-dispatch.ps1` reject an `-Owned` entry
containing a space or a parenthesis, naming `-Task` as where prose belongs.

Rejected: dropping the script and pasting the block by hand. That is the pre-472 state and the
drift it caused (`bdb0323`) is the reason the script exists.

## Acceptance

- A `/mega-todos` run of N dispatches no longer costs N full copies of the static preamble in the
  orchestrator's context, OR `skills/mega-todos/SKILL.md` states plainly that it does and tells the
  orchestrator how to minimise it.
- If option 1 or 2 is taken, it is proven with one real dispatch that reads its brief and completes
  correctly, not asserted.
- `build-dispatch.ps1` errors on an `-Owned` entry that is not path-shaped, with a message naming
  `-Task`.
- `python ci/run_all.py` passes.
