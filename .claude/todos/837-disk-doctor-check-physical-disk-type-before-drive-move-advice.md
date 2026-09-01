<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=1, content-hash=03297047 -->
<!-- duplicate-checked: grepped .claude/todos/ and done/ for MediaType/PhysicalDisk/HDD/SSD, no hits -->
# disk-doctor should check physical disk type before recommending a cross-drive move

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a step to `skills/disk-doctor/windows.md` (and `macos.md` if it gains an equivalent) requiring
Claude to check each involved drive's physical media type (SSD vs HDD) BEFORE recommending moving
anything between drives - not just before/after a same-drive delete.

## Context

2026-08-29 disk-doctor session: after the routine C: scan, Joe asked what could move to D: to free
up C:. Claude recommended moving the Steam library to D: as a "zero risk" win without checking what
kind of drive D: actually is. Joe asked "are you sure that doesn't slow anything down?" - only then
did Claude run `Get-PhysicalDisk` + `Get-Partition -DriveLetter C/D` and discover C: is an NVMe SSD
(Samsung 980 1TB) and D: is a spinning HDD (Toshiba HDWD110). That materially changes the advice
(HDD load-time/streaming-stutter tradeoff, disk contention with `D:\cargo-target` builds already
living there) and had to be corrected after the fact instead of stated correctly the first time.

This is the same class of gap CLAUDE.md's "verify before asserting" rule already names generally
(read the system before claiming something about it) - disk-doctor just never had its own concrete
trigger for the cross-drive-move case specifically, only for scan/delete claims.

Confirmed fact worth reusing: the vault note `Dev machine storage.md` (written this session) now
records C:/D:'s physical types, so a future session doesn't need to re-run the disk query - just
read that note first, and only re-verify if it looks stale or a new drive is involved.

## Approach

1. In `windows.md`, add a short rule near the "Output rules" section (or wherever cross-drive
   suggestions get made): before suggesting moving anything to/from a drive letter not yet
   characterized this session, check the vault note `Dev machine storage.md` first; if that drive
   isn't in it yet, run `Get-PhysicalDisk | Select DeviceId, FriendlyName, MediaType` +
   `Get-Partition -DriveLetter <X>` to map it, then update the vault note.
2. Name the concrete tradeoffs to state once media type is known: HDD load-time increase, HDD
   mid-play streaming stutter/pop-in risk for asset-heavy titles, disk contention with anything else
   already writing to that same physical disk (e.g. build caches), audible seek noise. SSD-to-SSD
   moves need none of this caveat.
3. Keep the check cheap - this is two fast PowerShell calls, not a scan-scale operation; no subagent
   dispatch needed for it.

## Acceptance

- [ ] `windows.md` names the check explicitly, not just implied by the general CLAUDE.md rule
- [ ] The rule points at `Dev machine storage.md` as the cache to check first
- [ ] Wording distinguishes "same physical disk, different partition" from "different physical
      disk" - the risk only applies to the latter

## Notes

- Distinct from todo 835 (delete-confirmation gate has no mechanical enforcement) - that's about
  destructive actions lacking a hook backstop; this is about advisory accuracy on a non-destructive
  recommendation, caught by Joe's question rather than any gate.
