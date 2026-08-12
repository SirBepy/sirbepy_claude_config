<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=b99566a1 -->
# Builder dispatches should run the comment-noise prefilter themselves

**Type:** skill-improvement

## Goal

Stop the orchestrator having to hand-trim oversized comment blocks out of every subagent's work
before it can be committed.

## Context

On 2026-08-05 this happened **five separate times in one session**, on five different dispatches:

- `active-session-mount.ts`, a 6-line doc block, trimmed to 4
- `chat-renderer.ts`, a 6-line block, trimmed to 4
- `event-store.ts` (9/22, 40%) and `sessions-wiring.ts` (6/29) together
- five Rust files at once (`daemon_link.rs`, `daemon_bridge.rs`, `registry.rs`, `state.rs`,
  `types/project.rs`), one at 81% comment density with a 9-line block, delegated to a dedicated
  trimming subagent
- `rpc.rs`, twice: the first trim cut the longest run under 5 but left the ratio at 36%, so it
  needed a second pass

Every one of those dispatch prompts already stated the rule verbatim, several in bold, and one
explicitly said a previous dispatch had been sent back for it. Restating the rule harder is
demonstrably not working.

The cost is real: each trim is a read of the diff, one or more edits, a re-run of the prefilter,
and for Rust a full `cargo build` re-verify, at roughly two minutes a go.

The fix is mechanical rather than motivational. The prefilter is a single deterministic command
that the builder can run against its own diff before reporting, exactly as it already runs
`pnpm tsc --noEmit` and `cargo build`.

## Approach

Amend `~/.claude/refs/delegation-doctrine.md`, in the "Every builder prompt embeds, without
exception" list, to add the comment-noise prefilter to the verify floor rather than leaving it as
a prose rule. The prompt should require the builder to:

1. run the prefilter from `~/.claude/skills/commit/comment-noise.md`, scoped to its own diff
   (`git diff HEAD -- <files it changed>`)
2. trim until it prints nothing
3. paste the clean output in its report alongside the typecheck and build output

The command is already written verbatim in `comment-noise.md`; the doctrine should point at it
rather than duplicating it, so the two cannot drift.

Note the prefilter needs a bash-capable shell for `awk`. On Windows dispatches that means the
Bash tool, not PowerShell, and the prompt should say so or builders will report it as unavailable.

## Acceptance

- A builder dispatch produces a diff that passes the prefilter with no orchestrator intervention.
- The builder's report includes the prefilter output as part of its verify floor.
- Measured over the next few multi-dispatch sessions: zero orchestrator-side comment trims.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #497) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Related but distinct, and worth merging with if someone picks these up together:

- **444** comment-cap enforcement only at PR time
- **478** `/commit`'s comment-noise check enforcement gap
- **462** trim oversized comment blocks in split modules

Those three are about enforcement at commit and PR boundaries. This one is about catching it one
step earlier, inside the dispatch, so it never reaches the boundary.

**2026-08-09 data point: the main agent, not a subagent, hit the exact same failure.**
Solo (non-dispatched) work on `types/chat.rs` and `chat/history.rs` produced two doc-comment
blocks over the 4-line hard cap (5 and 6-7 lines), with the full CLAUDE.md comment-cap rule
already loaded in context the whole time. Only `/commit`'s own comment-noise prefilter caught
it. Stronger evidence than the subagent case: even with the rule fully in context (not just
restated in a dispatch prompt), self-application while typing still failed. Supports this
todo's "mechanical, not motivational" framing - the fix likely generalizes past "builder
dispatches" to "any drafting pass, including the main agent's own."
- completed, commit 39029b7
