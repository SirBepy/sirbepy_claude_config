<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Copy-paste text goes in fenced code, not blockquotes

**Type:** global-rule
**Origin:** ai
**Summary:** Move the copy-paste rule from "copyable text in a blockquote" to "copyable text in a fenced code block", because Conductor now draws every blockquote as a reply-style quote of a person.

## Why

On 2026-11-12, in `claude_usage_in_taskbar` (branch `quote-blocks`), Joe settled that a markdown blockquote is always a quote of a person, drawn as a reply bubble with the speaker on its own line (`> **Airion:**` then the words). The old transcript copy card for blockquotes is gone. Asked what replaces it for paste-ready text, Joe said: "maybe we start using ``` ``` for code blocks? we barely use copy cards anymore anyway, but myb thats the way to go?"

Conductor's per-turn prompt (`TURN_STATUS_PROMPT`, `src-tauri/src/daemon/claude_config/args.rs`) already tells chats spawned by the app that anything Joe should copy goes in a fenced code block. The global rule still says the opposite, so a chat outside the app (or one weighing the two) gets a conflict.

## Goal

- `~/.claude/refs/copy-paste-format.md` "The core rule": copyable content goes in a fenced code block, not a blockquote. Keep the sequential-commands and Windows-path sections consistent with that (the backslash exception becomes moot).
- `~/.claude/CLAUDE.md` Communication bullet "Copy-paste for Joe": same change in its one-line core.
- Add one line saying a blockquote is for quoting a person, with their name in bold first.

## Context

- Joe has not yet approved a global edit; this is filed, not applied (global work needs his word in the session that does it).
- Conductor side shipped in the `quote-blocks` commit of `claude_usage_in_taskbar` (markdown-quote.ts, chat-messages-markdown.css).
