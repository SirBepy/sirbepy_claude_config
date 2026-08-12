<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=5a7ab2be -->
# disk-doctor: document Docker Desktop's WSL2 VHD does not shrink via the "obvious" fix

**Type:** skill-improvement

## Goal

Record what was tried and what didn't work when Docker Desktop's LocalAppData footprint (`docker_data.vhdx`, found at 26.54G/26.4G) stays large even after `docker system prune -a` - so a future session doesn't re-attempt the same dead ends.

## Context

2026-08-05 session tried, in order:
1. `docker system prune -a -f` - freed space *inside* the container filesystem, did not shrink the VHDX file on disk (expected, documented Docker behavior).
2. `wsl --shutdown` + `diskpart` (`select vdisk` / `attach vdisk readonly` / `compact vdisk` / `detach vdisk`) - reclaimed **0 bytes**. Diskpart's compact only reclaims space the filesystem inside has explicitly TRIMmed; a plain shutdown+compact with no trim step did nothing.
3. `wsl -d docker-desktop -- fstrim -av` - trimmed only 40MiB. Wrong target: `docker_data.vhdx` (26.4G) isn't mounted as `/` inside the `docker-desktop` WSL distro - it only gets mounted by `dockerd` itself when Docker Desktop's backend is actually running, which had just been quit to attempt the compaction. Chicken-and-egg: can't reach the disk to trim it while Docker Desktop is stopped, but compacting requires Docker Desktop stopped to release the file lock.
4. The one operation that WOULD actually reclaim the space - fully deleting `docker_data.vhdx` and letting Docker Desktop recreate a fresh minimal one on next launch - was correctly NOT attempted, because it destroys any named Docker volumes (e.g. a dev database) that `docker system prune -a` doesn't touch by default, and no volumes-check had been done first. Joe explicitly declined pursuing this further on 2026-08-05 ("leave docker alone, im scared we fuck smth up").

## Approach

Add to `windows.md`'s KNOWN-SAFE or a new "known-hard" section:

> Docker Desktop's `docker_data.vhdx` (LocalAppData\Docker\wsl\disk\) does NOT shrink via `docker system prune` alone, nor via `wsl --shutdown` + `diskpart compact vdisk` alone (0 bytes reclaimed in practice - no TRIM occurred). The disk only mounts while `dockerd` itself is running, so `fstrim` from an external WSL distro can't reach it once Docker Desktop is stopped. The only operation that reliably reclaims the space is deleting the VHDX and letting Docker Desktop recreate it fresh - but this destroys any named Docker volumes not already checked for. Treat as a judgment call requiring an explicit volumes-check (`docker volume ls` + confirm none hold real data) before ever proposing the delete-and-recreate path, never a routine "safe" cleanup step.

## Acceptance

- Future sessions don't re-attempt steps 2-3 above expecting a different result.
- The delete-and-recreate path is only ever proposed alongside an explicit volumes-check, never bundled into a "just compact it" recommendation.

## Notes

Joe's standing answer on this specific item as of 2026-08-05: leave Docker's VHD alone entirely, does not want it revisited unless he brings it up again.

- 2026-08-08: Added new "KNOWN HARD (judgment call, not a routine safe-delete)" section between KNOWN SAFE-TO-DELETE and SCAN LOG (~line 148) with the VHDX gotcha.
