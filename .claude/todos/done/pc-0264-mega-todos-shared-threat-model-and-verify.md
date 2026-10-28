<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=10, reconfirm-count=1, content-hash=8767e58d -->
# /mega-todos: parallel agents on a shared threat model, and an --all-targets verify floor

**Type:** skill-improvement
**Origin:** ai

## Goal

Close two gaps in `~/.claude/skills/mega-todos/SKILL.md` that a real run on 2026-08-12 turned into a shipped security hole and a shipped broken test build.

## Context

Run of 2026-08-12 in `claude_usage_in_taskbar`: 22 todos, 11 lanes, 24 agents. Both failures were found afterwards by `/code-check`, not by the run's own barriers.

**Gap 1, the serious one. Two agents given the same brief hardened their inputs differently.**

Todo 434 and todo 244 both added daemon RPC modules exposing a filesystem path parameter to remote clients, and both were added to the same `SAFE_METHODS` allowlist. They ran in the same lane, sequentially, with 244's brief explicitly saying "follow whatever daemon-method pattern todo 434 just established".

244's agent independently added an `is_known_cwd` guard and tests for it. 434's agent did not. Result: `remove_worktree` was remotely callable with an arbitrary client-supplied path. 244's own doc comment even documented the divergence ("Unlike worktrees.rs's raw `cwd` params...") and nobody read it, because a doc comment is not a gate.

The lane rule as written partitions by FILE OVERLAP only. File overlap is the right unit for "can these two agents write concurrently", but it is the wrong unit for "do these two agents share a security invariant". Two modules can be file-disjoint and still share a threat model.

**Gap 2. The verify ladder says `cargo check`, and one builder plus the orchestrator both used plain `cargo build`.**

`cargo build` does not compile `#[cfg(test)]` code. So it reports an import used only by tests as an unused-import warning. Acting on that warning deleted a live import and broke `--all-targets` for hours without any check going red.

## Approach

In `SKILL.md`:

1. **Step C (lane assignment):** after partitioning by file overlap, add a second pass over the AUTO queue asking whether any two todos touch the same trust boundary (a network-reachable allowlist, an auth check, a path/id accepted from a client, a permission gate). If so, either put them in one lane with an explicit "apply the SAME guard as its sibling" instruction, or write the specific guard into BOTH briefs. Do not rely on one brief saying "follow the pattern the other one established" - that is what failed.
2. **Verify ladder:** change every Rust verify mention from `cargo check` to `cargo check --all-targets`, and add one line stating why: plain `cargo build`/`cargo check` skips `#[cfg(test)]`, so unused-import warnings from it are wrong for test-only imports and acting on them breaks the test build silently.
3. Consider a barrier line item: for any todo that added an entry to a remote-callable allowlist, diff its input validation against the sibling entries already in that list.

## Acceptance

- SKILL.md Step C names the trust-boundary pass, with the 434/244 case as the worked example.
- No bare `cargo check`/`cargo build` left in the verify ladder.
- A future reader can tell WHY `--all-targets` is mandatory without re-deriving it.

## Notes

- Done 2026-08-12, commit c930934. Step C gained a trust-boundary partition pass with the 434/244 case as the worked example and a ban on follow-the-sibling-pattern briefs; every Rust verify mention is now --all-targets with the cfg(test) reason written down.
