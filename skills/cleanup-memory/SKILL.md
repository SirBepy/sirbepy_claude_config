---
name: cleanup-memory
description: Audits the current project's auto-memory files for staleness, dead references, and duplication; dedupes and archives, applying by default after one up-front question.
disable-model-invocation: true
---

# /cleanup-memory

> Dedupe, verify, and triage the auto-memory system (the memory directory named in this session's auto-memory context) - applied to Claude's own persistent memory instead of todos. Unlike `/cleanup-todos`'s per-item confirm list, this auto-applies every finding by default; the one up-front question exists so the dev can say "stop" or "check twice", not to enumerate items for sign-off.

This is a maintenance pass only: it never acts on a memory's advice, only on whether the memory
itself is still accurate and non-duplicate. Auto-apply is the default outcome, not an opt-in flag -
the single question in Step 5 is the dev's one chance to redirect (apply / get a second opinion /
say something else), not a per-item gate. Nothing is ever plain-deleted: every archive/drop moves
the file to `<memory-dir>/archive/` (Step 6), recoverable by moving it back and re-adding its
`MEMORY.md` line.

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

Cross-check `MEMORY.md`'s entries against the files actually on disk. A file counts as reachable if
`MEMORY.md` links it either way: a `(file.md)` link or a `[[wikilink]]` reference (memory files
cross-reference each other via `[[name]]`, and a `(file.md)`-only sweep overcounts orphans - a
reproduction on `claude_usage_in_taskbar` found 62 vs the real 58 for exactly this reason).

- A file reachable from neither form: `orphan-file`.
- A `MEMORY.md` line whose linked file doesn't exist: `orphan-index-entry`.

Both are mechanical - no subagent needed, no judgment call. Report the counts of both
(`orphan-file: N`, `orphan-index-entry: N`) even when zero - Step 7 carries these forward.

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

## Step 5 - Ask (one question, up front)

The apply set going in: every `origin: dedupe` loser (Step 3), every `suggested_drop` (Step 4),
every broken-link fix (Step 2/4), every `orphan-file` needing a new index line, and every
`orphan-index-entry` needing its dangling line dropped (Step 2). Nothing outside this set is
ever auto-applied - Step 1.5's size warnings and CLAUDE.md/axiom candidates stay flag-only.

Ask exactly ONE structured question (the harness's `AskUserQuestion`, or
`mcp__cc_conductor__ask_user_question` where available - per CLAUDE.md's Communication section)
as the FIRST content of the turn, with no preceding chat text: a same-turn question tool call
swallows any text before it in this harness, so the audit counts and highlights go inside the
question's own `question`/header text, never in a separate message first. This is the same
constraint the old Step 5 documented; it now governs where the summary text lives, not whether
a question can be asked at all.

Options:

- **Apply all** (default/recommended) - auto-apply the full set above, protections intact
  (archive not delete, fold-before-archive, honour any exclusions already on record for this
  project).
- **Get a second opinion** - run Step 5.5 before applying.
- **Something else** (free text) - exclusions ("nothing about X", "nothing modified this month"),
  `fix links only`, or `keep all`; apply whatever remains after honouring the reply literally.

No further per-item prompting after this reply, regardless of branch taken.

## Step 5.5 - Second opinion (only if chosen)

Dispatch 2 subagents (`model: 'sonnet'`), the full apply set in each prompt:

- **Refuter**, pointed at the destructive items only (archives, drops): default to "do not act"
  on any item it's not confident about.
- **Reviewer**, pointed at the additive/structural items (re-index proposals, link fixes, dedupe
  keeper choice): checks the audit's judgment calls, not just its mechanics.

Any item either subagent flags as refuted/uncertain drops out of the apply set and is named in
the Step 7 summary as excluded. Everything neither flags proceeds to Step 6. This does not
re-open the question from Step 5 - it resolves inline from the two reports.

## Step 6 - Apply

The only step that mutates the memory directory. Order matters and is not optional - it is what
keeps the index and the files from ever falling out of step (see CLAUDE.md's Memory Discipline:
"never delete an index line while its memory file still exists on disk").

For each archive/drop item, in this exact order:

1. Move the file to `<memory-dir>/archive/` (never plain-delete).
2. Verify the move: the file exists at the new path and no longer exists at the old one.
3. Only after that verification, remove its `MEMORY.md` line.
4. Grep remaining memory files for `[[<name>]]` references - replace with a plain-text mention
   (drop the link syntax) rather than leaving a dangling link.

Never remove an index line before its file has been confirmed moved (steps 1-2 before step 3,
every time) - that ordering is what makes the desync structurally impossible rather than merely
discouraged.

For a dedupe merge specifically: before step 1, check the loser's body for any detail not already
in the keeper's body (a distinct example, a distinct "Why"). State explicitly, per entry, either
"nothing unique to fold" or the exact detail folded and where it landed in the keeper - then fold
it in before archiving. This applies to every dedupe-loser entry, listed or not, since under
auto-apply nobody reads a list before the write happens.

For each `orphan-file`: add a `MEMORY.md` line pointing to it (summarized from its `description`
frontmatter). For each `orphan-index-entry`: remove the dangling line (safe - no file exists to
desync against).

For `fix links only` or an equivalent free-text reply: repair each broken `[[name]]` in place
(correct it if it's a typo of an existing memory's actual name, otherwise drop the link syntax
and leave the sentence readable) - no files archived.

**Mandatory final check, before Step 7:** re-run Step 2's index/file cross-check over the whole
directory. If anything still mismatches (an index line with no file, or a file with no index
line), stop and surface it in the Step 7 summary instead of reporting success - do not let a
partial apply pass as clean.

Never touch `MEMORY.md` structure beyond the lines this run's apply set covers.

## Step 7 - Post-apply summary

Deliver as the turn's FINAL message, no tool call after it (same swallow risk as Step 5 - this
message is the report the dev is meant to read). Short and auditable, not a re-run of the audit:

- What moved: dedupe merges (loser -> keeper, folded-detail note), drops, re-indexed orphans,
  link fixes.
- Any item excluded by Step 5.5, named with the reason.
- Step 2's counts for both desync directions (`orphan-file`, `orphan-index-entry`), before and
  after apply.
- Result of the mandatory final consistency check (clean, or what still mismatches).

## Non-goals (v1)

- No cross-project sweep - one project's memory directory per run. Running it project-by-project
  is the intended workflow, same as `/cleanup-todos` being per-repo.
- No auto-drop past the Step 5 question - the one question gates the whole apply set; nothing is
  ever plain-deleted, only archived.
- No scheduled/cron trigger - manual invocation only.
- No rewriting a memory's *content* for style/length during this pass - a kept memory's body is
  only ever edited to fold in a dedupe-loser's unique detail (Step 6) or repair a link; anything
  more is a separate, differently-gated edit.
