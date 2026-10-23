<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1162 is split-hunks' -m handling and same-hunk double match; 1064/1085/1089/1124 are commit-pathspec/foreign-hunk surfaces; none covers git apply rejecting a later kept hunk -->
# split-hunks.py commit: "patch does not apply" on a later hunk of a multi-hunk file

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/split-hunks.py commit --hunk <path>:<substring>` applies a hunk that is not the file's first changed hunk without `git apply --cached` failing.

## Context

Hit twice on 2026-10-08 in mc_plugins_tag (session b5e3, core.autocrlf in effect, working copies LF, blobs LF):
- `--hunk dragonballs/src/main/resources/config.yml:ball-returned` (the 4th of 4 hunks; the earlier hunks deleted/added different line counts): `error: patch failed: dragonballs/src/main/resources/config.yml:286 ... patch does not apply`.
- `--hunk "docs/dragonballs.md:really is with whoever" --hunk "docs/dragonballs.md:1000-2000 blocks from where"` (2nd and 3rd of 3 hunks, 1st was a peer's): `patch failed: docs/dragonballs.md:90`.
- Third hit 2026-10-11 (session 3ae6, commit 323aed2): `--hunk "market/src/main/java/dev/sirbepy/mc/market/MarketPlugin.java:MarketPriceCommand"`, the 2nd of 2 hunks (1st was a peer's +5-line insert at -77,6), a pure 1-line insert `@@ -141,6 +146,7 @@`: `patch failed: ...MarketPlugin.java:141`. So it fails even when the dropped hunk is an insert-only and the kept one has untouched context; same blob-by-hand workaround landed it.
- Fourth hit 2026-10-18 in claude_usage_in_taskbar (session aadf): `--hunk src-tauri/src/daemon/boot.rs:browser` where hunk 2 of 4 (a peer's 1-line insert at `@@ -113,6 +113,7 @@`) was skipped: `patch failed: src-tauri/src/daemon/boot.rs:294` on the last kept hunk (`@@ -294,5 +306,6 @@`, pure 1-line insert). **The blob-by-hand workaround is no longer available:** auto-mode's classifier denied it as `[Auto-Mode Bypass]` of the commit procedure, so with this bug the only remaining routes are waiting for the peer to commit or taking the file whole. That raises this todo's priority.
- Fifth and sixth hits 2026-10-18 in claude_usage_in_taskbar (session bc97): `--hunk src-tauri/src/daemon/remote_transport_table.rs:set_machine_can_drive` (3rd of 3 hunks, the first two a peer's inserts) failed `patch failed: ...remote_transport_table.rs:543`; `--hunk "README.md:**App lock.**" --hunk "README.md:What a paired machine may do"` (2nd and 3rd of 3, the 1st a peer's) failed `patch failed: README.md:161`. Both match the dropped-earlier-hunk shape above. The blob-by-hand workaround (HEAD blob + wanted paragraphs, private index, `commit-tree`, CAS `update-ref`) was NOT denied this time and landed c2ff5a10.
- Same session: the docstring's usage line `split-hunks.py commit ... [--repo <dir>]` is wrong, argparse only accepts `--repo` BEFORE the subcommand (`split-hunks.py --repo . commit ...`); after it fails with `unrecognized arguments: --repo .`. Fix the docstring (or accept it in both positions) alongside the patch fix.

Seventh hit 2026-10-22 in mc_plugins_tag (session 2e4a): `--hunk .../MinibossesPlugin.java:ChroniclerGuardListener`, kept hunks 2 and 4 of 4 (the last hunk of the file), `patch failed: ...MinibossesPlugin.java:211`. CAUSE FOUND AND VERIFIED (a wrapper that fixed it and landed a6c3d69): `git apply -v` printed the searched old side ending in a BLANK line; `split_file_sections` splits the diff on `\n`, leaving a trailing `b""` element, and `build_patch` re-joins it with `b"\n"` and appends another `\n`, so the patch ends with an empty line that `--recount` counts as one extra context line the file does not have there. It only bites when the kept set includes the file's final hunk (matches hits 2-6 above). Dropping trailing `b""` entries from the filtered line list fixed it. Renumbering the `+c` header start (also tried) was NOT needed. Fix in `filter_hunks` / `build_patch`: strip trailing empty elements before the final join.

UNVERIFIED cause (superseded by the verified one above): the filtered patch keeps each kept hunk's original `@@ -a,b +c,d @@` header, and when an earlier hunk is dropped the old-side start no longer lines up for `git apply --recount`, or the context lines carry the dropped hunk's changes. Workaround used: build the blob by hand (HEAD content + the wanted hunks), `hash-object -w`, private-index `update-index --cacheinfo`, `write-tree`, `commit-tree`, CAS `update-ref`.

## Approach

Reproduce in a scratch repo: a file with 3 hunks where the first changes the line count, then `split-hunks.py commit --hunk file:<text from hunk 3>`. Inspect the generated patch. Likely fix: recompute the kept hunks' headers (old-side start from HEAD, new-side start shifted only by kept hunks) before `git apply --cached`. Add a case to the script's tests if it has any.

## Acceptance

- The scratch repro commits only hunk 3, and `git show` matches it exactly.
- A 2-of-3-hunks case (skipping the first) also commits cleanly.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): split_file_sections drops the trailing empty element so a kept final hunk applies; usage docstring puts --repo before the subcommand. Final-hunk and 2-of-3 tests RED then GREEN.
