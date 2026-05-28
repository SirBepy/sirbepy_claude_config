You are a subagent for /project-onboarding generating ONE file: state-and-nav.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/state-and-nav.md
Length: 150-400 lines. If you cannot fill 150 lines with substance from the codebase, write fewer lines and emit a <gap> for the missing scope — never pad.

COVER (this file's scope):
- State management library (Riverpod / BLoC / Provider / etc) and the project's chosen patterns
- Controller inventory: list the major `@riverpod` (or equivalent) controllers, what each owns, whether `keepAlive`
- State class patterns (Equatable vs Freezed, AsyncValue<T> usage)
- ref.watch / ref.read / ref.listen conventions used in the project
- Router library (GoRouter / auto_route / Navigator 1.0) and the route definition style
- Route inventory: pull `AppRoute` constants (or equivalent) and list them with their path + screen widget
- Navigation patterns: named vs path-based, custom helper extensions, redirect logic
- Guard / redirect logic (e.g. login redirect)

DO NOT COVER (other files own these):
- Models / DTOs / endpoints → data-and-api.md
- Layer split / DI pattern overview → architecture.md
- Build tooling, codegen mechanics → architecture.md (you can mention "controllers use codegen" but not how to run it)
- Product purpose, personas → what-it-does.md
- Vocabulary definitions → glossary.md

PRIMARY SOURCES:
- {REPO_ROOT}/lib/core/routing/ (or equivalent)
- {REPO_ROOT}/lib/presentation/ controllers (search for `@riverpod`, `@Riverpod(keepAlive: true)`)
- {REPO_ROOT}/.cursor/rules/dart-riverpod.mdc, dart-navigation.mdc (or .claude/rules mirrors)
- {REPO_ROOT}/pubspec.yaml for state / nav deps

GAP PROTOCOL:
When the codebase does not answer a question your section needs, emit one line:
<gap>could not determine [specific question] - looked at [files checked]</gap>
Inline, at the point in the doc where the answer would have gone. Do NOT speculate. Do NOT write "presumably" or "likely". Either cite a file:line or emit a gap.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use em dash (—) or en dash (–). Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble. The file IS the output.
- Every controller / route claim must cite a file:line.
- Tables are good for the route inventory and controller inventory.
- Snippets must be real (copied verbatim).
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of <gap> tags emitted, any file you wanted to read but could not.
