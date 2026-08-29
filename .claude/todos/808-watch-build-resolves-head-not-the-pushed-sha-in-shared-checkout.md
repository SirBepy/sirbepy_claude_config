<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=6aed3bb6 -->
<!-- duplicate-checked -->
# watch-build.ps1 resolves HEAD at launch time, not the sha it was pushed for

**Type:** skill-improvement
**Origin:** ai

## Goal

`build-watch.md`'s launch step tells callers to omit `-Sha` so "there's no hand-typed sha to get
wrong" - but in a shared checkout with concurrent sessions, HEAD can move between `git push` and
the watcher launching, so the auto-resolved sha is wrong instead. Have `/commit`'s push flow
capture and pass the actual pushed sha explicitly.

## Context

Observed 2026-08-26 in `claude_usage_in_taskbar`, 4 concurrent peer sessions sharing one checkout.
`/commit pushnbump` pushed `738e5a0d`. The watcher was launched immediately after (no `-Sha`, per
`build-watch.md` step 3's explicit instruction), but by the time it ran `git rev-parse HEAD` a peer
session had already committed on top (`ce03f04a`, later `a31640e6`) - none of it pushed yet, so
`git ls-remote` still showed `738e5a0d` as the real remote HEAD. The watcher printed
`BUILD_RESULT=no_run SHA=ce03f04a...`, which reads as "the push may not have triggered CI" and is
false - `gh run list` showed a real, healthy `Tauri Release` run for `738e5a0d` in progress the
whole time.

`watch-build.ps1` already accepts an optional `-Sha` (`param([string]$Sha, ...)`, self-heals to
`git rev-parse HEAD` only when omitted/malformed) - the bug is entirely in the doc's guidance to
omit it, written before this repo routinely had concurrent sessions.

## Approach

1. In `build-watch.md` step 3, have the caller resolve the sha it just pushed - `git -C <path>
   rev-parse HEAD` run IMMEDIATELY after the `git push` succeeds, before any other tool call can
   let a peer's commit land in between - and pass it as `-Sha <sha>` to the launch command.
2. Update the "no hand-typed sha to get wrong" rationale: the risk framing was about a human
   mistyping a sha, not about a shared checkout drifting - note both risks and why passing the
   sha captured right after push resolves both (it's programmatic, not hand-typed).
3. Leave the script's own self-heal (fall back to `rev-parse HEAD` when `-Sha` is blank/malformed)
   alone - it's a reasonable last resort for callers that don't follow the doc.

## Acceptance

A `/commit pushnbump` in a repo with a concurrent peer session, where the peer commits (without
pushing) between this session's push and its watcher launch, still watches the sha THIS session
pushed - proven by reproducing the interleaving above and confirming the watcher's `SHA=` matches
`git rev-parse HEAD` captured right after `git push`, not a later value.

## Notes

Related but distinct from `371-watch-build-misreads-skipped-as-failure.md` (done) - that one is a
false `failure` verdict from misreading a `skipped` run; this one is a false `no_run` verdict from
watching the wrong sha entirely. Also related to `797` (positional refs in shared checkouts) and
`805` (CI flaking on a peer's mid-write) as the same family of "this repo now has concurrent
sessions and several tools still assume single-session," but none of the three overlap in scope.
