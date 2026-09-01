---
name: code-check
description: Triggers on /code-check. Structural + convention review - file splits, DRY, dead code, documented project patterns. Writes findings to the todos backlog. Callable standalone or from /close.
argument-hint: "[uncommitted|unpushed|<path>|<hash>] (default: uncommitted)"
---

# /code-check

> Structural review: file splits, DRY, dead code. Writes findings to ai_todos.

## The analysis runs in a fresh subagent, always

**The session that wrote the code never reviews it.** That is the whole reason this skill exists
separately from the work, in Joe's words: AI is very bad at reviewing its own code. Running the
review later did not give that property, it only delayed the same reviewer. A subagent gives it
for free, because it has no memory of the authoring decisions and no investment in the approach.

Split of duties, and it is not negotiable:

- **The invoking session** resolves the scope (below), dispatches, then acts on what comes back:
  Step 4a's routing, Step 5's output, and any todo files. Writing into `.claude/todos/` stays here
  because the backlog contract forbids a subagent doing it.
- **The subagent** runs Steps 0-4 read-only and returns findings. It edits nothing and writes no
  todo.

**What the dispatch may carry:** the scope arg, the resolved file list, and the diff. **What it must
never carry:** what the session was trying to do, why it chose an approach, or any assurance that
the code is correct. Passing the authoring rationale reintroduces exactly the bias this dispatch
exists to remove, and a reviewer told "this is fine, just check it" is no longer independent.

