<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=9c34c230 -->
<!-- duplicate-checked -->
# ui-screenshot-reminder passes once any screenshot exists, so later UI edits ship unseen

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the `ui-screenshot-reminder` Stop hook gate on "has a screenshot been taken **since the last
UI edit**", not "were any screenshots taken this session".

## Context

zng-app session, 2026-08-27. The hook fired correctly early on, I complied, and it never fired
again - so I handed Joe **two visibly broken builds in a row** later in the same session, both
caught by him rather than by me:

1. Step indicator clipped: it is a `Row` of `Column`s with the default `mainAxisSize.max`, so
   inside the app header it stretched to the bar height and pushed the progress bars off the top
   edge.
2. The same block sat in an `Expanded` between logo and controls, so it centred on the leftover
   space rather than on the bar, visibly off-centre.

His reaction: *"do you think this is good? cuz its not"*, and later *"you even messed this up"*.
One screenshot before either handover would have caught both. I took 21 screenshots that session,
just none after those particular edits - which is exactly why the hook stayed quiet.

The gap is the predicate. A session-wide "any screenshots?" check is satisfied forever by the
first capture, so the reminder is weakest late in a long UI session, which is when fatigue and
accumulated changes make it most needed.

## Approach

`~/.claude/hooks/` - the hook backing the `[ui-screenshot-reminder]` Stop message (grep the hooks
dir for that literal tag; it is wired in `settings.json` under `Stop`).

Change the predicate to compare timestamps rather than existence:

- newest mtime among UI-ish changed files (`.css`/`.scss`/`.less` plus whatever the current matcher
  treats as visual - in this session it was `.dart` UI files), versus
- newest mtime among `.png` files under `.for_bepy/screenshots/<pid>-<start-ticks>/`.

Fire when the newest UI edit is **newer** than the newest screenshot. That keeps the existing
zero-screenshot case firing and adds the "stale screenshot" case.

Watch for: a session that legitimately edits UI files after its final screenshot and is closing
anyway (e.g. a revert). Probably acceptable noise - the reminder is advisory - but consider a
grace window rather than a hard compare if it proves annoying in practice.

## Verify

- [ ] Make a UI edit, capture a screenshot, then make a second UI edit and end the turn - the hook
      MUST fire on the second.
- [ ] Same but with no second edit - it must stay quiet.
- [ ] Zero screenshots at all with a UI edit - must still fire (existing behaviour, no regression).

## Notes

Filed from a zng-app session per CLAUDE.md's rule that findings about the global `~/.claude` tree
belong in this backlog, not the surfacing project's. Not executed there - only filed.
- Done via /mega-todos batch 2, commit 7ce205a: the once-per-session one-shot marker is replaced by a stateless compare, the hook fires whenever the newest UI-ish changed file is newer than the newest screenshot, so a screenshot followed by further unshot UI edits fires again. .dart added to UI_EXTENSIONS, which the incident needed. Three integration cases added. The builder committed this then hit the session limit before reporting, so acceptance was verified from the tree by the orchestrator rather than from a builder report.
