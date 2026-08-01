You are a subagent for /project-onboarding generating ONE file: compare-to-{COMPARE_NAME}.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/compare-to-{COMPARE_NAME}.md
Length: 80-250 lines. This file is a STRUCTURAL DIFF, not a full second onboarding doc. Stay focused.

The "current project" is at {REPO_ROOT}.
The "compare project" is at {COMPARE_PATH}.

COVER (this file's scope):
- 1-paragraph TL;DR of the comparison (same stack? same architecture? same backend?)
- Side-by-side table comparing:
  - Tech stack (Flutter version, key deps)
  - Architecture layout (presentation/data/models/core vs whatever {COMPARE_NAME} uses)
  - State management library
  - Routing library
  - DI pattern
  - Build tooling
  - Test scaffold
- Notable differences worth flagging for a developer moving between the two
- Notable similarities (so the reader knows what carries over)
- One-paragraph "if you know {COMPARE_NAME}, here's how {REPO_ROOT} basename will surprise you"

DO NOT COVER:
- Full onboarding of {COMPARE_NAME} - that's a separate /project-onboarding run inside {COMPARE_PATH}
- Product / business model comparison - only structural / engineering differences
- Per-feature comparison - too deep; stick to scaffold and patterns

PRIMARY SOURCES:
For each project, sample these files:
- pubspec.yaml (versions, deps)
- lib/ top-level directories (Glob `lib/*` on each)
- .cursor/rules/ or .claude/rules/ for architectural rules
- CLAUDE.md or AGENTS.md for documented conventions
- analysis_options.yaml for lint posture

You do NOT need to read every file in {COMPARE_PATH}. Sample enough to make accurate structural claims. If you cannot tell, emit a <gap>.

GAP PROTOCOL:
<gap>could not determine [specific question] - looked at [files checked in both repos]</gap>
Inline. Do NOT speculate.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use an em dash or en dash. Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble. The file IS the output.
- Every claim must cite a file in one or both repos (use `{REPO_ROOT-basename}/path` or `{COMPARE_NAME}/path` to disambiguate).
- Tables are good for side-by-side comparison.
- Keep tone neutral - this isn't a "which is better" doc, it's a "what's different" doc.
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of <gap> tags emitted, summary of biggest difference and biggest similarity.
