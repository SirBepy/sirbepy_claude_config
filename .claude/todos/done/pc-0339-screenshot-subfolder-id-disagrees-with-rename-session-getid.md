<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=8, reconfirm-count=1, content-hash=deb85113 -->
# Screenshot subfolder id in CLAUDE.md disagrees with rename-session.ps1 -GetId

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the screenshot subfolder id that a session *creates* match the id `/close` later uses to prove
ownership, so purge scoping actually works.

## Context

Observed 2026-08-14 in a `zng-biller` session.

Global `CLAUDE.md` (UI & visual changes) tells a session to write throwaway screenshots to
`.for_bepy/screenshots/<claude-ancestor-pid>-<ancestor-start-ticks>/`, described as a process-tree
walk to the Claude ancestor plus its start ticks. Following that literally produced
`33104-639222976961254202`.

`/close` Phase 0 resolves the same id a different way, via
`~/.claude/skills/close/rename-session.ps1 -GetId`, which matches `$env:CLAUDE_CODE_SESSION_ID`
against `~/.claude/sessions/*.json`. In the same session that returned **`10556-134312566990498489`**.

Different PID and a different-magnitude tick value, so the two schemes do not agree at all. The
consequence is exactly what the subfolder scheme exists to prevent: Phase 3 step 3 says a session
may delete only files under *its own* Phase 0 id, so a session that created its folder per
CLAUDE.md finds no folder at the Phase 0 id and its real folder is indistinguishable from "another
session's subfolder, never delete". The screenshots then rot forever. The `zng-biller` repo already
has three such subfolders plus 49 loose root-level files.

`/close`'s own Phase 0 notes that the process-tree walk was already found unreliable (todo 60:
"the walk resolved to two different PIDs at two points in the SAME session"), and switched to the
sessionId match. CLAUDE.md was never updated to match, so the two halves of the same scheme now
describe different ids.

## Approach

1. Decide the single source of truth. `rename-session.ps1 -GetId` is the better one: it is stable
   within a session by construction, and it is what the purge already keys off.
2. Update global `CLAUDE.md`'s UI & visual changes section to say "get the subfolder id by running
   `~/.claude/skills/close/rename-session.ps1 -GetId`", and drop the process-tree-walk wording.
   Note this is a global `~/.claude` edit, so it needs Joe's go-ahead in the session that does it.
3. Check whether any other skill hardcodes the walk-based description and update those too.
4. Decide what to do about existing orphan subfolders. `/close` deliberately refuses to delete them
   because ownership cannot be established from outside. A one-off `/cleanup-todos`-style sweep with
   Joe confirming, or an age rule he explicitly opts into, are the options; do not have `/close`
   start deleting them unilaterally.

## Acceptance

- A session following CLAUDE.md creates the same subfolder id that `/close` Phase 0 resolves.
- Verified by actually running both in one session and comparing, not by reading the docs.
- `/close`'s purge deletes that session's own screenshots without the operator overriding scope.

## Notes

- Do not "fix" this by loosening `/close`'s purge to delete by mtime. That was explicitly rejected;
  concurrent sessions write files both newer and older than each other and mtime cannot tell them
  apart. The id scheme is the right design, it just has two disagreeing implementations.
- Completed via /auto-do-todos 2026-08-15: CLAUDE.md:84 now points at rename-session.ps1 -GetId as the single source of truth for the screenshot subfolder id, replacing the process-tree-walk wording the script own comments call best-effort/unstable. Repo-wide grep confirmed close, screenshot and mockup were already correct; the two remaining stale copies in skills/flutter-e2e/SKILL.md (lines 32 and 67) were fixed by the orchestrator after that file freed up. -GetId verified live, returns a <pid>-<procStart-ticks> shaped id.
