<!-- Claim before executing: .claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1338 is testing-floor-guard, a different surface -->
# Push-gate boundary counts a push from another repo; a commit-skill memory still fires on the dispatch preamble's /commit

**Type:** task
**Origin:** ai
**Summary:** Two residuals left after the review-unpushed items 12 and 14 fixes (lane F3, 2026-11-07).

## Why

Item 14 asked for `--dry-run` and "a push in another repo" to stop counting as the boundary. The dry-run half is fixed (`all_pushes_upload_nothing` in `hooks/push-gate.py`). The other-repo half needs the pushed repo resolved per transcript entry, which `transcript_evidence` does not have today. Item 12's fix makes an Agent prompt match a skill only as a `/name` token, but the CLAUDE.md dispatch preamble itself says "Commit your own work with /commit", so that token still appears in every builder dispatch.

## Goal

Each case below behaves as listed, with a regression test that is red before the fix.

## Context

- `hooks/push-gate.py` `transcript_evidence` takes any non-error `git push` tool result as the boundary after which `/test` and `/e2e` must be loaded again. `git -C /other/repo push` and `cd /other/repo && git push` in the same session count, so the repo being marked loses the skills it loaded earlier. Fail-closed and recoverable (the model loads the skills again), hence low severity. Fix idea: `transcript_evidence` gets the repo root being marked, resolves each push's target with `resolve_push_target` (cwd from the transcript entry, `git_dash_c_path`), and counts only pushes into that root.
- `hooks/_memory_triggers.py` `match_entries` fires a `skills: [commit]` memory on any Agent prompt containing the `/commit` token, and retires it if `once: true`. Every builder dispatch carries "Commit your own work with /commit before your report-back", so the memory still fires on the first builder dispatch of a session, and on a read-only dispatch too (its line "The main agent will run `/commit` by pathspec" also matches the token). Only prompts that say "commit" without the slash no longer match. Whether that is wanted (the builder will in fact run /commit) or noise needs a decision from Joe: a `once: true` commit memory is spent on the dispatch instead of on the main session's own /commit.

## Approach

Add the payloads to `hooks/test_push_gate.py` (a transcript with a push into another repo, then a mark for this one) and to `hooks/test_memory_trigger.py`, prove red with `skills/close/red-check.ps1`, then fix.

## Acceptance

- A successful `git -C <other repo> push` earlier in the transcript does not erase the `/test` and `/e2e` loads for the repo being marked; a push into the marked repo still does.
- Joe's call on the second bullet is recorded here, and the memory trigger matches the chosen behavior.
