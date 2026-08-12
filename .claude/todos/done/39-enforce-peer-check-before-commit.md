<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=bfb21592 -->
# Enforce the peer check before commit, instead of relying on Claude to remember

**Type:** skill-improvement

## Goal
Make "check for concurrent sessions before committing" a mechanism rather than an instruction, because the instruction was ignored six times in one session.

## Context
The Conductor session guidance says, verbatim:

> "before editing a file another session might also be touching, or before running `git commit`, call list_peers - if it shows another active session, call post_message to say what you're about to do before proceeding."

In the 2026-07-30/31 frontend2 mobile session (`fix/frontend2-mobile`), Claude made **six commits without ever calling `list_peers` first**, and only started coordinating after a peer session broadcast a collision warning on the repo channel. Three other sessions were active in the same repo the whole time. Nothing was lost, but that was luck: `list_peers` later showed 3-4 concurrent sessions, two of them editing `frontend2/src/pages/PurchaseItemsPage.tsx` — the same file.

This is an enforcement gap, not a "be more careful" fix. The rule lives in prose in the session preamble, competes with everything else there, and has no gate.

Related existing memory: `feedback-every-commit-via-commit-skill` (all commits go through `/commit`), which is the natural place to hang the check.

## Approach
Options, in rough order of preference:

1. **Add it to the `/commit` skill's flow** (`~/.claude-personal/skills/commit/SKILL.md`) as a numbered step before step 8's pathspec commit: call `list_peers`; if any peer is active, `post_message` naming the pathspec about to be committed, then proceed. This is one edit and covers every commit, since the global rule already forbids raw `git commit`.
2. A `PreToolUse` hook on `Bash` matching `git commit` that reminds/blocks. Heavier, and the MCP tool is not callable from a hook, so it can only warn.

Prefer option 1. Keep it cheap — a peer check that takes three tool calls will get skipped again.

Also worth deciding: should the check be skipped when the session is in its own worktree? It should NOT be — this session was in a dedicated worktree and still collided, because collisions happen at merge time, not on disk.

## Acceptance
- `/commit` cannot complete a commit without the peer check having run in that turn.
- A dry run with another Conductor session open produces a `post_message` naming the files.
- The step is documented in the skill file, not just in Claude's head.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 188; renumbered to 39 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: Added step 7a to SKILL.md's `/commit` flow, right before step 8's pathspec commit: `list_peers` + `post_message` naming the pathspec, no worktree exemption, silently skipped when the MCP tools aren't available.
