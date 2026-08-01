You are a subagent for /project-onboarding generating ONE file: glossary.md.

Target output: {REPO_ROOT}/.for_bepy/notebooklm/glossary.md
Length: 80-300 lines. Glossary may be shorter than other files. Quality > length - only include terms that are project-specific and would confuse a new hire.

COVER (this file's scope):
- Project-specific vocabulary - domain words, internal jargon, code-named features (e.g. "hot routes", "ephemeral flavor", "decoration arena")
- Acronyms used in the project that are not industry-standard
- Internal product names / code names for features
- Stack-relevant terms only if they have a project-specific meaning (e.g. "the auth flow" if the project defines "the auth flow" as something specific)

DO NOT COVER (these belong elsewhere or nowhere):
- Generic Flutter / Dart terms (Widget, Riverpod, GoRouter - those go in the reader's head from their general training)
- Specific model field names (data-and-api.md owns the field shape)
- Route names (state-and-nav.md owns the route inventory)
- Personas (what-it-does.md)

FORMAT:

```
## <Term>
**Where it appears:** `lib/path/file.dart:line`, also CLAUDE.md, domain-knowledge/foo.md

Definition in 1-3 sentences. Plain language. Avoid restating the codebase; explain the WHY or the CONCEPT.
```

Order: alphabetical by term.

PRIMARY SOURCES (search aggressively for repeated proper-noun-looking strings):
- {REPO_ROOT}/CLAUDE.md
- {REPO_ROOT}/lib/AGENTS.md if present
- {REPO_ROOT}/.cursor/rules/ for terms used in rule names
- Domain knowledge docs referenced from CLAUDE.md
- Grep the lib/ tree for capitalized project-specific identifiers that repeat (e.g. `HotRoute`, `Revaire-something`)
- pubspec.yaml description / name

GAP PROTOCOL:
When you find a term but cannot determine its meaning:
<gap>term `HotRoute` appears in lib/models/hot_route/ and CLAUDE.md but I could not determine what it means semantically - only its code shape</gap>

If a term is just a class name with no project-specific semantic meaning, do NOT include it. Glossary is for words that need a definition, not a class index.

OUTPUT RULES:
- Write directly to the target path. Overwrite if exists. Use UTF-8 encoding (the Write tool defaults to UTF-8 without BOM, which is correct).
- NEVER use an em dash or en dash. Use a plain hyphen (-) with spaces around it, a comma, or a colon. The reader's editor will mangle em dashes if any tool touches the file with a non-UTF-8 read.
- No preamble. The file IS the output.
- 15-40 terms is a healthy glossary. More than 60 means you're padding with generic terms.
- Do NOT include `Riverpod`, `GoRouter`, `Freezed`, etc unless the project has a special meaning for them.
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Stage your changes but do NOT commit. The main agent will run /commit after your report-back.

Report back with: line count written, count of terms defined, count of <gap> tags emitted.
