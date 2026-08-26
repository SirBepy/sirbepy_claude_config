# Comment-noise check

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2).
Read on demand - not part of either skill's always-loaded body.

The cap: **2 lines typical, 4 lines hard, per comment block**, and added comment
lines under **~25%** of a file's added lines once that file adds 20+ lines (below
that the ratio is noise - a 5-line constants file with one 2-line why-comment is
fine, and the block cap already covers it). Matches the global CLAUDE.md Code
Style rule; if a number changes, change it in both. A block earns its place ONLY
by naming a constraint, a gotcha, or a measurement the code cannot show.
Restating the next line, narrating steps, labelling JSX sections, or parking
design rationale in code all fail; rationale goes in the PR body.

**Timeless Present.** A comment is written for someone meeting the code for
the first time, so it states what IS, never what changed. `// Added mutex to
fix race condition` is a changelog entry stranded in the source: six months on
the reader does not know which race, cannot tell whether the mutex is still
needed, and does not care that it was added. `// Mutex serializes cache access
from concurrent requests` states the invariant instead. Same instinct as the
rationale rule above, different axis: that one is about length, this one is
about tense. Checked by `comment-tense.sh` in the same prefilter, which is
deliberately high-precision and low-recall - it flags a change verb opening a
comment block (`Added`/`Removed`/`Renamed`/`Replaced`/`Refactored`/`Migrated`/
`Bumped`), plus `we decided to`, `unlike the old`, `as of this change` and
`TODO from the`. Measured 2026-08-22 over the whole tracked tree as one
all-added diff: **1 hit in 86 code files**, and that one is arguably genuine.
Bare `no longer` and `previously` were tried and CUT - they produced 36 hits,
nearly all legitimate, because both are ordinary ways to state a current
invariant. Known recall gap: inside an unbroken run of `//` lines only the
first is checked, which is the price of not flagging wrapped continuations.

**Write within the cap - this is a writing budget, not just a gate checked
after the fact.** Before writing a block, decide if it names a constraint,
gotcha, or measurement the code can't show; if not, don't write it.
- Rust trap: the prefilter's `#` regex counts `#[attribute]` lines as
  comments too, so a 4-line `///` doc block sitting right above one attribute
  already trips `longest >= 5` - budget 3 doc lines max above an attribute.
- Never reword an untouched comment - restoring it verbatim keeps it out of
  the added-lines count entirely; rewording it to "say the same thing" adds
  it back in for no reason.
- If step 5a flags a block anyway: CUT it, never reword it. Rewording is what
  turns one flag into six rounds of re-running the prefilter.

1. **Mechanical prefilter** (one command, no judgment, run it verbatim via
   Bash). Lives in `skills/commit/comment-noise.sh`, a real script rather than
   inline in this file - skill-argument substitution rewrites a bare `$0`
   found in a skill's own body text, which used to clobber awk's `$0` ("whole
   current line") every time this was pasted inline. A script on disk is
   never passed through that substitution.

   - **Working-tree mode** (`/commit`'s step 5a, diffing the not-yet-committed
     change): `git diff HEAD` alone is blind to untracked files - a brand-new
     file has no `HEAD` entry, so it never appears in that diff and would
     silently read as clean. The script folds every untracked file in scope
     before running the same awk over the combined stream:
     ```
     bash skills/commit/comment-noise.sh <file> <file> ...
     ```
   - **Range mode** (`/create-pr`, comparing the branch against its base -
     a branch diff already contains every file the branch added, so
     untracked files aren't a concern here). Diffs `<base>` against the
     working tree, not `<base>..HEAD`, so a re-run after step 2b's trims
     sees the trim instead of reporting the same stale hits:
     ```
     bash skills/commit/comment-noise.sh --range <base>
     ```

   No output = `clean` in either mode, and the check is done. Do not read a
   single comment. Regex covers `//`, `/* */`, `*`, `#`, `--`, and `<!--`; a
   language using none of those line-comment markers isn't covered - flag it
   by eye if one shows up. The `#` branch deliberately excludes `#[` and `#!`
   so Rust attributes and shebangs count as code, not comments.
   `.md`/`.mdx` files are skipped entirely - a `#` there is a heading, never
   a comment, and the cap is a code rule (todo 340). Generated output is
   skipped by filename suffix too (`.freezed.dart`, `.g.dart`, `.pb.go`,
   `.pb(enum|json|server).dart`, `_pb2.py(i)`, `.generated.*`) since no
   author can act on a flagged block there - never by directory name, so a
   hand-written file under a `generated/` folder still gets checked (todo 456).
2. **Judge only the flagged files.** Read those diffs and list the specific
   offending blocks (`file:line`, first line, line count). A 5+ line block that
   genuinely documents one hard constraint can survive - say so and why. Do not
   review comments in files the prefilter didn't flag; they are in budget.
   A block flagged only because it moved verbatim into a new file (a pure code
   move, wording unchanged) is not new noise - confirm via
   `git show HEAD:<old-file>` before dismissing it. The exemption covers
   unchanged text moved as-is only; a newly authored comment sitting in a
   moved file is still a hit.
