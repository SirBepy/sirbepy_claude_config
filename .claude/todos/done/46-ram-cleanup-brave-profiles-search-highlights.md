<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Continue Windows RAM cleanup: Brave profile dedup + Search Highlights + Flutter servers

**Type:** task

## Goal

Joe's machine (32GB RAM) was down to 1-3GB free. Session diagnosed where it goes and got as
far as presenting cleanup options, but Joe went to sleep before picking one. Resume at the
open decision and carry out whichever path he picks.

## Context

Full diagnostic pass (all read-only, nothing changed on disk yet):

**Big picture** (`Get-Process | Group-Object Name`, RAM by app family):
- Browsers total (brave + chrome + msedgewebview2): ~6.7GB across 84 processes
- Flutter toolchain (dart + dartaotruntime + dartvm), 3 concurrent projects: ~5.45GB / 17 procs
- Claude sessions (claude + claude-conductor, 8-9 concurrent Conductor sessions): ~4GB / 17 procs
- VS Code: 1.9GB / 14 procs
- WSL2 VM (reserved, not necessarily in use): ~941MB
- svchost (98 procs) + conhost (46 procs): only ~1.7GB combined - genuinely NOT the problem,
  despite looking like "tons of small processes" at first glance

**Dead end, no action needed:** 20 identical `node.exe` processes running
`Buzz\node-tools\...\claude-agent-acp\dist\index.js` looked like a leak. Re-checked minutes
later and they were gone on their own (node count 35->13, free RAM 1.2GB->2.8GB). Transient,
not a leak. Don't re-investigate unless it recurs and stays elevated.

