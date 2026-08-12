# disk-doctor — macOS platform file

Repeatable cleanup scan for Joe's Mac (darwin/arm64). You **advise**, never delete. Joe runs the commands.

## How to run a scan

**Dispatch, don't run inline.** Send the scan commands for this round to a `general-purpose` subagent,
`model: sonnet`, prompted to run the listed commands and return only a digested summary (dirs/caches
over ~1GB with sizes) - never raw `du`/`find` dumps into the main thread. One subagent call per round
(initial sweep, then a separate one per drill-down round) keeps the back-and-forth Joe-steered without
a monolithic report.

Run in parallel, then rank findings by payoff (GB freed × ease × reversibility):

```bash
df -h /                                                                                                                   # free space first
du -sh ~/* 2>/dev/null | sort -rh | head -25                                                                              # home top dirs
du -sh ~/Library/Caches/* 2>/dev/null | sort -rh | head -15                                                              # all caches (dynamic, no hardcoded names)
du -sh ~/Library/Application\ Support 2>/dev/null                                                                        # app data (not caches - separate blind spot)
du -sh ~/Library/Developer/Xcode/DerivedData 2>/dev/null                                                                 # Xcode build artifacts
xcrun simctl runtime list                                                                                                 # iOS sim runtimes (use -j flag only when extracting UUIDs for delete)
du -sh ~/Library/Developer/CoreSimulator 2>/dev/null
find ~ -maxdepth 6 -name node_modules -type d -prune 2>/dev/null | xargs du -sh 2>/dev/null | sort -rh | head -10        # maxdepth 6 caps runtime on large repos
du -sh ~/Downloads ~/.Trash 2>/dev/null
find /System/Library/AssetsV2 -maxdepth 1 -name "*iOSSimulator*" 2>/dev/null | xargs du -sh 2>/dev/null
```

Avoid `sudo du` - it blocks on a password prompt in this harness.

### Second-pass drill-down

After the initial scan, drill into the **top-3 home dirs exceeding 2GB**:

```bash
du -sh <dir>/* 2>/dev/null | sort -rh | head -10
```

Hard cap: 3 dirs max regardless of how many exceed the threshold. Skip `~/Library` if it appears in top-3 (it is an aggregator; its contents are already covered by the dedicated cache, AppSupport, and simulator commands) - substitute the next qualifying dir.

## Output rules

- Rank deletables, biggest realistic win first.
- Per item: size, what it is, regenerates/re-downloadable?, exact delete command.
- Flag slow-to-restore items (sim runtimes) - confirm live project targets before swinging.
- Never suggest anything in NEVER-TOUCH below.
- Offer to write commands; Joe runs them. You never run `rm`.

## Self-improvement (only when invoked as /disk-doctor)

At END of scan, propose any new KNOWN-SAFE spots, NEVER-TOUCH additions, or a SCAN LOG entry using the confirmation gate in `gate.md` (in this skill folder). Only edit this file when invoked as `/disk-doctor`. No silent/auto edits, no edits when triggered indirectly.

---

## NEVER-TOUCH (Joe's machine)

- `~/*.jks` keystores (test-keystore, kto-keystore, github-builds-keystore, some-old-key) - signing keys, loose in home.
- `~/josipm.gitlab.ssh` + `.pub` - SSH keys.
- `~/github-recovery-codes.txt` - account recovery.
- `~/fvm` (~1.7G) - Flutter version mgr, active toolchains. Not junk.
- `~/.claude/` - config, skills, memory.

## KNOWN SAFE-TO-DELETE (regenerates / re-downloadable)

- iOS Simulator runtimes via `xcrun simctl runtime delete <id>` - re-download from Xcode. Biggest win (~38G in `/System/Library/AssetsV2/com_apple_MobileAsset_iOSSimulatorRuntime`). GOTCHA: `simctl delete <id>` (no `runtime`) errors "Invalid device" - that subcommand is DEVICES only. Get runtime IDs from `xcrun simctl runtime list -j`. Deletion is async (shows "Deleting"). 17.5≈7.3G, 18.5≈8.8G.
- Orphan sim devices: `xcrun simctl delete unavailable` (did nothing on 2026-05-23 - no orphan devices, weight was in runtimes not devices).
- `~/Library/Caches/*` entries not in NEVER-TOUCH - all regenerate.
- Stale-project `node_modules` - `npm i` rebuilds.

## SCAN LOG

Cap: 5 entries max. When at cap, drop the entry with the earliest date field before appending; if dates tie, drop the topmost entry. Never reorder remaining entries.

- 2026-05-22: First scan. Free 2.1Gi (critical). 5 sim runtimes: 17.5, 18.5, 26.2, dup 26.4×2 ≈ 38G - top target. CoreSimulator 15G. Home Library 62G total. Caches: Google 2.8G, Spotify 1.9G.
