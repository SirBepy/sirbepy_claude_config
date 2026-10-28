<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new finding, not itself a duplicate -->
# todo-duplicate-guard.py over-triggers on the common "split <file>" / "consider a shared X" todo shape

**Type:** skill-improvement
**Origin:** ai

## Goal

Reduce `hooks/todo-duplicate-guard.py`'s false-positive rate on structural `/code-check` findings,
specifically the very common "[file] should be split" / "Duplicate: [symbol]" title shapes, without
weakening its real catch (two todos genuinely covering the same file/defect).

## Context

Filing 6 `/code-check` structural findings into `claude_usage_in_taskbar`'s backlog on 2026-10-16,
5 of 6 tripped the guard on first write - every one a false positive, confirmed by reading the
cited "duplicate" candidates (none touched the actual file in question; e.g. a finding about
`src-tauri/src/sessions/message_drafts/api.rs` was flagged against `gaming-mode`,
`schedule-recurrence`, `chat-transforms-markdown`, `chat-dom-renderer`, `remote-access-tailscale` -
none of which touch `message_drafts/api.rs` at all).

Root cause (inferred, not read from the hook's source this session - verify before changing it):
the guard's "3+ shared tokens, or 2+ covering most of a short title" heuristic treats generic
structural vocabulary ("split", "module", "file", "render", "panel", "existing", "shared",
"consider", "priority") as salient, but a backlog that already has 1150+ todos accumulates dozens
of "split X into Y" / "extract Z" titles that ALL share this vocabulary by the very nature of the
finding category - it's the title shape `/code-check` itself always produces for a class-2
structural finding, not evidence of covering the same subject.

## Approach

Not yet designed - needs the hook's actual source read before changing anything (per
`refs/debugging-method.md`, don't guess at a fix for code not yet read this session). Candidate
directions to evaluate:
- Weight/require at least one shared token that is a distinctive noun (a filename stem, a specific
  symbol name) rather than counting generic structural verbs/nouns toward the 2-3 threshold.
- Exclude a fixed stoplist of category vocabulary ("split", "module", "file", "shared", "existing",
  "consider", "extract", "render", "panel") from the shared-token count entirely.
- Weight a shared FILENAME (from the new todo's `**Files:**`-adjacent content, if present) much
  more heavily than shared prose tokens - two todos about the same actual file are the real
  signal, prose vocabulary overlap is not.

Any fix must keep the real catch: a genuine second todo about the same file/defect should still
trip the guard. Test against this session's own candidate set as a regression check (the 5 false
positives plus any true positive in the existing backlog, e.g. re-filing `done/1120`'s exact defect
should still trip it).

## Acceptance

- The 5 false-positive patterns from 2026-10-16 (see Context) no longer trip the guard when
  re-tested with the same new-file content.
- A genuine duplicate (same file, same defect, re-filed) still trips the guard.
- `python ci/run_all.py` (or whatever test suite covers `hooks/todo-duplicate-guard.py`) stays
  green.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
