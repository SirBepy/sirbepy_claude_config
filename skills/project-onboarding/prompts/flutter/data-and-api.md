You are a subagent for /project-onboarding generating ONE file: data-and-api.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/data-and-api.md
Length: 150-400 lines. If you cannot fill 150 lines with substance from the codebase, write fewer lines and emit a <gap> for the missing scope — never pad.

COVER (this file's scope):
- Domain models in `lib/models/` (or equivalent) — group by area, show field shape via the Freezed/json_serializable class signature, not full source
- Repositories in `lib/data/repositories/` (or equivalent) — what does each repo own, what methods does it expose, what backend does it hit
- HTTP client setup (Dio / http / etc) — base URLs per flavor, interceptors, auth header injection
- Endpoint inventory — group by repository, list the routes called (path + verb), citing the repo file:line
- Cross-repo contracts: any references to other repos (e.g. zng-server, revaire-platform) — paths, expected schemas
- Local persistence: shared_prefs, secure_storage, hive, sqflite — what's stored, by what, why
- Caching layers if any
- Error/response envelope shape (does the backend return `{data, error}`, raw JSON, etc)

DO NOT COVER (other files own these):
- Riverpod state shapes that wrap these models → state-and-nav.md
- Routes / navigation → state-and-nav.md
- Product purpose, personas → what-it-does.md
- Layer split / DI pattern → architecture.md
- Build tooling, codegen → architecture.md
- Vocabulary definitions → glossary.md

PRIMARY SOURCES:
- {REPO_ROOT}/lib/models/ (use Glob, read the model class signatures)
- {REPO_ROOT}/lib/data/repositories/ (or equivalent)
- {REPO_ROOT}/lib/core/ for HTTP client setup
- Any server-domains.md / API schema docs referenced from CLAUDE.md
- {REPO_ROOT}/pubspec.yaml for HTTP / serialization deps

GAP PROTOCOL:
When the codebase does not answer a question your section needs, emit one line:
<gap>could not determine [specific question] - looked at [files checked]</gap>
Inline, at the point in the doc where the answer would have gone. Do NOT speculate. Do NOT write "presumably" or "likely". Either cite a file:line or emit a gap.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use em dash (—) or en dash (–). Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble. The file IS the output.
- Every endpoint or model claim must cite a file path (`lib/data/repositories/x/x_repository.dart:42`).
- Tables are fine for endpoint inventory and model lists. Prose for explanations of patterns.
- Snippets must be real (copied verbatim from the codebase).
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of <gap> tags emitted, any file you wanted to read but could not.
