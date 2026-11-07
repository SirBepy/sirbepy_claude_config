# /close Phase 3 steps 2-5: full procedure

Read on demand from `skills/close/SKILL.md` Phase 3 when a todo, screenshot count, digest or respawn file is in play. Step 1 (memory writes) stays in SKILL.md.

2. **`.claude/todos/`** Peer sweep first, conditional on concurrent sessions: before writing any
   `task` todo below, call `list_peers` once - the one unconditional call, cheap even solo. Phase 0
   and Phase 1 step 5 are the two sources that assert work is unstarted or unfinished, and a live
   peer may already have picked one up (todo 890: a `/handoff` todo called two Shortcut items
   unstarted while a peer had already fixed and shipped both). Zero peers: add nothing and write the
   todos below as-is - `list_peers` returning zero is a weak signal, not proof of solitude, it has
   undercounted a live peer in this repo before, so an empty sweep is never worded as "confirmed
   unstarted". One or more peers: also call `read_messages`, check whether a peer's session name or
   a recent message names the same ticket/file/feature as the item about to be filed, and where it
   does `post_message` to ask directly, folding the answer (or "asked, no reply yet") plus the
   sweep's timestamp into that todo's Notes instead of filing it as plain unstarted work.

   An item whose fix lives in a DIFFERENT repo (most often a finding about the global `~/.claude`
   tree surfaced from a project session) is filed into THAT repo's backlog, per root `CLAUDE.md`'s
   allocation rule. Follow `skills/create-todo/SKILL.md`'s "Cross-repo filing" flow rather than
   hand-rolling it: the destination gets the same content-duplicate guard, the same atomic id
   reservation, and the same `.git/info/exclude` self-heal a local file gets.

   Write a separate `.md` file per item from:
   - Phase 0 (unfinished items filed instead of finished: `--now`, an unattended chain, the size brake, or the wait cap) - tag `**Type:** task`,
     `**Origin:** dev` (the dev asked for it; Claude just didn't finish it in time).
   - Phase 1 step 5 (unfinished offers) - tag `**Type:** task`, `**Origin:** ai` (Claude proposed it
     unprompted and it never got executed).
   - Phase 1 steps 3-4 (repeated manual steps, skill rule violations) - tag `**Type:**
     skill-improvement`, `**Origin:** ai`, Approach section names the skill file involved.

   Follow `ai-todos-format.md` (this skill's folder) for everything: template (every todo gets a one-sentence `**Summary:**`, plus a `## Why` only when the session states the reason), filename/id rules (`<id>-<slug>.md`, id from `reserve-todo-id.ps1`, `pc-NNNN` form), git-policy self-heal. The bar: a future cold AI session must be able to execute the task from the file alone, without re-reading session history. Skip if no items. Note: Phase 2 review findings are written to the backlog by `/code-check` directly - do not re-write them here.
3. **Screenshot summary.** `/close` no longer deletes screenshots - todo 324 moved that to
   `/disk-doctor`, which ages folders out later while Joe decides. If Phase 0 recorded any
   screenshots captured this session, count the files under this session's own
   `.for_bepy/screenshots/<pid>-<start-ticks>/` subfolder (the Phase 0 id) for Phase 4's counter. 0
   if Phase 0's zero-writes flag was true. If that flag is FALSE (this session did capture
   screenshots) but the Phase-0 id's subfolder is missing or empty, that is an id mismatch (todo
   459: `-GetId` can still resolve to an id nobody wrote to), not a real zero - flag it as
   `mismatch` for Phase 4 instead of counting 0. Never substitute an mtime-matched folder here; the
   ownership proof is by subfolder name only (Phase 0), since a concurrent session's files can be
   newer or older. Nothing is printed or deleted here. If
   this session captured any screenshot via the Playwright MCP
   (`mcp__playwright__browser_take_screenshot`), also check the repo root and `.playwright-mcp/`
   for stray `.png` files - the MCP writes there directly and this summary cannot see them; report
   any found, never auto-delete, since they may be git-tracked. `.for_bepy/mockups/` and
   `mockup-step-*.json` are out of scope here too - `/mockup` step 7 owns their disposal.
4. **Session digest.** Skip a session with no decision or rejected option worth keeping (a pure
   mechanical run). Otherwise write this session's digest from the Phase 1 material, no extra
   model call: pipe `## Done`, `## Decided`, `## Rejected` (option plus the reason it lost) and
   `## Open` sections (write `none` under an empty one) to
   `python ~/.claude/skills/recall/recall.py digest-save <sessionId>`. Resolve `<sessionId>` with
   Transcript grounding step 1 even when the rest of grounding was skipped as a short session,
   since a short session can still hold a decision worth a digest. It refuses to overwrite an existing digest; never pass
   `--replace` here. Digests feed `recall.py decisions` (design: `refs/permanent-memory.md`).
5. **Inherited respawn detail file.** If this session's first user message is a `/respawn`
   handoff naming a `Detail file: <path>.respawn.md`, delete that file: it was written only for
   this chat (`skills/respawn/SKILL.md` Step 1). Skip silently when there is none or it is already
   gone. Under `/respawn` this runs too, because the new detail file it writes next supersedes it.
