<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# comment-noise prefilter: false positives on moved code, grown blocks, and CSS `#id` selectors

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the comment-noise prefilter from demanding edits to code that was only MOVED, stop it missing
comment blocks that grow past the hard cap a couple of lines at a time, and stop it misreading CSS
ID selectors as shell-style comment lines.

## Context

Both observed on 2026-08-08 in `claude_usage_in_taskbar` during a session with 15 commits.

**False positives on pure moves.** The prefilter counts ADDED lines from the diff. A file-split
refactor makes the new file 100% added lines, so every comment that MOVED with the code is counted
as newly written. It fired three times on pure moves:

- `permission-modal/resurface.ts` at 34/120 (28%), longest run 10
- `preview-panel-document.ts` at 22/70 (31%), longest run 6
- `accounts/identity.rs` at 30%, docs moved from `credentials.rs`

Verified they were pre-existing: `git show HEAD:src/views/sessions/permission-modal/index.ts` showed
the source file already carried 50 comment lines with a longest run of 17. Obeying the prefilter
literally would have meant rewriting comments inside a refactor whose whole contract was "pure move,
no rule changes", which is a worse outcome than the flag.

The skill's instruction is "Flagged = trim the offending blocks now, don't ask", with no exemption,
so the correct action currently requires overriding the skill on judgement every time.

**False negative on grown blocks.** The run counter counts CONSECUTIVE ADDED comment lines, not the
size of the resulting block. A module doc that grows from 3 lines to 5 by adding 2 interleaved lines
registers as a run of 2 and passes clean, while the file now violates the 4-line hard cap.
Confirmed: `src-tauri/src/daemon/hooks_server/messages.rs` passed the prefilter, and a later
`/code-check` pass correctly flagged its 5-line module doc.

**False positives on CSS `#id` selectors.** The regex `#[^[!]` (meant to catch shell/Python/Ruby
`#comment` lines while excluding `#!` shebangs) also matches CSS ID-selector lines like
`#modal-host {` or `#modal-host-card-slot {` - a plain `#` at the start of a code line is
indistinguishable from a `#`-comment to this pattern. On `claude_usage_in_taskbar`'s
`src/shared/modal.css` (2026-08-08), this inflated the flagged ratio to 41% (16/39) on a file whose
REAL comment content was ~9 lines / 24% (already under the per-block cap) - every one of the ~7
`#modal-host...{` selector lines got miscounted as a comment. Verified by hand-classifying every
added line (`git diff --no-index -- /dev/null <file>` piped through the regex with a debug print
per line) - the false positives were exactly the `#`-prefixed selectors, nothing else. Treated as a
verified false positive and proceeded without further trimming (already-legitimate comments, cap
correctly satisfied once the miscounted lines are excluded).

## Approach

In `~/.claude-personal/skills/commit/comment-noise.md` (the one place the cap and the command are
defined; `SKILL.md` step 5a and `/create-pr` step 2b both mirror it, so update all three together):

1. **Moved code.** Add a documented exemption: before trimming, check whether the flagged comments
   exist verbatim at `HEAD` elsewhere in the repo (e.g. `git show HEAD:<old-path>`, or
   `git log --follow` / `git diff -M` rename detection). If they are moved rather than new, record
   that and skip the trim. Prefer teaching the command `-M`-style rename awareness over a prose
   caveat, since a prose caveat gets skimmed.
2. **Grown blocks.** Complement the added-run counter with a check on the RESULTING block in the
   file, not just the added slice: for each hunk touching a comment block, measure the full
   contiguous comment run in the post-image and compare it against the 4-line hard cap.
3. **CSS `#id` selectors.** Narrow the `#`-comment branch of the regex so it only fires when the
   file extension is a shell/Python/Ruby-family language (`.sh`, `.py`, `.rb`, `.ps1`, etc.), or
   require the line to match `^\s*#\s` (a `#` followed by whitespace, which a bare CSS selector
   `#id {` never has) rather than the current bare `#[^[!]`. Keep the ratio rule as-is otherwise;
   it is the per-block cap that matters most.

## Acceptance

- A pure file-split refactor no longer produces a flag that must be overridden by judgement.
- A comment block that grows from 3 to 5 lines IS flagged.
- A `.css` file whose only "comment-like" lines are `#id { ... }` selectors is no longer flagged
  for a ratio it doesn't actually have.
- The cap numbers themselves stay defined in exactly one place, with `SKILL.md` and `/create-pr`
  still referencing rather than restating them.

## Notes

- Re-verified 2026-08-08: premise still holds.
- 2026-08-08 (later same day): added the CSS `#id`-selector false-positive case, found on
  `claude_usage_in_taskbar`'s `src/shared/modal.css`.
- Duplicate of 45 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
