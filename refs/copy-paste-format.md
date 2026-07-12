# Copy-Paste Format Reference

The trigger rule lives in `~/.claude/CLAUDE.md` under "Communication". This file holds the expanded ruleset for formatting responses so Joe can copy content easily from the taskbar app.

## The core rule

Anything Joe is meant to copy goes in a **blockquote**. Everything else (inline backticks, fenced code blocks) does not render distinctly in the app, so avoid them for copyable content.

This applies to: commands, code to run or paste, config snippets, prose to paste elsewhere, SQL, JSON payloads, environment variable values, curl requests, sequential shell steps.

## Placeholders

When a copyable block contains a placeholder (e.g. `<YOUR_TOKEN>`, `<PROJECT_ID>`), note it in a prose line immediately before the blockquote - not as a comment inside the block:

Replace `<PROJECT_ID>` with your Firebase project id:

> firebase deploy --project <PROJECT_ID>

## Sequential commands

Multiple commands meant to run together can be batched in one blockquote:

> flutter clean && flutter pub get && flutter run

Separate blockquotes only when the steps are genuinely independent or Joe needs to pause between them.

## Language matching

Respond in whatever language Joe wrote in - no exceptions, no defaulting to English.

- Joe writes in Croatian: full response in Croatian, including prose inside blockquotes.
- Joe writes in English: full response in English.
- Mixed message: match the dominant language; if unclear, match the question clause.
- Code, commands, and identifiers stay in their natural form (English) regardless of response language. Only surrounding prose switches.
- Messages drafted FOR Joe's teammates (Stevan, Peter, etc.): default to casual Croatian with English tech terms left as-is (endpoint, response, deploy, PR...) - mirror the tone of Joe's Slack history, short and informal, no formal openings. This applies ONLY to the copyable teammate message inside the blockquote - Claude's own prose to Joe stays in English (Joe talks to Claude in English). Confirmed 2026-07-08.

## Message length

Keep responses tight enough to read in one pass without scrolling:

- Prose answers: 2-4 sentences max unless depth is explicitly asked for.
- Bullet lists: 3-5 items max; group if more.
- No multi-paragraph preamble before the thing Joe wants to copy.
- No closing summaries that restate what was just said.

If the task genuinely requires a long response (a full file, a long command), that is fine - strip all prose padding around it.

## What NOT to do

- Do not embed a copyable command inside a prose sentence. Put it in its own blockquote.
- Do not add explanatory comments inside a copyable block if they would break it when pasted verbatim.
- Do not EVER deliver copyable content as plain unquoted text - prose replies included. Joe reaffirmed 2026-07-08 (overriding an earlier incident-derived exception that suggested plain text for Slack-style prose): ALWAYS use a blockquote for anything he is meant to copy, no exceptions. Keep backticks out of the blockquote content itself so the paste stays clean.
