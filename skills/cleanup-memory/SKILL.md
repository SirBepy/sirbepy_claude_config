---
name: cleanup-memory
description: Audits the current project's auto-memory files for staleness, dead references, and duplication; dedupes and archives, everything confirm-gated before anything moves.
disable-model-invocation: true
---

# /cleanup-memory

> Dedupe, verify, and triage the auto-memory system (the memory directory named in this session's auto-memory context) - mirrors `/cleanup-todos`'s confirm-gated triage, applied to Claude's own persistent memory instead of todos.

This is a maintenance pass only: it never acts on a memory's advice, only on whether the memory
itself is still accurate and non-duplicate. Every removal - a dedupe merge or a suggested drop -
goes through the confirm gate in the Apply step. Nothing moves before the dev replies.

## Step 1 - Locate and read

The memory directory for the current project is the one named in this session's auto-memory
context (the `# auto memory` section). If that section isn't present this session, stop and
report: "No memory system detected for this project."

Glob `*.md` in that directory, excluding `MEMORY.md` itself. If empty: output "No memory files
found." and stop.

Read every file's frontmatter (`name`, `description`, `metadata.type`) and full body. Also read
`MEMORY.md`.

## Step 1.5 - Size and length checks (mechanical, read-only)

- **Encoded-cwd path derivation**: the project memory dir is
  `~/.claude/projects/<encoded-cwd>/memory/`, where `<encoded-cwd>` replaces path
  separators and colons with `-` (e.g. `C:\Users\foo\bar` -> `C--Users-foo-bar`).
  Derive it from the primary working directory shown in the session environment -
  never assume a hardcoded root.
- **MEMORY.md line count**: the harness silently truncates at 200 lines, dropping
  everything after. Warn at 175, flag critical at 195+.
- **Index entry length**: flag any MEMORY.md bullet over ~150 chars - detail
  belongs in the linked topic file, not the index.
- **T0 axiom candidates**: flag entries meeting ALL 3: (1) Claude defaults wrong
  without it, (2) failure is silent, (3) applies every session. Candidates for a
  future `axioms.md`; only promote if not already in CLAUDE.md.
- **CLAUDE.md promotion candidates**: flag memories that apply across ALL
  projects (editor prefs, communication style, universal workflow rules). Flag
  only - never auto-write to `~/.claude/CLAUDE.md`.

## Step 2 - Index/file consistency (mechanical, read-only)

Cross-check `MEMORY.md`'s entries against the files actually on disk:

- A file with no `MEMORY.md` line pointing to it: `orphan-file`.
- A `MEMORY.md` line whose linked file doesn't exist: `orphan-index-entry`.

Both are mechanical - no subagent needed, no judgment call. Carry into the report as-is.

## Step 3 - Dedupe (read-only)

Read every file's `description` + body, flag pairs/groups covering the same underlying fact,
rule, or incident (overlapping topic, near-identical `description`, or one memory that's clearly
a superseded/earlier version of another - e.g. a body that says "SUPERSEDED" or "RESOLVED" and
names the memory that replaced it). For each group, identify which one has the more complete,
current body (or the most recently-touched file if tied) - that one is kept. Tag the others
`origin: dedupe`, recording the kept `name`.

Do NOT write or move anything in this step.

## Step 4 - Staleness / dead-reference triage

Cap the deep pass at 60 files to bound subagent prompt size - overflow gets the shallow pass
below. Sort candidates by mtime ascending (least-recently modified first) so a different set
rotates through each run. After a file's deep pass, touch it (e.g. a trivial no-op edit to its
`description` line, or append a `<!-- last-deep-checked: YYYY-MM-DD -->` comment) so it rotates to
the back of the queue next run.

**Deep pass (up to 60):** dispatch exactly ONE subagent (`model: 'sonnet'`), full text of each
memory in one prompt. For each memory, it verifies:

- Every concrete claim that names a file path, function, command, or flag: does it still exist
  in the current codebase (grep/glob check)? Same discipline as this file's own "Before
  recommending from memory" contract, just run as a batch audit instead of per-use.
- Every `[[name]]` link: does a memory file with that `name` in its frontmatter actually exist?
  Flag broken links.
- `suggested_drop`: true/false + one-line reason. Flag ONLY when the memory is genuinely stale
  (named things no longer exist and the memory's advice can't apply), explicitly marked
  superseded/resolved with no residual generalizable advice, or fully covered by another kept
  memory. Never flag on age alone - a still-accurate, still-relevant memory stays regardless of
  how old it is.

Must stay a single batched call, never one dispatch per memory.

**Shallow pass (remainder, if any):** main agent only, no subagent, no content read.
`suggested_drop` forced `false` - a shallow-tier memory can still appear in the confirm list via
Step 3's dedupe tagging (dedupe is corpus-wide, not tier-limited), but never independently
flagged stale by this step.

## Step 5 - Report

Deliver as the turn's FINAL message, no tool call after it - a same-turn `AskUserQuestion` would
swallow the preceding text in this harness.

Contents, in order:

0. Step 1.5 findings: size/length warnings, T0 axiom candidates, CLAUDE.md
   promotion candidates (or "None.").
1. Index/file consistency hits from Step 2 (or "Index and files match.").
2. Dedupe-group count and list.
3. Broken-link findings (memory `X` links to `[[Y]]`, no memory named `Y` exists).
4. Stale/dead-reference findings from the deep pass (memory `X` claims `path/fn` exists, not
   found).
5. A unified confirm list: every `origin: dedupe` loser, every `suggested_drop`, every broken
   link's source memory (if the fix is "drop" rather than "just fix the link text" - judgment
   call left to the dev, not auto-decided here). Each entry: `name`, one-line reason, origin(s).

Close with a plain-text prompt: "Reply with names to confirm (dedupe merges and drops), `fix
links only` to just repair broken `[[links]]` without dropping anything, or `keep all`."

## Step 6 - Apply confirmed items

The only step that mutates the memory directory.

For each confirmed drop or dedupe-loser: move the file to `<memory-dir>/archive/` (never
plain-delete - a memory turning out to still be load-bearing should be recoverable), remove its
`MEMORY.md` line, and grep the remaining memory files for `[[<name>]]` references - replace with
a plain-text mention (drop the link syntax) rather than leaving a dangling link.

For a dedupe merge specifically: before archiving the loser, check its body for any detail not
already present in the keeper's body (a distinct example, a distinct "Why") - fold that in as a
short addition to the keeper first, then archive the loser.

For `fix links only`: repair each broken `[[name]]` in place (either it's a typo of an existing
memory's actual name, in which case correct it, or it points at something truly gone, in which
case drop the link syntax and leave the surrounding sentence readable) - no files archived.

Never touch `MEMORY.md` structure beyond removing/updating the specific lines this run confirmed.

## Non-goals (v1)

- No cross-project sweep - one project's memory directory per run. Running it project-by-project
  is the intended workflow, same as `/cleanup-todos` being per-repo.
- No auto-drop, ever - every removal goes through the Step 5 confirm gate.
- No scheduled/cron trigger - manual invocation only.
- No rewriting a memory's *content* for style/length during this pass - a kept memory's body is
  only ever edited to fold in a dedupe-loser's unique detail (Step 6) or repair a link; anything
  more is a separate, differently-gated edit.
