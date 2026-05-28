You are a subagent for /project-onboarding generating ONE file: architecture.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/architecture.md
Length: 150-400 lines. If you cannot fill 150 lines with substance from the codebase, write fewer lines and emit a <gap> for the missing scope — never pad.

COVER (this file's scope):
- Top-level layer split (presentation / data / models / core or equivalent) — show the actual tree
- Package/module organization inside `lib/`
- Dependency injection / service-locator pattern (Riverpod providers as DI? get_it? other?)
- Build tooling: fvm version, flavors, build_runner targets, code generators in use (`@riverpod`, `@freezed`, `json_serializable`, etc)
- Cross-cutting concerns: error handling shape, logging, analytics surface, feature flags
- Testing scaffold: where tests live, golden tests, mock patterns

DO NOT COVER (other files own these):
- State management library or patterns → state-and-nav.md
- Routing, navigation, deep links → state-and-nav.md
- Specific models, DTOs, API endpoints → data-and-api.md
- Product purpose, personas, business model → what-it-does.md
- Project-specific vocabulary definitions → glossary.md

PRIMARY SOURCES:
- {REPO_ROOT}/pubspec.yaml (dependencies, codegen)
- {REPO_ROOT}/lib/ tree (use Glob to list top-level dirs)
- {REPO_ROOT}/.cursor/rules/ if present (architectural rules)
- {REPO_ROOT}/.claude/rules/ if present (mirror of cursor rules)
- {REPO_ROOT}/analysis_options.yaml
- {REPO_ROOT}/build.yaml if present
- {REPO_ROOT}/test/ tree for test layout
- {REPO_ROOT}/scripts/ for build helpers

GAP PROTOCOL:
When the codebase does not answer a question your section needs, emit one line:
<gap>could not determine [specific question] - looked at [files checked]</gap>
Inline, at the point in the doc where the answer would have gone. Do NOT speculate. Do NOT write "presumably" or "likely". Either cite a file:line or emit a gap.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use em dash (—) or en dash (–). Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble. The file IS the output.
- Every concrete claim must be backed by a file path (`lib/foo/bar.dart:42` format).
- Mix prose and code snippets. Snippets must be real (copied verbatim, not invented).
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of <gap> tags emitted, any file you wanted to read but could not.
