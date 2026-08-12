# Commit edge cases

Read on demand from `/commit` - merges, partial staging, and backdating are
rare paths, not part of the normal flow.

## Merge commits

Merges go through this skill's flow too - never a raw `git merge` + push that lands an unreviewed merge commit, never `git commit` directly, and never a raw `git cherry-pick` either: it creates a commit the same way `git commit` does, bypassing the marker gate just as easily. Make sure this session's commit-marker exists before it runs (see the commit-guard section above). Unlike a merge, a cherry-pick's message usually keeps the original commit's message as-is - it's carrying forward an already-reviewed commit, so there's no `MERGE:`-style rewrite; the marker is the only thing it's missing.

- **When a merge is needed:** a non-fast-forward push (remote has commits local never pulled) or deliberately absorbing superseded remote history into a new line of work.
- **Prefer the least-surprising resolution.** If a plain `git pull --no-rebase` merges cleanly and the result is what you want, take it. Only reach for `git merge -s ours <remote-ref>` when you intentionally want to KEEP local content and record the remote history as absorbed-but-superseded (e.g. an old framework version preserved on a legacy branch).
- **Message:** use a `MERGE:` prefix and state plainly what was absorbed and where the superseded content still lives, e.g. `MERGE: absorb remote React v2.7 into history (content preserved on legacy/react-v2; Flutter tree unchanged)`.
- **Hard stops still apply.** `git rebase` (rewrites shared history) and force-push are NOT merge resolutions - do not reach for them to avoid a merge commit. In an autopilot/unattended run, force-push is a hard stop; park it rather than guessing.

## Splitting one file across commits (partial staging)

When a single file holds changes belonging to different commits, stage the specific hunks - do NOT commit the whole file, and do NOT mutate the working tree (delete progress → commit → undo) to fake it.

- `git add -p` is the usual way, but it's INTERACTIVE and hangs in this non-interactive shell. Do not use it.
- Non-interactive route instead:
  1. `git -C <path> diff <file> > <tmp>.patch` (or `diff HEAD <file>`).
  2. Edit the patch: delete the hunks you don't want. Keep the `diff --git`/`index`/`---`/`+++` header lines and the `@@` line of each hunk you keep. Don't bother renumbering `@@` counts.
  3. `git -C <path> apply --cached --recount <tmp>.patch` (`--recount` tolerates off `@@` counts from hand-trimming). If it still rejects on context mismatch, re-dump and re-trim rather than forcing.
  4. Verify the partially-staged result compiles/lints on its own (the committed state must build without the unstaged remainder), then commit.
- This is surgical and leaves the working tree untouched - prefer it over restore-edit-amend whenever you need exact lines.
- **Exception to step 8's pathspec rule:** a hunk-level split genuinely needs the index (that's what `apply --cached` stages into), so it is the one case that commits FROM the index instead of by pathspec. Re-run `git diff --cached --stat` immediately before committing to confirm the index holds ONLY the hunks you just staged - if a concurrent session added anything else in between, stop and re-isolate rather than committing whatever the index now contains.

## Backdating commits

- When the user asks for a specific commit time, jitter it to look organic:
  - Always randomize the seconds (00-59).
  - Shift the minutes by a few (typically +/- 1-4) from whatever was requested.
  - Example: user says "27 minutes after the previous commit" → don't use exactly :45:00; use :43:17, :46:52, etc.
- Apply the same timestamp to both author and committer dates: `GIT_COMMITTER_DATE="..." git ... commit --date="..." ...`.
- Confirm the resulting timestamp back to the user after committing.
