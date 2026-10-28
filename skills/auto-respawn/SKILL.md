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
2. Run `/respawn lite`: read `~/.claude/skills/respawn/SKILL.md` and follow its Lite mode (it
   cannot be invoked through the Skill tool). Put this chat's re-arm steps and open items under
   its **Next steps**.
3. The handoff prompt's FIRST characters must be the literal line `/auto-respawn`, with the Lite
   prompt underneath. The opt-in lives in this chat's transcript, so the successor starts opted
   out, and a slash command only expands at the very start of a turn: an instruction to "run it"
   further down never reaches the skill, which the model cannot invoke itself.

After invoking, reply with one line confirming the chat is opted in, and continue the task.
