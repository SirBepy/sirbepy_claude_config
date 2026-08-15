<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=8, reconfirm-count=1, content-hash=eb287229 -->
# /close should stop deleting screenshots; /disk-doctor owns cleanup by age

**Type:** skill-improvement
**Origin:** dev

## Goal

Take screenshot deletion away from `/close` entirely, keep the per-session subfolder as a
permanent organizing convention (one folder per chat), and let `/disk-doctor` be the thing that
reclaims the space later, on age.

## Context

Joe's call, 2026-08-13, in a zng-biller session. Two separate decisions:

1. **`/close` stops deleting screenshots.** Today `close/SKILL.md` Phase 0 resolves the session's
   `<pid>-<procStart-ticks>` id specifically so Phase 3 step 3 can purge that subfolder, and Phase 4
   reports "N screenshots cleaned". Joe does not want the close of a chat to destroy its own visual
   record - a screenshot is often the only artifact showing what a change looked like, and it is
   gone before he ever looks at the folder.
2. **The per-session segmentation stays, and gets a better reason to exist.** He explicitly likes
   one folder per chat. Its purpose changes from "lets /close prove ownership before deleting" to
   "keeps the pile browsable and gives /disk-doctor a clean unit to age out".

`/disk-doctor` is the right owner because it is already the repeatable disk-reclaim scan and it is
already advise-only - it reports what to delete and Joe deletes. That matches how he wants
screenshots handled: nothing disappears without him.

**Do not rebuild the session-folder mechanism - it already exists.** `skills/screenshot/session-shot-dir.cjs`
computes and creates the per-session dir, and `screenshot-helper.cjs`'s `resolveScreenshotPath()`
auto-resolves a bare filename into it and throws if a caller targets the screenshots root
(shipped via done/300). `close/rename-session.ps1 -GetId` resolves the id itself, via
`$env:CLAUDE_CODE_SESSION_ID` matched against `~\.claude\sessions\*.json`, NOT a process-tree walk
(done/60 - the walk resolved to two different PIDs inside one session).

Note `close/SKILL.md` exists as two byte-identical copies, `~/.claude/skills/close/` and
`~/.claude-personal/skills/close/`. Whichever is authoritative, both need the same edit or they
drift.

## Approach

**`/close`:**
- Delete Phase 3 step 3's purge. Do not soften it to a prompt - Joe wants no deletion path there.
- Phase 4's counter line drops the "N screenshots cleaned (M legacy at root, P other-session
  subfolders, both untouched)" segment, or becomes a plain "N screenshots written to <dir>" so the
  folder is still discoverable.
- Phase 0 still resolves the id: the writing side (put shots in the right subfolder) is unaffected
  and still wanted. Only the deleting side goes.
- Check `close/light.md` for its own copy of the purge step before declaring this done.

**`/disk-doctor`:**
- Add `.for_bepy/screenshots/` across all projects to its scan scope. Report per-project totals and
  per-subfolder size plus age, oldest first.
- Age is the axis, not ownership: with `/close` no longer deleting, an old subfolder is just old,
  regardless of which session wrote it. Loose root-level files (the pre-convention legacy pile,
  ~40 in zng-app alone) are in scope too, on the same age rule.
- Stay advise-only, as the skill already is. It reports; Joe deletes.
- Suggest a default age threshold in the report rather than hardcoding a silent one.

**Consumer follow-on, folded in here:** `zng-biller/scripts/screenshot-dev.js` still defaults
`--out` to whatever the caller passes and lands files loose at the screenshots root. That was
zng-biller todo 74, relocated into this file on 2026-08-13 and archived there, so this is the only
live record of it. If the shared helper can be reached from a plain Node script in a repo with no
Node dependencies of its own, it is a one-liner; if not, a `--session-dir <id>` flag is the
fallback. Any other project with a hand-rolled screenshot script has the same gap.

## Acceptance

- `/close` on a session that took screenshots deletes nothing, and says so plainly in Phase 4.
- No purge step remains in `close/SKILL.md` or `close/light.md` (grep for "screenshots cleaned").
- `/disk-doctor` reports screenshot folders with size and age, oldest first, across projects.
- Screenshots still land in `.for_bepy/screenshots/<pid>-<start-ticks>/` - the writing convention is
  untouched by this change.

## Notes

- Global `CLAUDE.md`'s UI & visual changes section currently justifies the subfolder with "This lets
  `/close` prove ownership by subfolder and delete only its own session's shots". That sentence has
  to change with this todo, or the rule's stated reason will contradict the shipped behavior.
- Related history worth not re-litigating: done/54 and done/300 built the enforcement so `/close`
  COULD purge. This todo keeps their machinery and removes only the purge itself.
- Fresh evidence that the helper is still bypassable, from the zng-biller session that filed this
  (2026-08-13): the screenshots went to `.for_bepy/screenshots/47728-639222354951061910/`,
  hand-computed from a process-tree walk, while `rename-session.ps1 -GetId` returned
  `43272-134311293074945700` for the same session. Two different ids, so a canonical purge would
  never have matched that folder. The session drove a hand-rolled Node script and simply never went
  through `session-shot-dir.cjs`. It is harmless once `/close` stops deleting, but it is the reason
  `/disk-doctor` must age out ANY subfolder shape it finds, not only well-formed ids.
