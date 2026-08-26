<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `/commit` step 8's hunk-level overlap check should be a script, not prose to re-derive

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop every commit from re-implementing the unpushed-overlap check by hand. It is a precise
algorithm, it is easy to get wrong, and it was gotten wrong twice in one session.

## Context

Hit 2026-08-21 during an `/auto-do-todos` run in `hubbub` (11 commits, five repos).

`skills/commit/SKILL.md` step 8's "Unpushed-overlap check (hunk-level, not file-level - see todo
368)" specifies a real algorithm in prose: list unpushed shas, intersect names as a pre-filter, then
for each surviving file parse each hunk's `@@ -a,b @@` old-side range, skip `b=0` pure additions,
`git blame -L a,a+b-1 HEAD -- <file>`, and only count a match between a blamed sha and a candidate
sha as a real hit.

Across that run the loop was hand-written **four separate times**, and the sha-comparison step was
wrong in two of them: the candidate shas from `git log --format=%h` are 7 chars while `git blame`
prints 8, so a naive `case "$c" in "$s"*)` compared them in the wrong direction and silently
reported zero hits. It was only caught by eyeballing the raw blame output and noticing a candidate
sha sitting right there in a list the script had just called clean.

A check whose failure mode is "silently reports no overlap" is exactly the wrong thing to leave as
prose. The whole point of todo 368's hunk-level upgrade was to make this check trustworthy enough
to stop asking about file-level noise; a mis-implementation quietly returns it to useless.

## Approach

1. Add `skills/commit/overlap-check.sh`, same shape as the existing `comment-noise.sh` /
   `em-dash.sh` / `secret-scan.sh` prefilters: takes the commit's pathspec, prints nothing when
   clean, prints real hits (file, line range, blamed sha, that sha's subject) and exits non-zero
   when it finds one.
2. Normalise sha length explicitly inside it (compare via `git rev-parse` full hashes, not string
   prefixes) so the bug above cannot recur.
3. Rewrite step 8's bullet to call the script and describe only the DECISION (interactive: ask via
   `AskUserQuestion`; unattended: proceed and record), keeping the algorithm in exactly one place.
4. Do NOT fold it into `prefilter-gate.sh`. That gate's contract is "exit non-zero blocks the
   commit", and a real overlap hit is not always a block: unattended runs are explicitly told to
   proceed and record. Keep it a separate call with its own exit-code meaning, and say so in the
   script header.

## Acceptance

- Step 8 contains no `@@` parsing or `git blame -L` instructions.
- The script reports a known-overlapping pair correctly, and reports clean for a file that
  file-matches an unpushed commit but shares no lines (the common false positive todo 368 removed).
- A 7-vs-8 char sha comparison cannot produce a false clean; add a fixture for exactly that.
- `python ci/run_all.py` passes.

## Folded in 2026-08-22: "interactive" is never defined, so the session self-classifies

