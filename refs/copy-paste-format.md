# Copy-Paste Format Reference

The trigger rule lives in `~/.claude/CLAUDE.md` under "Communication". This file holds the expanded ruleset for formatting responses so Joe can copy content easily from the taskbar app.

## The core rule

Anything Joe is meant to copy goes in a **blockquote**, except content containing a backslash (Windows paths), which goes in a **fenced code block** instead - see "Windows path escaping gotcha" below. Plain inline backticks otherwise don't render distinctly in the app, so avoid them for copyable content.

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

## Windows path escaping gotcha

Markdown (CommonMark/GFM) treats a backslash before ASCII punctuation as an escape and consumes the backslash - a blockquote is raw markdown, so it renders this way too. `\.` becomes `.`, `\_`/`\-`/`\(` become `_`/`-`/`(`, and even `\\` collapses to `\`. Any Windows path with a dot-directory (`.for_bepy`, `.claude`, `.git`, `.env`, `.vscode`, `.cursor`) loses its separator: `C:\Users\tecno\revaire-mobile\.for_bepy\aab` pastes as `...revaire-mobile.for_bepy\aab`. Confirmed 2026-08-12.

- Fix (2026-08-12, supersedes the earlier forward-slash workaround): any copy-paste content containing a backslash goes in a **fenced code block**, never a blockquote - code blocks are not parsed as markdown, so every separator survives verbatim. A path named in prose (not a standalone copyable block) uses inline code instead.
- Rejected alternatives and why: forward slashes render fine but break `cmd.exe` and some CLIs; doubled backslashes (`C:\\Users\\...`) render correctly but leave the raw source text wrong; a blockquote wrapping a code block is correct but verbose with unconfirmed nested rendering.

## What NOT to do

- Do not embed a copyable command inside a prose sentence. Put it in its own blockquote.
- Do not add explanatory comments inside a copyable block if they would break it when pasted verbatim.
- Do not EVER deliver copyable content as plain unquoted text - prose replies included. Joe reaffirmed 2026-07-08 (overriding an earlier incident-derived exception that suggested plain text for Slack-style prose): ALWAYS use a blockquote, or a fenced code block for backslash content per the gotcha above, for anything he is meant to copy. Keep backticks out of the blockquote content itself so the paste stays clean.