Dispatch with `general-purpose` and `model: 'sonnet'` explicitly. The three preamble markers below
are required by `hooks/dispatch-preamble-guard.py`, which requires *a* staging line and accepts
either wording (see `refs/builder-preamble.md`'s placeholder table) - it does not mandate these
exact three strings, only that each marker's family is present:

```
READ-ONLY DISPATCH

Stage your changes but do NOT commit. The main agent will run /commit after your report-back.
(For a repo sharing a git index with concurrent sessions, e.g. zng-app/zng-biller, use instead:
"Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.")

`run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
before ending your turn.

You are reviewing code you did not write, and you are not being told who wrote it or why.

Scope: <scope arg>
Files: <resolved file list>
Diff: <the diff, or the command that produces it>

Run Steps 0 through 4 of ~/.claude/skills/code-check/SKILL.md against that scope. Edit nothing.
Write no todo files. Return the findings as the JSON blocks that skill defines, each with your
class-1/2/3 judgement from Step 4a and the reason for it.
```

**If the Agent tool is unavailable** (some runners disable it), say so in one line, run the
analysis in-session, and label the output `isolation: NOT held`. A review that quietly loses the
property is worse than one that admits it.

## Scope resolution

Determine what to review based on args:

| Arg | What to run |
|-----|-------------|
| `uncommitted` | `git diff HEAD --name-only --diff-filter=ACM` union `git ls-files --others --exclude-standard` |
| `unpushed` | `git log @{u}..HEAD --name-only --diff-filter=ACM --format=` |
| `shas:` prefix, one or more hashes (`shas:abc1234`, `shas:abc1234 def5678`) | union of `git diff-tree --no-commit-id --name-only -r <hash>` per hash - each commit's own change, not a range diff. Used by `/close` Phase 2 to scope to one session's own commits. The prefix is what makes a ONE-sha list unambiguous; without it a lone sha falls through to the range row below and diffs sha-to-working-tree, which is empty right after a commit. |
| Looks like a file path | treat as single-file list |
| Looks like a bare hash or range (`abc1234`, `HEAD~3..HEAD`) | `git diff <arg> --name-only` |
| No args | default to `uncommitted`: `git diff HEAD --name-only --diff-filter=ACM` union `git ls-files --others --exclude-standard` |

"Uncommitted" means everything `git status` would show as dirty, not everything `git diff` alone can see: `--diff-filter` only matches paths already in the index, so a brand-new untracked file needs the `git ls-files --others --exclude-standard` half of the union or it never enters scope.

## Step 0 - Skill description budget

Before filtering, scan the resolved scope for any `SKILL.md` files. For each, read the `description:` frontmatter and count its words. If over budget (> ~25 words / 120 chars), record a finding - unless the extra length is a trigger keyword that can't be cut without breaking the skill's firing (same judgment as bepy-skill-creator's Description budget gate):

```json
{ "title": "[skill] description over budget", "files": ["path"], "problem": "description is N words; skill descriptions load into every session's system prompt, so verbosity is a per-session token cost", "fix": "trim to trigger surface (~25 words), preserving every trigger clause and when-to-use keyword" }
```

If scope has no `SKILL.md` files, skip this step.

## Filter to code files

After resolving, filter to code files only. Drop: `.md`, `.json`, `.toml`, `.yaml`, `.yml`, `.gitignore`, anything under `.for_bepy/`, `.claude/todos/`, or `memory/`.

If the filtered list is empty (and Step 0 produced no findings): print "No code files in scope." and stop.

## Step 1 - Size check

For each file in scope, get line count: `wc -l "path"` via Bash tool.

If > 400 lines AND has an obvious split seam (separate concerns, reusable unit, clear module boundary), record:

```json
{ "title": "[file] should be split", "files": ["path"], "problem": "[file] is N lines, mixes [X] and [Y]", "fix": "split at [boundary] into [new-file]" }
```

If no obvious seam, skip that file.

## Step 2 - DRY pass

For each new top-level symbol in scope (function, const, class, interface, type, export, def, func, local function - language-dependent): Grep the repo for equivalents by name, shape, and purpose. For each duplicate found, record:

```json
{ "title": "Duplicate: [symbol]", "files": ["path:line (new)", "path:line (existing)"], "problem": "what duplicates what (one sentence)", "fix": "delete X and import Y / extract shared util to Z" }
```

Cap: ~3 Grep calls per symbol. Use only Grep, Read, and Glob - no shell pipelines. If scope has zero new top-level symbols (body-only edits), skip this step.

## Step 3 - Dead code pass

For each new top-level symbol: `Grep pattern: "\\b<symbol>\\b", output_mode: "count"`. Count <= 1 (definition only) = never called. Also flag: unreachable branches, commented-out blocks left in, imports never read.

```json
{ "title": "Dead code: [symbol]", "files": ["path:line"], "problem": "one sentence", "fix": "delete / uncomment / wire up at X" }
```

## Step 4 - Project convention pass

Steps 1-3 are language-agnostic structure. This step checks the diff against what THIS project has
written down, which is where most of the review value sits: a generic pass will happily bless code
that breaks a rule the repo spent a page explaining.

1. **Discover the binding docs** (read them, don't assume their contents):
   - the nearest `CLAUDE.md` to the files in scope - a package-level one beats the repo root, and
     when they conflict the package file wins (that is usually stated in the root file itself)
   - every `.cursor/rules/**/RULE.md` in the repo, read DIRECTLY. Do not rely on a `CLAUDE.md`
     `@import` chain to surface them: the import is one line that is easy to skim past, and these
     files typically hold the stack-specific rules (naming, component/DS usage, state management,
     routing) that a diff is most likely to breach. Glob for them rather than assuming the paths.
   - whichever of these exist: `PATTERNS.md`, `DESIGN-SYSTEM-SPEC.md`, `CONTRIBUTING.md`,
     `STYLEGUIDE.md`, `ARCHITECTURE.md`, `.specify/memory/constitution.md`, plus anything a
     discovered doc names as binding (follow one level of "see X for the rules" links)
   - `~/.claude/code-style/<stack>.md` for the project's stack
   - the lint/format config covering the scope (`eslint.config.js`, `.prettierrc`, `ruff.toml`,
     `.editorconfig`) - the machine-checkable subset, and the place to confirm real budget numbers
     instead of guessing them
2. **Delegate when a doc is expensive to read.** If the docs sit under a package whose own
   `CLAUDE.md` is large (it gets re-injected on every Read in that tree), dispatch ONE subagent
   (`model: 'sonnet'`, read-only, "report findings, edit nothing") that reads the docs plus
   `git show <range>` and returns findings only. Keeps the raw doc bytes out of the main context.
   If the Agent tool is unavailable, this one does NOT degrade freely - keeping those bytes out is
   the entire point, so read the docs inline only when the range is under ~10 files, and above that
   SKIP this step naming the docs left unread. See the doctrine's "When the Agent tool is
   unavailable"; this is the bounded-scope exception it describes.
3. **Judge only against rules that are actually written**, and QUOTE each one. A finding without a
   quote is not a finding. **A rule only binds files in the language/stack it targets** - a
   Dart-specific rule cited against an HTML, Python, or JS file is not a finding; when scope is
   genuinely unclear, treat it as an unwritten-rule observation instead.
4. Record each as:

```json
{ "title": "[rule] one-line breach", "files": ["path:line"], "problem": "<doc> <section> says \"<quoted rule>\"; path:line does X instead", "fix": "the concrete change" }
```

   Prefix the title with `BLOCKER:` when the quoted rule is a MUST / NEVER / non-negotiable.
5. **Unwritten rules are a doc gap, not a code defect.** Anything that looks wrong but no document
   states goes in a clearly-marked "unwritten-rule observations" list printed inline and NEVER
   written as a code todo. If such an observation is worth enforcing, the todo to file is a
   documentation change to the pattern doc, not a fix to the reviewed code.

## Step 4a - Classify and route each finding

Every finding from Steps 0-4 gets exactly one class, and the class decides whether it is applied
here or filed for later. Filing is the default; applying is the exception that must earn itself.

| Class | What it covers | Route |
|-------|----------------|-------|
| 1 - mechanical | An unused import, a symbol nothing references, a duplicated helper collapsed onto one that already exists, a description over budget | Apply it, if and only if the exercise test below passes |
| 2 - structural | Splitting an over-long file, extracting a repeated block, centralising constants | File it, unless the exercise test passes AND the suite is green |
| 3 - judgment | The abstraction is wrong, the boundary is in the wrong place, a convention breach with a real decision inside it | Always file it. Never apply |

**The exercise test, and it is the whole gate.** Before applying anything, name the specific test
file or command that would FAIL if this change were wrong, and say why it would reach the changed
lines. A repo-wide suite passing is not evidence for a file that no test imports.

This is not a hypothetical caution. Measured 2026-08-22 while writing this section: a mechanical
dead-symbol scan flagged `hooks/_hooklib.py`'s `strip_quotes` as having zero references, when
`hooks/package-manager-guard.py:28` and `hooks/flutter-workdir-guard.py:37` both import it under
an alias. Deleting it would have made both guards fail closed on every invocation, and
`python ci/run_all.py` would still have passed, because neither guard has a `hooks/test_*.py`
suite. The detector was confident and wrong, and the verification floor could not see it.

After applying, run the named command, paste its real output, and report the change in one line.
Never file a todo for something already applied.

**The honest exit.** A class-1 finding whose exercise test cannot be named is neither applied nor
filed. Append one line to `.claude/todos/dropped-findings.log` instead:

```
<ISO date>  <class>  <path:line>  <one-line finding>  dropped: <what verification was missing>
```

A finding nobody will action and nobody can verify does not belong in a backlog that already
needs `/cleanup-todos` sweeps. The log exists so a misclassification stays recoverable rather
than vanishing silently.

## Step 5 - Output

Merge findings from Steps 0-4, minus anything Step 4a applied or dropped.

**If the project has a repo root for `.claude/todos/`:** write each finding as a `.md` file there, per `~/.claude/skills/close/ai-todos-format.md` (filename/id rules, git-policy self-heal; create the folder if missing). Format:

```markdown
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# [title]

**Type:** task
**Origin:** ai

## Goal
[what needs to happen]

## Context
[problem. Cite files as path:line.]

## Approach
[fix]

## Acceptance
[how to verify it is done]
```

**If not in a project (no repo root):** print all findings inline, one block per finding.

Print a summary line:

```
code-check: N findings (A size, B DRY, C dead code, D desc, E convention). M written to todos, P applied, Q dropped.
```

`P` and `Q` come from Step 4a. Name each applied finding and each dropped one on its own line
below the summary; a bare count hides which file changed.

Print any "unwritten-rule observations" from Step 4 below that line, under their own heading, so
they are visibly NOT part of the finding count.

If zero findings: `code-check: No structural issues found.`
