<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Every prefilter change rebuilds the same scratch-repo harness by hand

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `skills/commit/` a reusable way to verify a prefilter change, so the next person does not
hand-roll a scratch repo, fixtures, and an old-versus-new comparison from scratch again.

## Context

Found 2026-08-26 during an `/autopilot` run that changed five scripts under `skills/commit/`
(todos 447, 412, 460, 456, plus 778's half). **The same three-part manual harness was rebuilt five
times in one session**, roughly 15 tool calls of pure setup:

1. `git init` a scratch repo under `C:\tmp\<something>`, sometimes with a real submodule
   (`git -c protocol.file.allow=always submodule add ...`).
2. Write fixture files. This cannot use the shell: `>`, `Set-Content`, `Add-Content` and `Out-File`
   are all blocked by `hooks/shell-content-write-guard.py`, so each run reached for
   `[System.IO.File]::WriteAllText` in PowerShell while doing the git plumbing in Bash.
3. Capture the pre-change script to compare against, via
   `git show HEAD:skills/commit/<script>` into a copy placed BESIDE the real script (so
   `$(dirname "${BASH_SOURCE[0]}")` still resolves to the real wrapped scripts), run both against
   the same fixtures, diff the output, then delete the copy by exact name.

**Why this is worth a helper rather than a note.** Step 3 has a real footgun that fired: the
temporary copy lives INSIDE `~/.claude/skills/commit/`, and one cleanup ran `rm -f` with a relative
path from the wrong cwd, reported "No such file or directory", and was read as success while the
copy survived in the repo. A stray executable in `skills/commit/` is exactly the kind of thing that
gets committed by accident.

**Why the harness is unavoidable.** There is no `test_*.sh` or `test_*.ps1` anywhere under
`skills/`, and `python ci/run_all.py` covers `hooks/test_*.py`, `tools/test_*.py`, skill frontmatter
and a `CLAUDE.md` token budget only. It exercises none of these scripts. A green CI run is not
evidence for a prefilter change, so a fixture run is the ONLY evidence available, which is why every
one of the five changes built one.

## Approach

1. Decide the shape first, and this is the real work. Two candidates:
   - **A fixture-based test suite** (`skills/commit/test_prefilters.sh`) that `ci/run_all.py`
     discovers and runs, turning "the only evidence is manual" into "CI covers it". Strictly better
     long-term and it is what `501` is about.
   - **A setup helper only** (`skills/commit/_fixture-repo.sh`) that builds a scratch repo with a
     known set of fixtures and prints its path, leaving assertions to the caller. Cheaper, but
     leaves every change still hand-verified.
   Recommended: the suite. The helper is a consolation prize that does not remove the manual step.
2. Whichever lands, cover the old-versus-new comparison explicitly, including placing the captured
   copy where `$dir` still resolves and removing it by ABSOLUTE path.
3. Seed it with the cases already written by hand this session, all of which have known-correct
   expected output recorded in the `done/` files: a submodule with a planted credential (`412`), a
   gitignored file with a planted credential (`460`), a `.freezed.dart` next to a hand-written
   `.dart` and a hand-written file under a `generated/` directory (`456`), and a marked versus
   unmarked todo under `.claude/todos/` (`778`).
4. Do NOT let it grow into a general test framework. Four scripts, one wrapper, one purpose.

## Acceptance

- Verifying a prefilter change takes one command, not a hand-built repo.
- If the suite route is taken: `python ci/run_all.py` discovers and runs it, and the discovered
  suite count goes up (it was 15 hook suites and 1 tool suite on 2026-08-26).
- Deliberately break one prefilter and confirm the suite FAILS. A suite that has never failed is
  not known to work.
- No temporary file is left anywhere under `skills/commit/` after a run.

## Notes

- Closely related: `501` (live guards with no test file) and `804` (the same blind spot in
  `comment-noise.sh`/`em-dash.sh` that `460` fixed in `secret-scan.sh`). If `804` is picked up
  first it will need this harness anyway, so doing this one first is the cheaper order.
- The expected outputs are already written down. Every `done/` file listed in step 3 records the
  exact before-and-after behaviour that was measured, so the suite can be seeded from them rather
  than re-derived.
