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

A blockquote is one markdown paragraph: a single newline inside it is a soft line break and
renders as a space, so two commands on two separate lines paste as ONE line, concatenated.
Confirmed 2026-09-10 (countoff session): `gcloud auth login` and `gsutil cors set ...` given as
two lines in one blockquote pasted as `gcloud auth login gsutil cors set ...` and errored.

Multiple commands meant to run together are safe to batch in one blockquote ONLY when joined onto
a single line with `&&` or `;`:

> flutter clean && flutter pub get && flutter run

Two (or more) commands that must run as separate steps but still travel together - an interactive
login followed by a second command, anything that cannot be chained with `&&`/`;` - go in a
**fenced code block** instead, one command per line (the same escape the Windows-path gotcha below
already uses). A fenced code block is not parsed as a markdown paragraph, so its line breaks survive
the paste.

Separate blockquotes only when the steps are genuinely independent or Joe needs to pause between them.

## Language matching

Claude's own prose to Joe is ALWAYS English (see `~/.claude/CLAUDE.md` "Communication"). Language matching applies ONLY to the copyable content inside a blockquote/code block, which takes its reader's language, not Joe's.

- Joe pastes a Croatian thread or screenshot: reply prose stays English, the drafted message inside the blockquote is Croatian.
- Joe writes to Claude in Croatian: reply prose still English.
- Code, commands, and identifiers stay in their natural form (English) regardless of response language. Only surrounding prose switches.
- Messages drafted FOR Joe's teammates (Stevan, Peter, etc.): first check the recipient's `People\<Name>.md` in the Obsidian vault (or the project's own people memory, e.g. `reference_zng_people.md`) for a stated language preference and use it if found; otherwise default to casual Croatian with English tech terms left as-is (endpoint, response, deploy, PR...) - mirror the tone of Joe's Slack history, short and informal, no formal openings. This applies ONLY to the copyable teammate message inside the blockquote - Claude's own prose to Joe stays in English (Joe talks to Claude in English). Confirmed 2026-07-08.

## Message length

Keep responses tight enough to read in one pass without scrolling:

- Prose answers: 2-4 sentences max unless depth is explicitly asked for.
- Bullet lists: 3-5 items max; group if more.
- No multi-paragraph preamble before the thing Joe wants to copy.
- No closing summaries that restate what was just said.

If the task genuinely requires a long response (a full file, a long command), that is fine - strip all prose padding around it.
- A drafted teammate-facing message (the kind placed in a blockquote for Joe to copy and paste, e.g. a Slack message) should read as short lines or short paragraphs separated by blank lines, not one dense paragraph, even when it already fits the 2-4 sentence cap above. Scoped only to that copyable message content - it does not govern Claude's own prose replies to Joe, which `snippets/terse-replies.md` already covers.

## Team status updates

Scoped to a status update Claude drafts for Joe to forward to coworkers (a deploy/release/fix landing), not a general teammate message.

- Lead with the outcome or decision, not the mechanism. Cut the technical play-by-play (DNS/TTL/propagation, how it was done) - say what changed, not how it happened.
- Account for send time: if Joe won't forward it right away, write the end state as of when he sends it ("live"), not the in-progress state at draft time ("propagira se, kroz ~sat").
- Prefer the English term the team already uses over a translated one ("live", not "ziva") - a specific case of the "English tech terms left as-is" rule under Language matching, worth naming because the correction landed on exactly that word.
- Blockquote form, recipient language, and short-lines formatting are already covered above (Language matching, Message length) - this section only adds what the update should say, not how it's formatted.

## Windows path escaping gotcha

Markdown (CommonMark/GFM) treats a backslash before ASCII punctuation as an escape and consumes the backslash - a blockquote is raw markdown, so it renders this way too. `\.` becomes `.`, `\_`/`\-`/`\(` become `_`/`-`/`(`, and even `\\` collapses to `\`. Any Windows path with a dot-directory (`.for_bepy`, `.claude`, `.git`, `.env`, `.vscode`, `.cursor`) loses its separator: `C:\Users\tecno\revaire-mobile\.for_bepy\aab` pastes as `...revaire-mobile.for_bepy\aab`. Confirmed 2026-08-12.

- Fix (2026-08-12, supersedes the earlier forward-slash workaround): any copy-paste content containing a backslash goes in a **fenced code block**, never a blockquote - code blocks are not parsed as markdown, so every separator survives verbatim. A path named in prose (not a standalone copyable block) uses inline code instead.
- Rejected alternatives and why: forward slashes render fine but break `cmd.exe` and some CLIs; doubled backslashes (`C:\\Users\\...`) render correctly but leave the raw source text wrong; a blockquote wrapping a code block is correct but verbose with unconfirmed nested rendering.

## What NOT to do

- Do not embed a copyable command inside a prose sentence. Put it in its own blockquote.
- Do not add explanatory comments inside a copyable block if they would break it when pasted verbatim.
- Do not EVER deliver copyable content as plain unquoted text - prose replies included. Joe reaffirmed 2026-07-08 (overriding an earlier incident-derived exception that suggested plain text for Slack-style prose): ALWAYS use a blockquote, or a fenced code block for backslash content per the gotcha above, for anything he is meant to copy. Keep backticks out of the blockquote content itself so the paste stays clean.
