<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# A push outside `/commit push` never triggers build-watch, so the watcher gets hand-rolled

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/build-watch.md`'s watcher reachable from any push, not only from the
`/commit push` / `pushbump` / `pushnbump` entry points, so a session that pushes directly stops
hand-rolling a blocking poll loop.

## Context

Filed 2026-08-20 from the `/close` retrospective of the session that shipped todo 423 (CI for this
repo).

`build-watch.md:6` scopes itself to "after a successful `git push` in `push`, `pushbump`, or
`pushnbump`". That is the only thing that names it. A session that runs `git push` on its own, which
is normal when the push is not part of a `/commit` invocation, gets no signal that the watcher
exists.

**What that cost, concretely, in the 423 session:** the todo's acceptance criterion required a real
CI run conclusion, so the run had to be observed. With no pointer to `watch-build.ps1`, the session
hand-rolled a bounded `gh api` polling loop with `Start-Sleep` three separate times, each blocking
the turn for the length of the CI run. `build-watch.md:3-6` already ships exactly this as a
non-blocking background watcher (`skills/commit/watch-build.ps1`, `-Branch`/`-RepoPath`, resolves
HEAD itself, reports a `BUILD_RESULT` marker) and CLAUDE.md's own "scan the codebase first, reuse
what already exists" rule should have caught it.

**A second, sharper miss in the same session.** `build-watch.md:42-44` states its inspection rules
"appl[y] whenever you inspect runs yourself (e.g. `gh run list`), not just when parsing the watcher's
marker", including "never `--limit 1`" and "enumerate and report every triggered run's conclusion".
The session polled with `?per_page=1`. No wrong verdict resulted, because this repo has exactly one
workflow and both of its jobs were enumerated separately, but the rule was broken and a second
workflow would have been invisible.

**Why this is not a duplicate of `done/69-build-watch-reference-gets-skipped-under-momentum.md`.**
That todo was about forgetting to read a reference that the flow already pointed at. This one is
structural: on a bare `git push` there is no pointer to forget. Prior build-watch todos 66, 69, 75,
252 and 371 all sit inside the `/commit push` path and none of them widen the trigger.

## Approach

1. Decide where the pointer belongs. Two candidates, and the answer is probably both:
   - `skills/commit/build-watch.md:6` - widen the stated trigger from the three `/commit` push
     subcommands to "any push to a repo with `.github/workflows/`", keeping the existing detect step
     (`build-watch.md:15`) as the actual gate since it already checks `gh`, the remote, and the
     workflows dir.
   - `CLAUDE.md` or a snippet - one line making the watcher the default way to observe CI, so a
     session that pushes directly reaches for it instead of a poll loop. Weigh this against the token
     ceiling: `ci/check_instruction_budget.py` gates `CLAUDE.md` at 6732 tokens with **zero
     headroom**, so anything added there must be paid for by a cut. That constraint alone may settle
     it in favour of the skill file only.
2. Consider whether a hook is warranted, then probably reject it. A `PostToolUse` hook on a `git
   push` command could inject the reminder mechanically. But this repo has killed three guess-based
   hooks in one day (see `PLAN.md`, "Hook doctrine"), and "was this push already watched" is state a
   string match cannot see. Prefer the documentation fix; if a hook is attempted, measure it against
   a real corpus of push commands first, per the same doctrine.
3. Leave the `per_page=1` rule alone. It is already written down at `build-watch.md:42-44` and was
   simply not followed; restating it louder is the failure mode todo 290 documented.

## Acceptance

- `build-watch.md`'s trigger sentence no longer implies the watcher is reachable only from
  `/commit push`, and names the bare-`git push` case explicitly.
- A real end-to-end check: push something to a repo with a workflow WITHOUT going through
  `/commit push`, and show the watcher launching from the widened path, with its real
  `BUILD_RESULT` marker output pasted. A documentation-only change with no run behind it does not
  close this.
- `python ci/run_all.py` still exits 0, and if `CLAUDE.md` was touched, the budget check's real
  output is pasted showing the file is still at or under 6732 tokens.

## Notes

Do not fix this by deleting the poll-loop habit from prose. The reason it happened is that the
reusable mechanism was not discoverable from where the session actually was, which is a wiring
problem, not a discipline problem.
