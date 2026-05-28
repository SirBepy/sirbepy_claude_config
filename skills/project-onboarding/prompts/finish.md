All content subagents have returned. Run these two steps serially. Do NOT spawn subagents for either.

ENCODING WARNING (critical, do not skip):
- Subagents write content files as UTF-8 without BOM. PowerShell's `Get-Content` defaults to ANSI (Windows-1252) on Windows 5.1, which mangles UTF-8 multi-byte characters into mojibake (e.g. `—` becomes `â€"`).
- When reading or rewriting files in either step below, use either the Edit tool (which handles encoding correctly), the Read tool (which reads UTF-8), or PowerShell with explicit UTF-8: `[System.IO.File]::ReadAllBytes($path)` then `[System.Text.Encoding]::UTF8.GetString($bytes)`. Write back via `[System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))`.
- Do NOT use plain `Get-Content` followed by `Set-Content -Encoding UTF8` for any file that may contain non-ASCII characters. This sequence corrupts em dashes and other multi-byte chars.

STEP 1 - Aggregate gaps into _followups.md
=========================================

For each content file in `.for_bepy/notebooklm/`:
- what-it-does.md
- architecture.md
- data-and-api.md
- state-and-nav.md
- glossary.md
- (if --compare was passed) compare-to-{name}.md

Do the following:

1a. **Truncation check.** If the file exceeds 400 lines, find the last `## ` heading boundary before line 400 and truncate there. Append one line:
    `<gap>section truncated at 400 lines - remaining scope: [list cut headings]</gap>`
    Truncation happens BEFORE gap extraction.

1b. **Gap extraction.** Read the file. Find every line containing `<gap>...</gap>`. Collect the inner text. Remove the `<gap>` line from the source file in-place. If removing the gap leaves an empty line adjacent to other empty lines, collapse them.

Write `.for_bepy/notebooklm/_followups.md` with this exact structure:

```
# Followups

Open questions surfaced during onboarding generation. Each gap is one line and includes which file raised it and what was checked.

Regenerate this file by running /project-onboarding.

## architecture.md
- could not determine [...] - looked at [...]
- ...

## data-and-api.md
- ...
```

Omit sections that have zero gaps. If total gaps across all files = 0, write the file with body:

```
# Followups

No followups - all subagents resolved their scope from the codebase.
```

STEP 2 - Write README.md
========================

Write `.for_bepy/notebooklm/README.md` with this exact template, substituting `{timestamp}` with current ISO date (`YYYY-MM-DD`), and `{compare_section}` with either the compare-line or empty:

```
# Project onboarding

Generated {timestamp}. Regenerate with `/project-onboarding`.

Files are designed for file-by-file NotebookLM ingestion. Read in this order:

1. `what-it-does.md` - product purpose and personas
2. `architecture.md` - layers, packages, build
3. `data-and-api.md` - models, endpoints, cross-repo contracts
4. `state-and-nav.md` - state management and routing
5. `glossary.md` - project-specific vocabulary
6. `_followups.md` - open questions the generator could not resolve{compare_section}
```

If `--compare` was passed, `{compare_section}` is:
```

7. `compare-to-{name}.md` - structural diff against {path}
```

If not, `{compare_section}` is empty string.

After both steps, stop. Do NOT commit. Joe will run `/commit`.

Report to user:
- Files written (paths)
- Total gap count across all files
- `READY_TO_COMMIT` marker
- Reminder: `/commit`
