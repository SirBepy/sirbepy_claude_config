---
name: project-onboarding
description: Generates onboarding docs in .for_bepy/notebooklm/ by detecting the project stack (Flutter supported today; others prompt to scaffold or abort), overwriting existing files. Pass --compare=<path> for a structural diff against another repo. Aborts and asks if the stack is ambiguous or unknown.
disable-model-invocation: true
argument-hint: "[--compare=<path>]"
---

# /project-onboarding

> Generate NotebookLM-ready onboarding docs for the current project. File-by-file ingestion model: each output file is a focused, citable source for NotebookLM Q&A.

## When to use

- The dev (or any user) wants to learn a codebase via NotebookLM file-by-file ingestion.
- Triggered only on exact `/project-onboarding`. No natural-language triggers.

## Arguments

```
/project-onboarding [--compare=<path>]
```

- `--compare=<path>` - path to a sibling repo. Skill adds one extra file `compare-to-{name}.md` with a 1-page structural diff. Optional.

## Hard rules

- **Exact-match trigger only.** Do not auto-fire on "explain this project", "onboard me", etc.
- **Overwrite without prompting.** The dev knows this from the description; no backup, no confirmation.
- **Subs never commit.** Each sub stages files only. Main agent reports `READY_TO_COMMIT` after finish; the dev runs `/commit`.
- **No flows file.** Static-read flow narratives hallucinate. If the dev asks "what about flows", point them at `state-and-nav.md` (routes) + running the app + asking NotebookLM.
- **No em dashes anywhere.** All sub prompts forbid em/en dashes. Generated docs use plain hyphens. Reason: em dashes get mangled to mojibake (`â€"`) when any tool reads a UTF-8 file as ANSI, which corrupts the file.
- **UTF-8 only.** Subs write UTF-8 no BOM. Main agent's finish step MUST use UTF-8-explicit file ops (see `prompts/finish.md`). Never use `Get-Content` then `Set-Content -Encoding UTF8` on non-ASCII content.

## Algorithm

### Step 1 - Stack detection (run from cwd; first match wins)

`flutter` (`pubspec.yaml` exists AND contains `  flutter:` the SDK key, not just `flutter_` deps) is the only implemented template. Non-Flutter stacks: stop and ask whether to scaffold a template.

**Multi-stack:** if two checks fire (e.g. Flutter + Cloud Functions in one tree), STOP. List detected stacks. Ask user: pick one, or `all` (output to `.for_bepy/notebooklm/<stack>/` per stack).

**Unknown:** zero matches - STOP. List root files. Ask user to name a template or abort.

### Step 2 - Output prep

- Target dir: `<cwd>/.for_bepy/notebooklm/` (create if missing).
- If `--compare=<path>` passed: validate path exists and contains a recognizable project (any of the stack signals above). If not, abort with the bad path quoted.

### Step 3 - Fan out content subagents (parallel)

For each content file in the detected stack's template, dispatch one subagent **in a single message with multiple Agent tool uses** (concurrent execution).

Flutter template content files (5):
1. `what-it-does.md` - prompt: `prompts/flutter/what-it-does.md`
2. `architecture.md` - prompt: `prompts/flutter/architecture.md`
3. `data-and-api.md` - prompt: `prompts/flutter/data-and-api.md`
4. `state-and-nav.md` - prompt: `prompts/flutter/state-and-nav.md`
5. `glossary.md` - prompt: `prompts/flutter/glossary.md`

If `--compare` passed: also dispatch a 6th sub with `prompts/flutter/compare.md`, substituting `{COMPARE_PATH}` and `{COMPARE_NAME}` (basename of path).

For each sub, the dispatch prompt is the full content of the prompt file with `{REPO_ROOT}` substituted to the absolute cwd, PREPENDED with the canonical preamble from `refs/builder-preamble.md` (the `<STAGING_LINE>` for "Subs never commit" per the Hard rules above is `Stage your changes but do NOT commit...`) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers. Subs are `general-purpose` type, dispatched with `model: 'sonnet'` pinned explicitly (never inherit the session model).

### Step 4 - Serial finish (after all subs return)

Read `prompts/finish.md` and execute its two steps:
1. Aggregate `<gap>...</gap>` tags from all content files into `_followups.md`.
2. Write `README.md` with reading order + timestamp.

Both steps run directly by the main agent (no further subs).

### Step 5 - Report back

Print to user:
- Files written (paths)
- Total `<gap>` count
- `READY_TO_COMMIT` marker
- Reminder to run `/commit`

## Failure modes (concrete rules)

| Failure | Rule |
|---|---|
| Sub returns 0 lines | Retry that sub ONCE with appended instruction: "Previous attempt produced 0 lines. The codebase contains evidence for this scope - re-read the relevant dirs and emit at minimum a 30-line skeleton with `<gap>` tags where evidence is missing." If retry empty, write the file with one line: `<gap>generator could not produce content for this scope - manual write needed</gap>` and continue. |
| Sub exceeds 400 lines | During finish Step 1, truncate at the last `## ` heading boundary before line 400; append: `<gap>section truncated at 400 lines - remaining scope: [list cut headings]</gap>`. Truncation happens BEFORE gap extraction. |
| Sub writes outside its scope | Not enforced at runtime (too fragile). Documented limitation; prompt discipline carries it. |
| Two stacks detected | Print both, ask user. No default. |
| Zero stacks detected | Print root file listing, ask user to name a template or abort. |
| `.for_bepy/notebooklm/` already exists | Overwrite without prompt. Per-file overwrite is atomic via sub direct-write. |
| Sub crashes / times out | Write its file with single line: `<gap>subagent failed - rerun /project-onboarding or write manually</gap>` and continue. Other files unaffected. |
| `--compare` path invalid | Abort before fan-out. Quote the bad path. |

## Cost

Each content sub ≈ 30-60k tokens (depending on repo size). 5 subs in parallel ≈ 150-300k. With `--compare` add ~50k. Total ~150-350k per run. Acceptable for a multi-file onboarding artifact the dev will reuse.
