<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "git_c", "overlap-check", "_prefilter-lib". done/813 folded
     four of the five copies; this is the fifth, left out deliberately. Not a duplicate of 813. -->
# overlap-check.sh still carries its own git_c, because its --repo parsing genuinely differs

**Type:** task
**Origin:** ai

## Goal

Close out the fifth `git_c` copy that todo `813` deliberately left standing, either by reconciling
`overlap-check.sh`'s argument parsing with the shared helper or by recording that it stays separate.

## Context

Filed 2026-09-02 as the honest remainder of todo `813`. That todo's Acceptance said "One definition,
sourced by all five." Four landed in `skills/commit/_prefilter-lib.sh` (`comment-noise.sh`,
`comment-tense.sh`, `em-dash.sh`, `secret-scan.sh`). The fifth, `skills/commit/overlap-check.sh`,
did not.

**The four-of-five outcome was authorized by the orchestrator in the dispatch, not decided
unilaterally by the builder**, and the dispatch's wording was: "Check its `repo` handling is
genuinely identical before folding it in rather than assuming from the one-line match. If it is NOT
identical, leave it alone and say so - four of five is a better outcome than a broken fifth."

The builder checked and reported two concrete divergences:

- `overlap-check.sh` accepts `-C` as an alias for `--repo`; the other four do not.
- it reads `${2:-}` where the other four read `$2`.

`813` itself also flagged this script as the odd one out for two structural reasons: it is not
wrapped by `prefilter-gate.sh`, and it has its own exit-code contract (0 clean / 1 real hit / 2
could-not-run) that the prefilter family does not share.

**This is deliberate leftover work, not a defect.** Nothing is broken today. The reason to settle it
is that `813` existed because a fifth copy appearing independently is what turns a disclosed
trade-off into a default, and leaving exactly one copy behind recreates that condition.

## Approach

1. Read `skills/commit/_prefilter-lib.sh` first, specifically `parse_repo_arg` and its
   `PREFILTER_ARGS` return convention. `813`'s builder noted that a function cannot shift its
   caller's `$@`, which is why the trimmed args come back through an array - that constraint shapes
   any fold.
2. Decide between two real options rather than assuming the fold is right:
   - **Fold it in**, teaching the shared parser the `-C` alias. Cheap, but it widens the shared
     parser's surface for one caller's convenience, and `-C` is meaningful to `git` itself, so the
     alias is not obviously worth generalizing.
   - **Keep it separate and say so** in a comment naming both divergences, so the next reviewer
     finds the answer instead of re-filing this. Given the script's separate exit-code contract and
     that it is not part of the prefilter gate, this is a defensible end state.
3. If folding: `overlap-check.sh` gates every commit in every repo on this machine and has no test
   suite. Prove identical behaviour before and after for no `--repo`, an explicit `--repo`, an
   explicit `-C`, and a path resolving to a different repo. Capture before-behaviour via
   `git show HEAD:skills/commit/overlap-check.sh` into a copy placed BESIDE the real script so its
   own directory resolution still works.
4. A missing or unreadable helper must fail LOUDLY. A silently unsourced `git_c` makes the gate pass
   on an empty diff, which is the silent-clean bug class `412`, `447` and `460` were all about.

## Acceptance

- A decision exists in writing, fold or keep-separate, naming the two divergences.
- If folded: all five scripts share one definition, and the four behaviours in step 3 are proven
  identical before and after for `overlap-check.sh` specifically.
- If folded: a deliberately renamed helper makes the script fail loudly, proven by running it.
- `python ci/run_all.py` exits 0, noting plainly that it does not cover any of these scripts, so a
  green run is not evidence either way.

## Notes

- Worth roughly a 3. Pure tidiness with a real recurrence argument behind it, on untested scripts
  that gate every commit - which is exactly the risk/benefit shape that made `813` a
  trigger-not-now todo in the first place.
- `810` proposes the fixture harness that would make step 3's proof cheap. Doing `810` first would
  make this materially safer.
