<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-0450 (code-check after writing, not at close) and pc-1280 (slim the commit and close skill text) touch parts of this; this todo is the whole redesign and should absorb or close them -->
# Redesign /close: move each of its jobs to the moment it belongs, then shrink or remove the skill

**Type:** skill-improvement
**Origin:** dev
**Summary:** Inventory everything /close does, decide for each job when it should really happen (as it happens, at a commit, at a sub's finish, when a chat ends, by the app), and rebuild or remove /close accordingly, with Joe deciding the design.

## Why

Joe, 2026-11-12, in the Conductor forever-chat work (main chat a6b0b8fa in claude_usage_in_taskbar), answering whether old finished subs should be closed automatically: "Yeah but I was more so talking about using the closing skills so that everything that needs to be remembered from that chat is remembered. But I guess maybe that's already done. Maybe we should even just completely remove the closed skill, but everything that we benefit from it gets applied in a better way. What do you think? I think it's time maybe for us to redo that skill and how it works and all the things that it does should likely be done at a different point in time"

## Goal

Nothing a chat learns or leaves behind depends on someone remembering to run /close, and long-lived Conductor main chats (which never close, rule 5 of `SUBCHATS_MAIN_PROMPT`) and subs (which end with `finish_subchat`, never /close) lose nothing.

## Context

- Conductor already moved some /close work elsewhere for its own chats (read in that repo on 2026-11-12): a sub's finish writes `<data_dir>/subchats/<sub>.digest.md` with Done / Decided / Rejected / Open (`src-tauri/src/daemon/subchats/decisions.rs:622-664`, deliberately NOT into `~/.claude/memory-archive/digests`; nothing reads it yet); a main chat writes a retro at close (`daemon/subchats/retro.rs`); rule 6 of the main prompt sends lasting facts to Auto Memory at the end of each piece of work; the push pipeline runs review and code-check.
- In Conductor a main chat is meant to live for weeks and is compacted in place (`claude_usage_in_taskbar/docs/forever-chat-plan.md`), so an end-of-chat step may never run for it.
- UNVERIFIED: the full list of what /close does today. Step 1 below reads `skills/close/SKILL.md` and its sidecars to build it.

## Approach

1. Inventory: read `skills/close/SKILL.md` and every sidecar it points to; list each job (retrospect, review, memory and vault writes, digest, todos, screenshots and scratch cleanup, orphan processes, session rename, the finish-open-work step) with what triggers it today.
2. For each job, propose the moment it belongs: as it happens (memory on confirm, todo on deferral), at a commit or push (review, code-check), at a Conductor sub's finish (digest, decisions), by the app when a chat ends (process and scratch cleanup, which a daemon can do with no model turn), or still at an explicit end. Note which already happen elsewhere.
3. Show Joe a before/after table on a question card and settle it; then rebuild /close as the thin remainder, or remove it, and update every skill and CLAUDE.md line that tells a chat to run /close (Conductor's subs and main chat prompts included).
4. Fold in or close pc-0450 and pc-1280.

## Decided (Joe, question card, 2026-11-12)

- "Spread jobs, delete /close now" (over keeping a 20-line /close, and over only adding the save step).
- `finish_subchat` requires a `learned` list (over a prompt-only rule, and over nothing).

## Notes

- 2026-11-12, built in `~/.claude` (master, not pushed): 88bbdb1 shared scripts moved to `tools/` and `refs/`; 5c9327e `recall.py digest-save --merge`; f20fdcb the save step in /commit, /respawn, /handoff, /one-off; b62c6c8 skill deleted, CLAUDE.md and process-hygiene rule, CI tombstone; 58c061a push gate runs the dead test-selector check, a gate chat ends with `close_session`; 7cc1426 remaining callers; ddd439f review fixes. `python ci/run_all.py`: all 9 checks passed after 7cc1426.
- Built in Conductor on branch `close-removal` (worktree `C:\Users\tecno\cargo-scratch\wt-close-removal`), rebased onto master on 2026-11-12, six commits, tip 0e83f601: `learned` on `finish_subchat`, the /close-only daemon and UI machinery removed, the main-chat digest written from the decisions log, review fixes. NOT merged yet: the main checkout had an uncommitted edit to `daemon/claude_config/args.rs`, which the branch also changes, so `merge --ff-only` would be refused.
- Calls made without asking, each reported to Joe: /respawn no longer runs /code-check (review lives at the push gate, per the approved table; this overrides his 2026-10-08 "respawn should always also do /code-check"); the sub card's Close and the /pickup button close through the app with no model turn; `rename-session` lost `-Close` and `-Force`.
- Known gaps filed: pc-1366 (the screenshot reminder hook does not check that a frame reached Joe). Conductor backlog: pc-1732 (a UI close of an unfinished sub skips `end_sub`).
- The compaction-time save step and retro for a forever main chat are a requirement added to `docs/forever-chat-plan.md` B1 on the branch, not built here.
- pc-0450 closed as superseded; pc-1280 and pc-1342 keep only their /commit halves.
- 2026-11-12 21:58: the Conductor branch close-removal was rebased onto master (after VERSION 0.2.150), re-verified (cargo module tests, tsc, 4103 vitest tests, css-vars, view-spec coverage) and fast-forwarded into Conductor master at f61067fe. Not pushed, not released: the app half takes effect with the next Conductor /release. The worktree, both branches and the scratch cargo target are removed.
