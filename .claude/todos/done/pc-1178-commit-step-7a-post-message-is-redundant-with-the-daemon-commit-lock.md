<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped the backlog for "post_message" and "committing". All hits are done/ items; none covers dropping 7a's announcement. -->
# 1178 - /commit step 7a: drop the per-commit post_message announcement

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-14

## Goal

`skills/commit/SKILL.md` step 7a tells every commit to `post_message` the pathspec it is about to
commit whenever `list_peers` shows another session. That announcement is redundant now:

- Claude Conductor already serializes `git commit` across sessions with a daemon-held per-project
  lock (`claude_usage_in_taskbar/src-tauri/src/daemon/hooks_server/commit_lock.rs`), enforced by
  PreToolUse/PostToolUse hooks. A second commit waits inside its own tool call, so it costs no extra
  API calls, and the lock expires after 5 minutes if its holder dies.
- A pathspec commit never reads the index, so a peer's commit cannot sweep this session's files.

Before the 2026-10-14 Conductor change, each such broadcast woke every idle chat in the project, and
each wake re-read that chat's whole context. A transcript scan that day found 550 of a Minecraft
listener chat's 1,882 turns were these wakes. Conductor broadcasts no longer wake anyone, so the
remaining cost is one tool call per commit for the poster, plus channel noise for every reader.

## Do

- Keep 7a's `read_messages` check: it is the part that caught real "don't commit" instructions
  (todo 1127).
- Drop, or narrow, the "call `post_message` naming the pathspec" sentence. If a peer is mid-edit on a
  file in the pathspec, a TARGETED `post_message` to that one peer is still right.

## Success

`/commit` in a repo with peers makes no broadcast post, and still reads the channel first.


## Notes

- Completed 2026-10-23 (loop-todos cycle 1): commit step 7a keeps read_messages and posts only to a peer mid-edit on a pathspec file; lock behavior checked in commit_lock.rs (5 min TTL, 120 s poll then deny); the history-rewrite announcement stays a broadcast since the lock does not cover reset.