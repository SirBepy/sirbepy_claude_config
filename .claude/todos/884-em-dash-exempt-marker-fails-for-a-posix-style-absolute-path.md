<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "em-dash", "exempt", "absolute path". done/812 fixed the
     Windows-style absolute-path form; this is the remaining POSIX-style shape. Not a duplicate. -->
# em-dash.sh's exempt marker still fails for a `/c/Users/...` POSIX-style absolute path

**Type:** task
**Origin:** ai

## Goal

Decide whether `skills/commit/em-dash.sh`'s `<!-- em-dash-exempt -->` handling needs to cover
git-bash POSIX-style absolute paths, and either fix it or record that the shape is out of scope.

## Context

Found 2026-09-02 by todo `853`'s builder while constructing `812`'s absolute-path regression test.
`812` fixed the Windows-style absolute form (`C:/Users/...`); this is the sibling shape it did not
cover.

Passing a git-bash style path such as `/c/Users/tecno/.claude/.claude/todos/10-marked.md` leaves the
exempt-marker key unmatched against the diff header, because git normalizes the `+++ b/` path to the
Windows drive-letter form (`C:/Users/...`) while the raw argument stays POSIX-style. The exemption
silently fails to suppress a hit, for that path shape only.

**Two facts that bound how much this matters, both from the finder:**

- Windows-style absolute paths - the shape `prefilter-gate.sh` and the PowerShell callers actually
  pass - are unaffected and verified working.
- The finder explicitly did NOT file this itself, on the grounds that it was a tangent from its own
  test construction and **not proven to be a shape any real caller uses.** That judgement is on
  record and may well be right.

**The failure direction is SAFE**, same as `812`: it FLAGS a file that should have been exempt, a
false positive that blocks a commit, never a false negative that lets an em dash through.

So the first question is not "how do we fix it" but "does anything reach it". This repo's own
builder preamble tells every agent the file arguments "can be relative or absolute", and agents run
commands through both a Bash tool and a PowerShell tool on this machine, which is exactly how a
`/c/...` argument would arise.

## Approach

1. **Answer the reachability question before writing any code.** Grep this repo for every caller
   that passes a path into `em-dash.sh` or `prefilter-gate.sh` and record which form each one
   produces. If no caller can produce a POSIX-style absolute path, the correct outcome is a note in
   the script saying so, not a fix.
2. If it is reachable: normalize with the same mechanism `812` used rather than adding a second one.
   `812` resolved tracked paths via `git ls-files --full-name` and untracked-visible ones via
   `git ls-files --others --exclude-standard --full-name`; check whether either already emits the
   drive-letter form for a POSIX-style input, which would make this a one-line change.
3. Whatever lands, re-prove `812`'s four acceptance cases (marked/unmarked, relative/absolute,
   in-scope/out-of-scope, tracked/untracked). They are the regression surface.

## Acceptance

- The reachability question is answered with a list of actual callers and the path form each
  produces, not an assumption.
- If fixed: a marked todo passed as `/c/Users/...` is exempt, and an unmarked one is still flagged.
- `812`'s four acceptance cases all still pass, both path forms.
- If NOT fixed: the decision and its reasoning live in the script or a sibling doc so this does not
  get re-filed.

## Notes

- Worth roughly a 3. Real and reproduced, but possibly unreachable, and the safe failure direction
  means nobody gets a bad commit out of it.
- Same family as `812` (done) and `853` (done). All three touch `skills/commit/em-dash.sh`, which
  now dot-sources `skills/commit/_prefilter-lib.sh` - read that first, the file layout changed on
  2026-09-02.
