<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Problem: Claude ends turns in full-auto repos without committing

**Type:** skill-improvement

## Goal

Design and ship a mechanical (hook-based) backstop so Claude cannot end a turn in a
`full-auto.md`-importing repo with uncommitted qualifying changes, without asking permission and
without a passive "let me know if you want /commit" stall.

## Context

In repos whose CLAUDE.md `@import`s `~/.claude/snippets/full-auto.md`, Claude is supposed to
auto-commit qualifying changes (edit made, fast checks passed, turn ended cleanly, no objection)
without asking. It has failed this 3 times in the `claude_usage_in_taskbar` project alone: twice
by asking permission outright, once by ending a turn with a passive offer that stalls the same
way.

What's already in place: global CLAUDE.md rule + `~/.claude/snippets/auto-commit.md` (imported
via `full-auto.md`); a feedback memory (`feedback_auto_commit_full_auto_projects.md` in the
project's auto-memory) already documented this after occurrence #2. None of it stuck - memory/
prompt-based correction is not mechanical; it depends on Claude reliably recalling and applying it
every single turn, which it hasn't. Same root cause as this folder's narration-before-tool-calls
item ([[12-narration-before-tool-calls-systemprompt]]): rules living in context/memory get
deprioritized as the window fills, with no harness-enforced backstop.

## Approach

**What was tried (2026-07-15 session, 7 rounds of /iterate-it + final /rate-it):** iterated a
Stop-hook-based mechanical enforcement design through 5 Explore + 2 Polish rounds, converging from
3/10 to 6/10, then got a final solo /rate-it (opus 4.8, high effort) on the assembled end-to-end
design: **5/10, "coin flip."** Not shipped.

**Design reached (P9), for reference if resuming this:**
1. Gate: no-op unless the canonical git root's CLAUDE.md contains `@~/.claude/snippets/full-auto.md`;
   no-op on active merge conflict or a gitignored opt-out file.
2. `PostToolUse` on `Edit|Write|MultiEdit|NotebookEdit`: append touched path to a marker keyed by
   canonical git root (resolved per-edited-file, not session_id - avoids the subagent-session-
   identity question entirely).
3. `PostToolUse` on `Bash` (unconditional): re-run `git status --porcelain`, append newly-dirty
   paths to the same marker.
4. `WorktreeRemove` hook (a real top-level hook event confirmed to exist in this Claude Code
   install's settings.json schema, sibling to `WorktreeCreate`): deny worktree teardown if the
   worktree is dirty.
5. `Stop` hook (backstop): sweep main root + every `git worktree list` entry, re-verify each
   marker's paths via ground-truth `git status`, block once (respecting `stop_hook_active`) naming
   dirty files.
6. Prune stale markers by age on every Stop.

**Rejected along the way (don't re-propose):** raw `git diff --name-only HEAD` as sole signal
(misses untracked files); any acknowledgment TEXT - chat or Bash output - as proof a commit
landed; session-id-keyed baseline snapshots of shared git-tree-state (cross-contaminates under
concurrent sessions in the same repo, which the dev does run); reusing the taskbar-usage project's
own statusline-chip UI channel (verified unbuildable - pull-based IPC scoped to hub-spawned chats
only); retrospective full-transcript JSONL parsing at Stop time; "warn once ever per file then go
silent"; regex over final-message offer-phrasing.

**Candidate path if resumed later:**
1. Empirically verify `WorktreeRemove` timing + blockability first - a half-hour spike, not a
   redesign, and it determines whether step 4 survives as-is or needs replacing.
2. Consider dropping step 3 entirely: the Stop hook already re-verifies every recorded path
   against ground truth, so the Bash-branch markers may be redundant belt-and-suspenders.
   Simplifies the design and removes the perf concern.
3. Fix concurrent-session correctness properly: record per-path which session dirtied it
   (reintroduces some session-id handling, deliberately avoided this round) and make every marker
   write atomic (write-temp-then-rename or flock).
4. Alternative worth considering fresh: scope down entirely. All 3 real violations so far were
   inline edits in a single non-worktree session - steps 1, 2, and 5 alone (no worktree handling,
   no Bash-scan) already cover that case cleanly and were never individually challenged across any
   of the 7 rounds. Ship the narrow version now, defer worktree/concurrency hardening until it
   actually bites in practice.

## Acceptance

- Claude cannot end a turn in a full-auto repo with uncommitted qualifying changes without either
  committing or being explicitly blocked/prompted by the hook - no silent passive-offer stall.
- Must not falsely block on: files legitimately left dirty mid-work by a concurrent session in the
  same repo, or a worktree the dev is still actively using.

## Notes

**Unresolved, load-bearing gaps that kept the score at 5/10:**
1. `WorktreeRemove`'s actual semantics are unverified - the settings.json schema confirms the
   event *name* exists, not that it fires before disk removal (vs. post-hoc notification) or that
   it's blockable (vs. `PreToolUse`, which documents `permissionDecision: deny`). This was flagged
   "VERIFIED" in the design when only the event name had been checked - needs an empirical spike
   before trusting it.
2. Concurrent-session marker corruption was relocated, not fixed: (a) multiple hook processes
   doing read-parse-append-write on one shared JSON marker race with no lock or atomic rename;
   (b) session A's Stop hook can read a marker containing paths session B legitimately left dirty,
   and block session A for session B's files.
3. Step 3's cost model was wrong: the unconditional `git status --porcelain` scan run after every
   Bash call has real per-call latency across a long session with hundreds of mostly-file-
   untouching calls.
4. The gitignored opt-out file is a permanent bypass, reintroducing the "warn once then go silent"
   failure mode explicitly rejected earlier in the same design process.

**Open question:** is a hard Stop-hook block even the right lever, or would a cheaper, lower-
blast-radius passive signal (something the dev checks, not something that blocks Claude) get most
of the value without the mechanism complexity?

Filed 2026-07-17 from a stray top-level `todos/` folder that predated (and was never migrated
into) the `.claude/todos/` contract - see [[10-multi-account-cli-wrappers]] for the same origin
note and root-cause explanation (blanket `*` `.gitignore` rule hid the folder from `git status`).
- Duplicate of 02 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
