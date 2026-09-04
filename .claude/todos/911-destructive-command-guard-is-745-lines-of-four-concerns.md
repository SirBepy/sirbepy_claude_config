<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todos 869, 797 and 835 all edited this file's matchers on 2026-09-04 and are in done/. None of them is about the file's size or its module boundaries. -->
# destructive-command-guard.py is 745 lines carrying four separate concerns

**Type:** task
**Origin:** ai

## Goal

Split `hooks/destructive-command-guard.py` along its existing concern boundaries, keeping the
current file as the CORE/MIDDLE/SHARED dispatcher.

## Context

Found 2026-09-04 by `/code-check` over the `/mega-todos` run diff. The file grew to 745 lines
that day: todos 869, 797 and 835 each added a matcher family to it, in sequence, in one lane. Each
addition was correct on its own; the size is the accumulation.

The four concerns the reviewer identified, which are also the natural seams:

- filesystem and device destructive matching (`rm`, `Remove-Item`, `mkfs`, `chmod`)
- SQL statement matching
- git force/reset/stash matching
- shared-checkout peer logic (`fetch_peer_count`, `stash_swept_files`, `is_main_checkout`)

Handle with care rather than mechanically. The file is dense with cross-referencing comments and
regexes, several of which exist because a specific false positive was measured against a real
command corpus (`match_disk_doctor_delete` was tuned against 86,430 harvested commands, 9 hits,
0 false positives). A comment that explains why a regex is shaped a certain way must travel with
its regex, and a verbatim move is exempt from the comment-noise cap - `comment-noise.sh` now
detects a verbatim move automatically, so the gate will not fight this.

## Approach

1. Read `~/.claude/refs/refactoring-method.md` first. Name the command that would fail if the split
   were done wrong before starting - that is not optional here.
2. Extract in the order above, one concern per commit, running
   `python hooks/test_destructive_command_guard.py` (over 100 cases) after each.
3. Keep `hooks/destructive-command-guard.py` as the entry point and the CORE/MIDDLE/SHARED tier
   dispatcher, so `settings.json` needs no change.
4. Consider whether the corpus-measurement script this file references belongs beside it.

## Acceptance

- No behaviour change: all existing cases in `hooks/test_destructive_command_guard.py` pass
  unmodified, and `python ci/run_all.py` exits 0.
- `settings.json` is unchanged - the hook path and entry point still resolve.
- Every incident-explaining comment sits with the regex it explains.

## Notes

- Filed by /mega-todos on 2026-09-04 from the run's own `/code-check` pass.
