<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=4, reconfirm-count=2, content-hash=8d7a1b81 -->
<!-- duplicate-checked -->
# The git_c helper is defined verbatim in five separate scripts

**Type:** task
**Origin:** ai

## Goal

Collapse the five identical `git_c()` definitions under `skills/commit/` onto one sourced helper,
so a change to how those scripts reach a foreign repo cannot land in some of them and miss others.

## Context

Found 2026-08-26 by `/code-check`'s independent reviewer, confirmed by
`grep -l "git_c()" skills/commit/*.sh` returning exactly five files.

The identical one-liner

```sh
git_c() { if [ -n "$repo" ]; then git -C "$repo" "$@"; else git "$@"; fi; }
```

now exists in `comment-noise.sh`, `comment-tense.sh`, `em-dash.sh`, `secret-scan.sh` (all four
added in one commit, `0292e46`, todo 447) and `overlap-check.sh` (a fifth copy in a new file,
`a45a8bd`, todo 474).

**Not urgent, and the todo says so on purpose.** Five copies of one line is cheap; the cost is
drift, and drift only bites when someone edits the rule. But the fifth copy is the signal worth
acting on: the first four were a deliberate, disclosed choice made in a single commit ("no shared
helper file existed to reuse, so the same small block is duplicated 4x"), while the fifth arrived
independently, in a different commit, for a different todo. That is the point where a pattern
stops being a considered trade-off and starts being the default.

**A concrete hazard already exists**, which is what tips this past pure tidiness: todo `812`
records that `em-dash.sh`'s path handling is wrong for absolute-path arguments. Whatever
normalization fixes it will very likely need to live next to `git_c`, and with five copies there
are five places to put it and four chances to forget one.

## Approach

1. **Trigger, not necessarily now:** do this when `812` or `804` needs to touch the repo-resolution
   logic anyway, or when a sixth copy appears. Extracting for its own sake spends risk on scripts
   that gate every commit in every repo, with no test suite, for no behaviour gain.
2. When it happens: create `skills/commit/_git-c.sh` (dot-sourced, not a module - these are scripts
   invoked directly by path, never imported) holding `git_c` and the `--repo` argument parse, since
   those two always appear together. `skills/_shared/pixel_utils.py` is the precedent for a shared
   file in this tree, though it is Python and imported rather than sourced.
3. Sourcing needs a path that resolves regardless of the caller's cwd. Each script already computes
   its own directory for other reasons; reuse that rather than adding a second mechanism, and make
   sure a missing helper fails LOUDLY. A silently unsourced `git_c` would make every one of these
   gates pass on an empty diff, which is exactly the silent-clean shape todos `412`, `447` and
   `460` were all filed about.
4. `overlap-check.sh` is the odd one out: it is not wrapped by `prefilter-gate.sh` and has its own
   exit-code contract. Check its `repo` handling is genuinely identical before folding it in, rather
   than assuming from the one-line match.

## Acceptance

- One definition, sourced by all five.
- Each of the five behaves identically before and after, for: no `--repo`, an explicit `--repo`, and
  a path resolving to a different repo. Capture before-behaviour via `git show HEAD:<script>` into a
  copy placed BESIDE the real script so `$dir` still resolves, and diff the outputs.
- A deliberately missing or unreadable helper makes the scripts fail loudly, proven by renaming it
  and running one.
- `python ci/run_all.py` passes. State plainly that it does not cover any of these scripts, so a
  green run is not evidence either way.

## Notes

- Same shape as `794` (a duplicated fallback across the two `skills/close/` PowerShell scripts,
  also filed as trigger-not-now). If both ever get done, do them separately: different languages,
  different sourcing mechanics, no shared solution.
- `810` proposes the fixture harness that would make the acceptance above cheap to prove. Doing
  `810` first would make this one materially safer.