**Brave deep dive** (Joe's prompt: "I only have 4 tabs open, how is that using RAM?"):
One Brave window with 4 tabs = 19 renderer processes, ~2.03GB total:
- 6 renderers = actual page content (~1.11GB - one page alone was 370MB)
- 11 renderers = browser EXTENSION background processes (~417MB) - these run permanently,
  independent of whether any tab is open
- plus GPU process (181MB), main/UI process (290MB), network/audio/storage utility (70MB)

**Brave profile audit** (Joe's follow-up: "I have 4 profiles, are extensions duplicated?"):
Read `Local State` (profile.info_cache) and each profile's `Secure Preferences` JSON
(`extensions.settings`) via PowerShell `ConvertFrom-Json` - do NOT re-read `Local State` with
the Read tool, it's a 72K-char single-line file full of P3A telemetry blobs that blows the
context window for no benefit; PowerShell JSON parsing is the way.

Profiles found: Profile 1 "Tecnomon" (25 real extensions), Profile 2 "TabsLabs" (5),
Profile 8 "Work" (1), Profile 10 "Fibo" (1). A "Default" profile dir exists on disk but has
no Preferences file - unused.

Confirmed duplication: **Bitwarden Password Manager installed in all 4 profiles.** Claude,
Cold Turkey Blocker, Vimium, and Dark Reader each installed in 2 profiles. 32 total extension
installs across profiles, only ~27 unique extensions - the overlap is pure duplicate RAM cost
since each profile is a fully separate installation with its own background process.

**Open decision Joe never answered** - presented as an AskUserQuestion, no reply given before
he signed off for the night:
1. **Dedupe extensions only** (Claude's recommendation) - keep all 4 profiles for
   identity/session isolation (Work vs personal logins staying separate), but remove the
   duplicate installs (Bitwarden, Claude, Cold Turkey, Vimium, Dark Reader) from whichever
   profiles don't actually need them. Needs Joe's input on which profile is "home" for each -
   Claude can't infer intent from installed-extension lists alone.
2. **Merge to one profile** - max RAM savings, but Work/Tecnomon/TabsLabs/Fibo sessions,
   cookies, and logins all collapse into one identity going forward. Real UX tradeoff, not
   just a RAM fix.
3. **Leave as-is** - Joe was just building understanding, no changes wanted.

**Two other items surfaced but never acted on** (conversation branched into the Brave/profile
investigation before circling back):
- **Windows Search Highlights**: 47-54 `msedgewebview2.exe` processes (~2.5-3GB), all children
  of `SearchHost.exe`. This is Windows injecting Bing web-content tiles into the Start Menu
  search box. Disabling it is a clean win - no functionality loss, doesn't touch Windows'
  actual file/app search (Win+S still works) and has nothing to do with Claude's own WebSearch
  tool (Joe was confused these were related - they're not). No registry change made yet;
  confirm exact method (registry key vs Group Policy) with Joe before editing, since it's a
  system-level change.
- **3 concurrent Flutter web dev servers** (zng-biller :8080, zng-app :42001, zng-admin
  :42002), ~5.45GB combined across dart/dartaotruntime/dartvm. Floated twice as an option;
  Joe never said which (if any) are safe to stop right now.
- **Trimming Claude/Conductor sessions** (~450MB per session, 8-9 running concurrently) was
  also offered as an option in the same round as Search Highlights/Flutter servers. Joe
  deflected into the Brave-tabs question instead of answering; never explicitly accepted or
  declined.

## Approach

1. Re-surface the 3-way profile decision above (dedupe / merge / leave) - don't re-derive the
   analysis, it's already done and documented here.
2. If dedupe: go profile-by-profile in `brave://extensions`, ask Joe which profile should keep
   each duplicated extension, disable/remove from the rest.
3. If merge: this is a real UX tradeoff (session/cookie isolation lost) - confirm Joe
   understands the consequence before touching anything, then walk through Brave's
   profile-merge/import flow (no clean built-in "merge" - likely means exporting
   bookmarks/passwords from the profiles being retired and manually re-adding extensions to
   the surviving profile, then deleting the old profile directories).
4. Independent of the profile decision: ask about Search Highlights (still pending) and the 3
   Flutter servers (still pending) - both were asked before but got sidetracked by the Brave
   tangent, not actually declined.

## Acceptance

- Joe has picked and Claude has executed one of the 3 profile-decision branches.
- Search Highlights and Flutter-server questions get an actual answer (yes/no/which), not
  left hanging again.
- Re-measure free RAM after any change (see Verify) to confirm the fix actually moved the
  needle - free RAM fluctuated 1.2-2.8GB even within this session, so a single before/after
  snapshot isn't reliable; take a couple readings.

## Verify

- [ ] `Get-CimInstance Win32_OperatingSystem | Select-Object @{N='FreeRAM_GB';E={[math]::Round($_.FreePhysicalMemory/1MB,2)}}` - current free RAM baseline
- [ ] `Get-Process | Group-Object Name | ForEach-Object { [PSCustomObject]@{ Name=$_.Name; Count=$_.Count; TotalMB=[math]::Round(($_.Group | Measure-Object WS -Sum).Sum/1MB,1) } } | Sort-Object TotalMB -Descending | Select-Object -First 15` - top consumers, numbers will have drifted since this session's snapshot
- [ ] `Get-Process msedgewebview2 -ErrorAction SilentlyContinue | Measure-Object` - check whether Search Highlights count is still 47-54 (i.e. still not fixed) or already dropped (someone else fixed it, or Windows updated)

## Notes

- 100% read-only session - no files edited, no registry changes, no processes killed. Nothing
  to roll back if picking this back up cold.
- Joe was tired/frustrated by the end ("i hate this so much") - keep the resuming tone
  action-oriented, jump straight to the open decision rather than re-walking the full
  breakdown.
- This todo lives in this repo's backlog (not a specific project's) because the diagnostic
  target was Joe's whole machine, not any one repo's code - there was nowhere more specific
  to file it. Convention in *this* repo is `todos/<id>-slug.md` directly at repo root (not
  nested `.claude/todos/`, since the repo root already is `.claude`) - `.gitignore` already
  excludes `todos/` via its whitelist pattern, no self-heal needed.
- Dropped by dev decision 2026-08-08 during /auto-do-todos: the RAM snapshot is from 2026-08-05 and stale, and C: is at 127.8G free, so the disk/RAM pressure that motivated it is gone. Not carried forward.