Step 3 of the approach above says the rewritten bullet should describe the DECISION, and that
decision is exactly where a second gap sits. Step 8 branches on **interactive** (stop and ask via
`AskUserQuestion`) versus **unattended** (proceed and record in the run's summary), and defines
neither.

Hit for real on 2026-08-22 in `~/.claude`. A session that started as a live chat with the dev
answering a question card was still running hours later on scheduler daemon pings, at 01:40, with a
genuine hunk-level hit on an unpushed commit. Neither branch fits: it was not launched by
`/auto-do-todos` or `/autopilot`, so nothing declared it unattended, and the dev was plainly not
there to answer. It took the unattended branch and recorded the hit in its report, which is the
right outcome but was a judgement call the skill left to the session, and a different session would
have blocked on a card nobody would answer for hours.

This is the same shape as todo 261 (`done/`), where a run that STARTED interactive and became
unattended matched neither of `/pickup`'s two branches. That one is fixed for `/pickup` only; step 8
still has it, and so does anything else that branches on this distinction.

**What to decide, and it needs the dev's call, not an invented rule:** what signal marks a session
unattended when it was not launched that way. Candidates worth putting on a card: the invoking
prompt came from a scheduler or daemon rather than a typed message; a question card in this session
already expired unanswered (see the recorded ~30-minute `ask_user_question` timeout behaviour); or
an explicit per-session flag the dev sets. Prefer whichever is mechanically checkable, since a rule
that asks the session to judge its own attendedness is a rule that will be judged differently every
time.

Two extra acceptance lines if this is taken with the script work: the script or the step names the
signal explicitly, and a session running from a daemon ping resolves to the same branch every time
without judgement.

## Folded in 2026-08-22: a third run, and a second silent-failure path the text above misses

Third independent hit, so this is frequency and not a one-off: an `/auto-do-todos` run in
`hubbub-game-split-opinions` hand-wrote the loop **six more times**, once per commit. That is 10
hand-derivations across three runs and three repos in two days.

The new information is a second way this check fails silently, which the sha-comparison bug above
does not cover. The old-side range fed to `git blame -L` is not in the `@@` header - it has to be
computed from it, as `a` to `a+b-1` out of `@@ -a,b @@`. In this run that arithmetic was done by eye
for **eight hunks** across six commits. Get one wrong and `git blame` happily reports the shas for
whatever lines you did name, the comparison runs clean against them, and the output is
indistinguishable from a genuine no-overlap result. So the check has (at least) two independent
paths to a false clean: comparing shas wrongly, and blaming the wrong lines. Both belong inside the
script; neither is visible to a reader of the prose.

One useful negative data point for the interactive-vs-unattended section above: this run hit it
zero times. It was launched by `/auto-do-todos`, so the branch was declared and unambiguous. That
narrows the gap to sessions NOT launched by a runner skill, which is exactly the shape todo 261
described - worth saying on the card, since it makes the fix smaller than the section implies.

## Notes

- Related: [[473-cleanup-todos-calls-a-script-that-does-not-exist]]. Same class of defect.
- Related: 261 in `done/`, the same interactive-became-unattended gap, fixed for `/pickup` only.
- Worth noting for whoever picks this up: the check DID earn its keep once the comparison was fixed.
  In that run it correctly cleared several file-level matches as line-disjoint and correctly flagged
  four genuine ones, which is the signal-to-noise todo 368 was aiming for.

### RESOLVED 2026-08-26. The section below records how, including a blocker that cleared mid-run.

**Done and committed:** `skills/commit/overlap-check.sh` exists and is verified. Contract is
`overlap-check.sh [-C|--repo <repo>] <file>...`, exit 0 clean, 1 real hunk-level hit
(`<file>:<range> <sha> <subject>`), 2 could-not-run, matching `prefilter-gate.sh`'s three-outcome
shape. It sidesteps the sha-width trap entirely rather than papering over it: `git log --format=%H`
and `git blame --porcelain` both yield 40-char hashes, so there is no 7-versus-8 comparison and no
`^` boundary marker to strip. Cross-validated against a hand-computed result from the same session:
both independently found `0292e46` as a real hit on `skills/commit/SKILL.md` while correctly
clearing `e61d305` on the same file as line-disjoint. Exit 2 confirmed for no-args and bad-repo; an
untracked path and a deleted path in one call do not crash it.

**Still to do, one edit:** `skills/commit/SKILL.md` step 8's unpushed-overlap bullet must be
replaced by a call to the script, keeping ONLY the decision policy (interactive asks, unattended
proceeds and records) and dropping the `@@` parsing and `git blame -L` instructions. The replacement
text was written and is correct, but could not be committed.

**Why it was blocked, which matters for whoever retries:** `skills/commit/SKILL.md` simultaneously
carried a second, unrelated uncommitted hunk from a concurrent session (a `/commit fold` pushed-check
rewrite around `:135-147`). A pathspec commit takes the whole working-tree file, so committing would
have swept in that peer's in-progress work, and it contains an em dash that `em-dash.sh` correctly
flags, so the gate blocked it too. The documented escape hatch, partial staging via
`git apply --cached` per `skills/commit/edge-cases.md`, was ALSO unavailable: its own precondition is
that the index holds only your hunks, and the index held todos `491` and `506` staged by another
session (see `778`). Both routes closed at once, so this was parked rather than forced.

**How it cleared, same session:** rather than wait, the run fixed the SECOND blocker at its root.
Todo `778`'s script half taught `em-dash.sh` the exempt marker, which made `491` and `506`
committable after three sessions of being stuck, which emptied the index, which reopened the
partial-staging route. The wiring then landed via `git apply --cached --recount` on a
single-hunk extract (`git diff | awk '/^@@/ { n++; if (n==2) exit } { print }'`), verified to
contain none of the peer's text, with the peer's hunk left unstaged and untouched in the working
tree. Worth remembering as a pattern: a blocker made of two independent halves can sometimes be
dissolved by fixing the cheaper half rather than by waiting for either.

**Gate caveat on that commit, stated rather than glossed:** `prefilter-gate.sh` reads the WORKING
TREE, so it flags the peer's em dash at `SKILL.md:138` and cannot return 0 here no matter how clean
the staged hunk is. The staged content was checked directly instead: `comment-noise.sh` skips `.md`
entirely by its own carve-out, the extracted hunk greps clean for U+2014, and it adds no credential
shaped text. If a future change makes the prefilters able to read `--cached`, this case is why.

**Explicitly NOT done, and not silently invented:** none of `498` (it needs a frequency measurement
first, by its own text), and neither of this todo's folded-in questions - what marks a session
"unattended" outside a runner skill, and the third silent-failure path - both of which its own text
says need the dev's call.
- Done 2026-08-26: skills/commit/overlap-check.sh owns the algorithm and step 8's bullet now calls it, keeping only the decision policy. The sha-width trap is designed out rather than patched: git log --format=%H and git blame --porcelain both yield 40-char hashes, so there is no 7-versus-8 comparison and no caret to strip. Cross-validated against a hand-computed result from the same session, both independently flagging 0292e46 and clearing e61d305 as line-disjoint, and it caught real overlaps in four subsequent commits this run. Not taken, deliberately and not silently: any of 498 (needs its own frequency measurement first) and this todo's two folded-in questions about what marks a session unattended, both of which need the dev's call.
