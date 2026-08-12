<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=de321b7d -->
# The ancestor-pid process-tree walk (screenshot subfolder id) is unreliable on a machine running many concurrent `claude` processes - match by sessionId instead

**Type:** skill-improvement
**Origin:** ai

## Goal

Replace the "walk up the process tree looking for a name matching `claude`" technique (used to
derive `.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/`) with a lookup keyed by
`$env:CLAUDE_CODE_SESSION_ID` (or equivalent) against `~/.claude/sessions/*.json`, which is
unambiguous even with many `claude`/`claude-conductor` processes alive at once.

## Context

Real incident, 2026-08-08, `claude_usage_in_taskbar` (a project with many concurrent Conductor
sessions sharing one machine). Mid-session, re-running the documented PowerShell walk (`while
($p) { if ($p.Name -match 'claude') { return $p.ProcessId } ... }` starting from the current
process and walking `ParentProcessId`) returned **two different PIDs at two different points in
the SAME session**: `18808` early on, `42108` later (at `/close` Phase 0). Screenshots taken
earlier in the session are sitting under `.for_bepy/screenshots/18808-639217840922375568/`; a
fresh derivation later in the same session yields `42108-...`.

Cross-checked against `~/.claude/sessions/*.json` (one file per live session, keyed by pid, with a
`sessionId` field): `42108.json` has `"sessionId":"328b5862-baa7-4e51-96c1-427ea242b639"`, which
matches this session's actual sessionId (confirmed via output-file paths used throughout the
conversation, e.g. `...\328b5862-baa7-4e51-96c1-427ea242b639\tasks\...`). No `.json` file for pid
`18808` was checked/found to exist at all by the time of this investigation - it's plausible
`18808` was never this session's own process, but some OTHER concurrent `claude.exe` that a
same-named-match walk happened to hit (the regex `$p.Name -match 'claude'` also matches
`claude-conductor.exe`, and on a machine with several sessions open, `Get-CimInstance
Win32_Process` parent-walks can apparently resolve to a different process than intuition suggests,
possibly due to how tool-call subprocesses get parented in this harness). Root cause not fully
diagnosed - what IS confirmed is that the walk is not trustworthy as a stable identifier across a
single session's lifetime here, only the sessionId is.

Practical effect: `/close` Phase 3's screenshot cleanup, if it blindly re-derives the id fresh at
close time and trusts it, would silently skip cleaning up screenshots taken earlier in the SAME
session under a now-stale-looking id - not because they're not its files, but because the walk
itself drifted. (Ownership was still provable by direct knowledge in this specific case - the
folder held exactly the 3 files this session created, nothing else - but that's not something a
cold future session or an automated Phase 3 step can lean on.)

## Approach

1. Prefer `$env:CLAUDE_CODE_SESSION_ID` directly if the harness sets it (already used by the
   `/preview` skill's POST body) - if present, that alone is the stable per-session key; no PID
   walk needed at all for anything that just needs "this session's own identity".
2. Where a `<pid>-<ticks>` shaped folder name specifically is still wanted (matching the existing
   convention other tooling expects), resolve it via: read `~/.claude/sessions/*.json`, find the
   entry whose `sessionId` matches `$env:CLAUDE_CODE_SESSION_ID`, and use ITS `pid` +
   `Get-Process -Id <that pid> | select StartTime` for the ticks - not a fresh process-tree walk.
3. Update `close/rename-session.ps1`/`.sh` (the canonical implementation other skills copy) to use
   this method, so `/mockup`, `/screenshot`, and `/close` Phase 0 all inherit the fix in one place
   rather than each hand-rolling the walk.
4. If `CLAUDE_CODE_SESSION_ID` is unset (older harness / plain terminal), keep the process-tree walk
   as a documented fallback, but note it as best-effort/unstable rather than authoritative.

## Acceptance

- Deriving the screenshot-subfolder id twice in the same session (once early, once late) yields the
  SAME id both times, verified on a machine with 2+ concurrent Conductor sessions open in the same
  or different projects.
- `close/rename-session.ps1`/`.sh` and any skill that inlines its own copy of the walk (mockup,
  screenshot) are updated together, not just one.

## Notes

- Distinct from todo 54 (subagents inventing their own destination because they can't derive the
  path themselves) - this is about the MAIN session's own derivation being unstable, not about
  subagents lacking it.
- Corroborating incident, 2026-08-09, `windows_taskbar_widgets`: mid-session (during `/mockup`'s
  screenshot step) Claude didn't even attempt the process-tree walk - skipped straight to
  improvising its own id from Bash's `$$` and `date +%s` (`1727-1786287710`, not a real
  `<ancestor-pid>-<ancestor-start-ticks>` pair at all). At `/close` Phase 0, the correct walk was
  done properly for the first time and resolved to a completely different id
  (`17460-639219138939420866`), with zero files under it - the real mockup screenshots were
  sitting under the improvised folder instead. Ownership was only recoverable via direct
  first-person memory of creating those files this turn, same "not something a cold future session
  can lean on" gap the original incident already flagged. A crisper mid-skill
  `$env:CLAUDE_CODE_SESSION_ID`-based one-liner (per this todo's Approach) would likely have been
  followed correctly where the multi-step CIM process-tree walk was skipped entirely.

## Merged in (2026-08-11)

Absorbed todos 54 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
