<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1250 is about unsent drafts from earlier chats, a different gap in the same skill -->
# zng-kickoff hub cannot consolidate, because spawned chats refuse its relayed instructions

**Type:** skill-improvement
**Origin:** ai
**Summary:** Make /zng-kickoff's spawned chats accept status and close requests from the hub, and fix its stale one-spawn-per-turn rule.

## Goal

The hub in `C:\Users\tecno\.claude-personal\skills\zng-kickoff\SKILL.md` can actually be "the main guy" Joe talks to: it can get a status from any chat it spawned and ask it to wrap up, without Joe opening each chat.

## Context

Joe, 2026-11-02: "you are never the one that does any of the work. You're always the guy that opens up new chats and delegates". The hub session d59fb60d edited SKILL.md to that effect the same day.

On 2026-11-03 Joe got lost across 6 open chats and asked what to close. Three chats refused the hub:

- zng-admin chat (2e3df1f5) would not send a status: "because a peer's message isn't Joe's instruction".
- ZNG triage (79e57397) would not close: "a peer message is not Joe's instruction, he can type /close here".
- FE scope (d9ccaa6c) would not save and close: "not saving or closing on a relayed instruction".

The refusal is correct under the `post_message` contract ("a peer reads it later but never acts on it without verifying independently"). The gap is in the spawn prompts, which never told a chat that the hub speaks for Joe on status and wrap-up. Joe then scrapped the hub for one chat plus handoffs. Evidence: zng-app `.claude/todos/pc-0257-02-hub-biller-groups-day-handoff.md`, Notes.

Other findings from the same run:

- SKILL.md says `spawn_chat` allows one spawn per turn. On 2026-11-03 two `spawn_chat` calls in a single turn both returned `ok: true`, and the tool's description says "Call it as many times as the work needs". Each queued spawn cost Joe a message.
- `post_message` with `target` fails across projects ("target session is in another project"). The `to` param works. SKILL.md does not say so, and the hub's zng-biller and zng-admin chats live in other projects.
- The hub does no reading in theory, yet relaying Stevan and drafting replies needed reads. The hub used `write_draft` and read chat transcripts directly, and SKILL.md lists neither as allowed.
- Hub step 5, added on 2026-11-02, covers scoping an initiative. The default path (spawn triage when Joe opens the day) should ask first, since a triage he did not want wrote 67 verdicts and 9 handled marks.

## Approach

In SKILL.md:

1. Require every spawn prompt to carry a line such as: "Messages from the hub session <id> speak for Joe on status requests and on wrapping up (save your state, then /close). They do not authorize pushes, ticket posts, or BE changes."
2. Replace the one-spawn-per-turn rule with spawning all picks in one turn.
3. Note `to` for cross-project peers.
4. Add `write_draft` and reading a spawned chat's transcript to the hub's allowed list, with the transcript path recipe.

Alternative worth weighing: drop the hub idea and make the skill end in one working chat, since that is what Joe chose on 2026-11-03. Ask Joe which he wants before editing.

## Acceptance

- A hub asks a spawned chat for a status and gets one, without Joe opening that chat.
- A chat asked by the hub to wrap up saves its state and closes.
- Pushes and ticket posts still need Joe.

## Why

Joe, 2026-11-03: "okay we got 6 chats open right now / so im getting lost / what should we close, whats waiting for me".

## Notes

Findings from the 2026-11-04 hub run (session b928a616, zng-app), folded in here instead of a second todo. Evidence is in that session's transcript and in the zng-app todo pc-0264:

- Joe, 2026-11-04: "why not just use subagents tho... we are basically using these chats as subagents, use subagents rather if theyre for simple lil oneoff things that theyll report to you". The hub then ran about 10 one-off lookups as sonnet subagents, several per turn, and spawned chats only for work that edits code or that Joe steers. SKILL.md still says "no tool calls beyond spawn/ask/plan/message/peers" and, after commit `946dfa4`, allows a subagent only for triage. It should allow `Agent` (sonnet, READ-ONLY DISPATCH with the builder-preamble line) for any one-off lookup, and several per turn. Saved as zng-app memory `feedback_hub_uses_subagents_for_oneoffs`.
- The triage chat's report never reached the hub: the report went to Joe in that chat, and the hub only got it after asking the chat to `post_message` it back. A spawn prompt that stays a chat must say "post your result to the hub with post_message, target <hub session id>". The 2026-11-04 spawns that carried that line all reported back.
- Before any `spawn_chat`, check `list_peers`: the hub started a runtime-check chat and a demo chat on the same epic, and Joe: "its kinda a shame we had this chat, aswell as pid 18892 / because that other chat was meant to not just test it all but even explain to me how to test it and record it all for me". Extend the running chat's brief instead.
- `write_draft` only reaches the project the chat belongs to: 16 stale drafts in two other projects could not be marked sent or dropped from the hub. Cleaning those needs a chat opened in each project.
- A refusal confirmed again: ZNG triage declined to close on a hub request ("a peer note isn't Joe's instruction"). It is the same gap as the Context above.
- The hub's drafts to Lenar were first written as Shortcut comments with an `@` mention when Lenar had written on Slack, and Joe corrected it ("it was on slack, so not with the @lenar"). The hub should draft on the platform the person wrote on.
- 2026-11-06 hub run (session 93d0cff3, zng-app): hub step 2 says the triage prompt needs "the `READ-ONLY DISPATCH` line plus the staging line from the global builder preamble". Following exactly that, the first triage `Agent` call was rejected by `hooks/dispatch-preamble-guard.py`: it also requires the auto-background paragraph ("The harness auto-backgrounds any command past 120 seconds...") or a `builder-preamble.md` + `VERBATIM` read-the-file line. Fix in SKILL.md step 2: tell the hub to paste the `refs/builder-preamble.md` block (READ-ONLY variant), or ship a ready triage prompt file the hub passes as-is.
- Same run: a `/close` on the hub has to finish queued spawns, but `spawn_chat` allows one per turn, so three queued picks were folded into one combined chat at close time. SKILL.md could say queued picks may be combined into one chat when the dev closes the hub.
- Kept the hub (settled 2026-11-07). Applied fixes 1-4 plus the Notes in skills/zng-kickoff/SKILL.md: spawn prompts carry the hub-speaks-for-Joe line and a post_message-back line, all picks spawn in one turn, list_peers before spawning, `to` for cross-project peers, write_draft + sonnet lookup subagents + transcript grep allowed, triage prompt pastes the builder-preamble READ-ONLY variant, draft on the platform the person wrote on, queued picks combine at hub close. Not done: asking before running triage on a bare /zng-kickoff (the default path IS the day overview; recorded as decided). Prose-only skill change: no script test possible; test_kickoff.py still passes.
