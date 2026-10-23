<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1186 and 1201 cover feed lag and probe headers, not a handled-ticket record or relocation -->
# /shortcut-priorities: remember tickets already handled, and move the skill under Zirtue scope

**Type:** skill-improvement
**Origin:** dev

## Goal

Two outcomes for `skills/shortcut-priorities/SKILL.md`:

1. Re-runs stop re-flagging tickets Joe and Claude already decided on in an earlier run.
2. The skill lives where the other Zirtue-only skills live, not in the global skill set, because its constants (Joe's Shortcut UUID, the ZNG repo paths, the Zirtue workspace tenant ids) are Zirtue-specific.

## Context

Raised 2026-10-20 in a zng-app chat running `/shortcut-priorities` over a 48h window. After the report, Joe and Claude spent the follow-up turns re-deciding items: sc-56414 and sc-56117 needed no reply (Joe had already answered), sc-56344 was waiting on Johanna, sc-56410 needed at most an optional one-liner. None of that verdict is saved anywhere, so the next run would flag all of them again. Joe's words: "we should start keeping track of what me and you already talked about in these shortcut priorities chats."

Joe chose a record kept with the global skill (not project memory, not chat-only) and said the skill itself should move under Zirtue scope. He wants to review "what else should move" in the zng-app chat, so the move is NOT yet decided in detail: the existing zirtue-scoped skill locations are UNVERIFIED here, check `skills/` for how `do`, `framer` and `verify` (the Zirtue-flavoured entries in the skill list) are placed before choosing a destination.

Existing live todos on the same skill, different subjects: 1186 (misses workable tickets, feed lag) and 1201 (activity probe missing browser headers). Read both first and keep edits to SKILL.md consistent with them.

## Approach

1. Decide the relocation target by looking at how the other Zirtue-scoped skills are laid out. Ask Joe if there is more than one plausible home.
2. Add a decisions file next to the skill (one line per ticket: id, date, verdict such as `no reply needed`, `waiting on <person>`, `owned by <person>`, plus a one-line reason). A file the skill reads, never a place Joe's session cookie or token goes.
3. In the flow, after step 4 (candidate filter) and before ranking: read the file, and for each candidate whose recorded verdict is still valid, show it under an "already handled" line instead of a ranked entry. A recorded verdict expires when a NEW comment from someone else lands after its date, or the ticket's workflow state changes; both are visible from the story JSON the skill already fetches.
4. After the report, the skill appends verdicts only for decisions Joe confirmed in chat, never for its own guesses.
5. Rejected: storing verdicts as zng-app Auto Memory. The skill would not read them automatically.

## Acceptance

- Re-running the skill over the same window lists sc-56414 and sc-56117 under "already handled", not as action items.
- A new comment from someone else on a recorded ticket brings it back into the ranking.
- The skill still never posts a comment or changes ticket state.
- The skill file passes the existing report-only rules; no cookie or token in the decisions file.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [ARCH] You said you want to review in the zng-app chat what else should move under Zirtue. Where does shortcut-priorities live: move to `zng-app/.claude/skills/` next to do/framer/verify / keep it global and only add the decisions file / another home you name.

## Notes

- The decisions file must be re-read before every write, since several chats can run the skill at once.
