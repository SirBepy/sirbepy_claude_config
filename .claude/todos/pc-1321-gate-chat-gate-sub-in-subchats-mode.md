<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard's hits share only the words gate, chat and push. pc-1294 is the close skill's started signal, and pc-1288 is already out of the backlog. None covers spawning the gate as a hidden sub. -->
# /gate-chat runs a push's gate as a hidden gate sub in a "Use subchats" chat

**Type:** skill-improvement
**Origin:** dev
**Summary:** A chat with "Use subchats" on should hand its push gate to a hidden sub with `gate: true`, instead of a visible gate chat, and today's skill gets refused there.

## Why

Joe, 2026-11-04: "i think the gate chat would be a subchat, why bother making the main chat do it?". Spec: `claude_usage_in_taskbar` todo pc-1597, section 2. Claude Conductor shipped the daemon side in commits 2e471112 and 170b721a on that repo's master.

## Context

`spawn_chat` from a mode-on chat refuses a call with no `task`, `goal`, `done_when` and `writes`, with an error that names `gate: true`. So `skills/gate-chat/SKILL.md` step 2 fails there until this lands. The refusal is safe, not silent.

`gate: true` is valid only from a mode-on main chat. It skips the brief check, requires `prompt` (which becomes the sub's first message word for word), defaults to Sonnet high, and refuses a second gate for the same parent while one runs. The gate sub gets its own prompt, and its `close_session` is refused naming `finish_subchat`, so a trailing `/close` in the prompt is harmless and the prompt does not need to change.

## Approach

From the builder's report, not re-read by the filer:

1. `skills/gate-chat/SKILL.md` step 2: a mode-on chat has "Subchats mode is ON for this chat" in its system prompt, with no later "Subchats mode is now OFF" note. In that case add `gate: true` to the `spawn_chat` call. Keep `cwd`, `name`, `model`, `effort` and the prompt exactly as today.
2. Step 3's wording: the gate runs as a hidden sub, its questions show in this chat, and its card says whether it pushed.
3. The 30% context threshold in `gate-chat`'s intro and in `/commit`'s step 1c ("Gate hand-off") should not apply to a mode-on chat: gate sub always, per the spec. Unattended runs still gate in place.

Then check `skills/release/SKILL.md` for the same hand-off.

## Done when

A `/commit push` from a mode-on chat in a Conductor build that has the feature runs its gate in a hidden sub, with no visible new chat, and a chat with the mode off behaves as today.
