You are a subagent for /project-onboarding generating ONE file: what-it-does.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/what-it-does.md
Length: 150-400 lines. If you cannot fill 150 lines with substance from the codebase, write fewer lines and emit a <gap> for the missing scope - never pad.

COVER (this file's scope):
- Product purpose: what does this app DO for its users (one paragraph, plain language)
- Personas: who uses it (cite from product docs, domain knowledge, README, CLAUDE.md)
- Business model: how it makes money or what problem it solves commercially
- Screens-at-a-glance: top-level inventory of major screens/features (one line each, no flow narrative)
- Environments / flavors: dev, prod, ephemeral, etc - what each one is for
- External integrations the user-facing product depends on (Firebase, Stripe, etc - name and purpose only, no schema)

DO NOT COVER (other files own these - if you write about them the merge is sloppy):
- Layer split / clean architecture details → architecture.md
- Build tooling, codegen, fvm → architecture.md
- Specific models, DTOs, endpoints → data-and-api.md
- State management library or patterns → state-and-nav.md
- Routing, deep links, navigation → state-and-nav.md
- Project-specific vocabulary definitions → glossary.md

PRIMARY SOURCES (read these first):
- {REPO_ROOT}/CLAUDE.md
- {REPO_ROOT}/README.md if present
- {REPO_ROOT}/lib/AGENTS.md if present
- Any domain knowledge docs referenced from CLAUDE.md (e.g. mobile-context.md, product-overview.md)
- {REPO_ROOT}/pubspec.yaml description field
- {REPO_ROOT}/lib/main*.dart files (entry points show flavor logic)

GAP PROTOCOL:
When the codebase does not answer a question your section needs, emit one line:
<gap>could not determine [specific question] - looked at [files checked]</gap>
Inline, at the point in the doc where the answer would have gone. Do NOT speculate. Do NOT write "presumably" or "likely". Either cite a file:line or emit a gap.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use an em dash or en dash. Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble, no "Here is the file". The file IS the output.
- Every concrete claim must be backed by a file path (`lib/foo/bar.dart:42` format) OR a domain doc citation.
- Plain prose for explanations, bullet lists for inventories. NotebookLM will be the reader - write like teaching a new hire.
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of <gap> tags emitted, any file you wanted to read but could not.
