---
name: auto-respawn
description: Triggers on /auto-respawn only. Opts this Conductor chat into the 150k context-cap respawn note. For long-running listener chats.
disable-model-invocation: true
---

# /auto-respawn

> Opt THIS chat into Claude Conductor's context cap. Off by default for every chat.

## What invoking it does

Nothing runs here: the invocation itself is the switch. The Conductor daemon scans this chat's
transcript for a `Skill` call to `auto-respawn` (or the typed `/auto-respawn` command), and once
it finds one, every turn after the chat passes 150k tokens carries a "Context cap" note
(`claude_usage_in_taskbar/src-tauri/src/daemon/hooks_server/context_cap.rs`). Chats that never
ran this skill never see the note.

Use it only for long-running listener or hub chats (e.g. mc_plugins_tag's Player Claude) that
re-read a huge context on every wake. Never for an ordinary working chat: a respawn drops the
conversation, and Joe manages those chats' length himself.

## When the note arrives

1. Finish the request in hand. Never respawn mid-task.
2. Call the `respawn` MCP tool with a complete handoff prompt: everything the successor needs
   (state, open items, re-arm steps), since it cannot see this conversation.
3. The handoff prompt's first instruction must be to run `/auto-respawn` again. The opt-in
   lives in this chat's transcript, so the successor starts opted out until it runs the skill.

After invoking, reply with one line confirming the chat is opted in, and continue the task.
