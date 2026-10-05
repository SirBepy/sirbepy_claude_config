<!-- duplicate-checked: 924 (done/) auto-derived the --own ranges from `git diff HEAD`; this is the follow-on failure that derivation created. 806 (done/) shipped the comparison script itself. -->
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# commit-pathspec.sh's foreign-hunk-check refuses as UNVERIFIED on every commit whenever other sessions are live, so every commit gets `--force foreign-hunk`

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/commit-pathspec.sh` distinguishes "a peer session is active in THIS repo" from "other Claude sessions exist on this machine", so a solo-repo commit does not refuse with a check the caller then overrides mechanically, which is what the override was never meant to become.

## Context

Head Soccer autopilot session 25f6b576 on 2026-09-11 made 27 commits. From the sixth commit on, every `commit-pathspec.sh` call refused with `[foreign-hunk-check] UNVERIFIED, refusing (4 live session markers - a shared checkout means an auto-derived own-range cannot prove absence of a foreign hunk ...)` and was rerun with `--force foreign-hunk` (24 overrides in one run). `list_peers` returned zero peers for the repo every time; the "4 live session markers" were `hooks/.session-markers/` files from unrelated Conductor chats in other repos (countoff, hubbub and similar). The auto-derived own-range path from todo 924 treats ANY live marker as "shared checkout", but a session marker is keyed by session id, not by repo, so it cannot say which repo a session is in. Net effect: the check is noise on a solo repo and its override became reflexive, the failure mode the SKILL.md prose ("never `--force` past reflexively") warns about. `--force coverage` was also needed on most commits because concurrent builders in the same session stage sibling files; that one is a legitimate judgment each time and is fine.

## Approach

1. In `commit-pathspec.sh`'s UNVERIFIED branch, count only markers whose recorded cwd (if the marker or `~/.claude/sessions/*.json` carries one) matches the target repo; sessions in other repos cannot hold hunks in this tree. If markers carry no cwd, join through `~/.claude/sessions/*.json` (`pid`, `sessionId`, `cwd`) the same way `close/rename-session.ps1 -GetId` resolves a session.
2. When zero same-repo markers remain, treat the auto-derived own-range as verified and print `[foreign-hunk-check] clean (no live session in this repo)`.
3. Keep the refusal for a genuinely shared checkout, and add a self-test in `hooks/test_*.py` or `ci/` that fakes two markers (one same-cwd, one other-cwd) and asserts only the same-cwd one triggers the refusal.

## Acceptance

- On a repo with no other live session in its cwd, `commit-pathspec.sh` commits without `--force foreign-hunk` while unrelated sessions are live elsewhere.
- The self-test covers both marker cases; `python ci/run_all.py` green.

## Notes

Recurred 2026-09-26 in `C:\Users\tecno\Desktop\Projects\roblox-trend-pipeline` during an
`/auto-do-todos` run: **6** live session markers this time, `list_peers` returning `[]` for the repo
every time, all three commits refused on the first call. Same mechanism, so nothing new to diagnose.
Folded in here per the contract rather than filed as a second todo.

One useful difference from the Head Soccer run recorded above: that session reached for
`--force foreign-hunk` 24 times, this one declared `--own-range <file>:<a>-<b>` per file instead,
which the script documents as ALWAYS trusted. That path keeps the check real rather than switching it
off, and the ranges were already printed by the refusal's own `[own-range] derivation:` block, so
copying them back in cost one extra call per commit and no judgement. Worth naming in the fix: until
step 1 lands, `--own-range` is the correct workaround and `--force foreign-hunk` is not, and the
SKILL.md prose could say so. That is also a second instance of the pattern todo
`989-commit-pathspec-refuses-then-prints-the-answer-it-refused-for` already describes.

