<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# sv.ps1 ephemeral entries vanish within minutes of a good boot

**Type:** bug
**Origin:** ai

## Goal

An `sv.ps1 ensure -Kind ephemeral` server stays up and listed until it is stopped, and `sv.ps1 stop`/`rm`/`logs` keep resolving the id `ensure` printed.

## Context

Reported by an e2e subagent in mc_plugins_tag (session c82d, 2026-10-09, worktree `D:/cargo-target/mc-e2e-c82d`, Paper e2e server on 25567). UNVERIFIED by the orchestrator, which only has the subagent's report:

- Twice, `ensure` printed `status=running action=started`, and within 1-2 minutes the entry was gone from `sv.ps1 ls`/`logs`. The Paper java process was dead too, with no "Stopping server" sequence in the Paper log (once right after a HuskHomes SQLite-busy warning, once with no warning).
- `stop`/`rm` on the id `ensure` had just printed answered "unknown project", and `-Project mc-e2e-c82d` seemed to come back as `mc-wt-c592` (another session's worktree project) between calls.
- Launching the same command (`.\gradlew.bat :testserver:runE2eServer --console=plain`) directly under the Bash tool's `run_in_background` stayed up through six suites.

Two other sessions ran their own sv-managed worktree servers on the same machine at the time, so a project-name or id collision between concurrent ephemeral entries is the first suspect.

## Approach

Read `skills/supervised-run/sv.ps1` and `sv-lib.ps1` for how ephemeral entries are keyed and reaped (project name derived from `-Root`? a reaper that kills entries whose parent session looks dead?). Reproduce with two concurrent `ensure -Kind ephemeral` calls from different worktree roots and different `-Project` names; check whether one call's bookkeeping overwrites or reaps the other's.

## Acceptance

- A test in `skills/supervised-run/test_sv.ps1` that starts two ephemeral entries with different projects/roots and shows both still listed and alive after the reaper interval; it fails on the current code if the collision is the cause.
- If the cause is something else, the todo records the measured cause.

## Notes

- Dropped by the cleanup-todos pass 2026-10-23: premise false for this repo. sv.ps1 and sv-lib.ps1 contain no reaper; ephemeral entries are deleted on process exit by design (supervised-run SKILL.md:78), and the reaping lives in server_supervisor registry.rs. Second-hand, unreproducible here.
