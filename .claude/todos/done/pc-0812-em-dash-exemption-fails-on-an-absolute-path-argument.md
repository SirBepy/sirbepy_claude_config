<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=3, content-hash=a823792f -->
<!-- duplicate-checked -->
# em-dash.sh's exempt marker is ignored when the file is passed as an absolute path

**Type:** task
**Origin:** ai

## Goal

Make `skills/commit/em-dash.sh`'s `<!-- em-dash-exempt -->` handling work for an absolute path
argument, not only a repo-relative one.

## Context

Found 2026-08-26 by `/code-check`'s independent reviewer against commit `f647216` (todo `778`'s
shipped half), and reproduced by the orchestrator before filing.

`exempt_list()` (`skills/commit/em-dash.sh:20-27`) prints back the caller's RAW argument string when
it finds the marker. The awk pass keys its lookup on `f`, taken from the diff's `+++ b/<path>`
header (`em-dash.sh:31`), which for a tracked file is always repo-root-relative no matter how the
caller wrote the argument. Pass an absolute path and the exempt set is keyed on the absolute string
while the lookup is keyed on the relative one, so it never matches and the marker is ignored.

Reproduced on a scratch repo, same file, same marker, same em dash, only the argument form differing:

```
$ bash em-dash.sh .claude/todos/10-marked.md          # relative
exit=0                                                 # exempt honoured, no output

$ bash em-dash.sh /c/tmp/.../.claude/todos/10-marked.md   # absolute
.claude/todos/10-marked.md:4                           # exemption silently ignored
```

**This is reachable in normal use, not contrived.** `refs/builder-preamble.md` was edited in the
same session (`e61d305`) to tell every builder "the file arguments themselves can be relative or
absolute", and `/mega-todos`' injected commit block passes absolute paths on purpose because a
builder's repo root is usually not `~/.claude`.

**The failure direction is SAFE, which is why this is not urgent.** It FLAGS a file that should have
been exempt: a false positive that blocks a commit, never a false negative that lets an em dash
through. Nobody gets a bad commit out of this; someone gets a confusing red gate on a file they were
told is exempt.

**Why the original verification missed it:** the fix was tested against relative paths only. Testing
one argument form and declaring the feature done is the actual lesson here.

## Approach

1. Reproduce first, both forms, exactly as above. **Do not write a fix before seeing the absolute
   form fail** - the whole point is that it looks like a working feature.
2. Normalize the emitted path to whatever form the diff header will actually carry. **Note the trap
   that makes this a judgment call rather than a one-liner: the two branches disagree.** A TRACKED
   file goes through `git_c diff HEAD -- "$@"`, whose header is always repo-relative. An UNTRACKED
   file goes through `git_c diff --no-index -- /dev/null "$f"`, whose header echoes the argument
   AS PASSED, so an absolute argument yields an absolute header. A single normalization applied to
   both will fix one and break the other.
3. Candidate: resolve each path to repo-relative with `git_c ls-files --full-name -- "$f"` for
   tracked files, and leave an untracked path in its as-passed form. Verify that guess rather than
   trusting it; `--full-name` returns nothing for an untracked file, which is a usable signal for
   which branch a path will take.
4. Check whether `comment-noise.sh` and `secret-scan.sh` need the same treatment. They do not have
   an exemption list today, so probably not, but `804` may add one to `comment-noise.sh` and would
   inherit this bug if it copies the current shape. Cross-reference it there.

## Acceptance

- A marked file under `.claude/todos/` is exempt via BOTH a relative and an absolute path.
- An UNMARKED file under `.claude/todos/` is still flagged via both forms.
- A MARKED file outside `.claude/todos/` is still flagged via both forms (the scope restriction from
  `778` must survive).
- The untracked-file path still works: a brand new, never-added marked todo is exempt.
- `--range <base>` mode still behaves as before.
- All four of the above are proven, not just the exemption. Only proving the happy path is what let
  this bug ship.

## Notes

- Filed as class 3 (judgment) by `/code-check` because the tracked-versus-untracked asymmetry in
  step 2 means there is a real decision inside it, not a mechanical substitution.
- No mechanical test covers this. There is no `test_*.sh` anywhere under `skills/`, and
  `python ci/run_all.py` does not exercise these scripts, so a green CI run is not evidence.
  `810` proposes the harness that would have caught it.
- Parent: `778`, still open on its own item 4 (a CI case, which writes under `hooks/`). Deliberately
  filed separately rather than folded in, since `778` is parked on an unrelated blocker.
- Fixed (773418d). exempt_list now normalizes to whatever form the diff header will actually carry. Deviation from the todo candidate worth knowing: the untracked branch is normalized via git ls-files --others --exclude-standard --full-name rather than left as-passed, because empirical testing showed a discovered-untracked file diff header comes from ls-files output and is always repo-relative, so the todo assumption held only for the separate gitignored fallback. git_c also moved to top level since exempt_list needed it and the --range branch never defined it. The POSIX-style /c/Users/... path shape is still unfixed and is filed as 884.
