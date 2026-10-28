<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=43f67690 -->
# The new git peer backstop warns on a session's own commit

**Type:** task
**Origin:** ai

## Goal

Stop `hooks/list-peers-pre-edit-guard.py`'s HEAD-moved backstop from attributing a session's own
commit to a peer on the next edit in that repo.

## Context

Reported 2026-09-04 by the builder for todo 895 (commit `fd90f58`) as a known, accepted limitation
of the fix it shipped.

That fix persists the session's last-seen HEAD sha per repo and warns whenever a later edit sees HEAD
has moved, deliberately independent of what `list_peers` reports, since `list_peers` was proven to
fail open. The gap: nothing refreshes the stored marker after the session commits its OWN work, so
the sequence commit-then-edit produces one warning per commit blaming the session for its own sha.

Todo 895's acceptance never required suppressing this, so it shipped as-is. It matters because a
guard that cries wolf on ordinary work is a guard that gets ignored, which is the failure mode the
backstop was added to prevent in the first place.

## Approach

Refresh the stored marker at the moment the session commits, so the backstop only ever fires on a sha
the session did not create. Candidate places, in rough order of preference:

1. A PostToolUse hook on a successful `git commit` that rewrites the marker. Self-contained, and it
   works for any commit path, including a builder subagent's own pathspec commit.
2. Have `hooks/commit-guard.py` write the marker as a side effect once it lets a commit through.
   Cheaper, but it fires before the commit succeeds, so a rejected commit would falsely advance it.
3. Compare against `git log --format=%an %ae` or the session marker directory to decide authorship
   rather than tracking a sha at all.

Option 1 looks right; confirm a PostToolUse hook can see the command's exit status before committing
to it.

## Acceptance

- Commit, then edit a file in the same repo: no peer warning fires.
- A genuine peer commit landing between two edits still warns.
- `hooks/test_list_peers_pre_edit_guard.py` covers both cases and `python ci/run_all.py` exits 0.

## Notes

- Filed by /mega-todos on 2026-09-04 from a wave-1 builder's out-of-scope report.
- DONE 2026-09-10 via /loop-todos cycle 1 via Approach option 1, the PostToolUse refresh. hooks/list-peers-pre-edit-guard.py gains is_git_commit_command (line 82), a token-based detector mirroring commit-guard.py own, so commit-graph, a --grep containing the word commit, or the word inside a message never false-positive; handle_post_tool_use (line 163) rewrites this session marker to the post-command HEAD after a real commit; and main() now dispatches on hook_event_name so the original pre-edit path is byte-identical for every other event. Refreshing unconditionally is safe because a failed or rejected commit never moves HEAD, so the refresh just re-reads the truth. settings.json gained ONE PostToolUse entry matching Bash and PowerShell, which was genuinely unavoidable: without a new event there is no way to observe that this session just committed. Both directions tested: a session own commit refreshes the marker and the next edit is silent, and a commit that no PostToolUse call ever observed still produces the HEAD-moved warning naming the file, so the peer case the guard exists for is intact. Accepted limitation, documented in the module docstring rather than left to be rediscovered: a peer commit landing between this session own edit and its own commit is absorbed by the refresh, which is inherent to a single-sha marker.
