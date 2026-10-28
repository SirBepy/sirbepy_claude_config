<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=9, reconfirm-count=1, content-hash=ba311831 -->
<!-- duplicate-checked: grepped todos/ and done/ for "pathspec", "ceremony", "commit-pathspec", "overlap-check" - 933 is about --own range computation only; 474/860 built overlap-check itself; nothing scripts the whole per-commit sequence. -->
# Script the per-commit pathspec ceremony so an orchestrator stops hand-composing it

**Type:** skill-improvement
**Origin:** ai

## Goal

One script that runs `/commit` step 8's fixed sequence for a given repo, pathspec and message, so a
multi-commit run composes it once instead of fourteen times.

## Context

`skills/commit/SKILL.md` step 8 is a fixed chain per commit: prefilter gate, branch guard against
the recorded EXPECTED branch, HEAD guard against the recorded EXPECTED sha, `overlap-check.sh --own
<run's shas>`, `foreign-hunk-check.sh --own <file>:<ranges>`, `git diff --cached --name-status`
coverage check, then `git commit -m ... -- <files>` and `git rev-parse HEAD` as its own call.

The hubbub autopilot run of 2026-09-05 made 14 commits across 5 repos and typed that chain by hand
every time as a long Bash one-liner (`test "$(git rev-parse --abbrev-ref HEAD)" = develop && test
"$(git rev-parse HEAD)" = <sha> && bash prefilter-gate.sh ... && git commit -q -m ... -- ... && git
rev-parse HEAD`), with the overlap and foreign checks in a separate call before it. It worked, but:
one of the fourteen dropped the coverage check, several ran the `--own` range for the foreign check
as `1-9999` for every file (which is only honest when the session authored every hunk, true here but
an unstated assumption), and the whole thing is exactly the "repeated manual step" `/close` Phase 1
exists to catch. `hooks/commit-guard` already re-runs the prefilter at commit time, so the gate half
is protected; the guards and the two overlap scripts are not.

## Approach

`skills/commit/commit-pathspec.sh -C <repo> --expect-branch <b> --expect-sha <sha> --own <shas>
--own-range <file>:<a>-<b>... -m "<message>" -- <files>`: runs the chain above in order, prints
each check's one-line verdict, refuses on any non-zero, commits by pathspec, prints the new full sha
on its own last line. `--own-range` optional; when omitted the script derives the session's ranges
from `git diff HEAD -- <file>` hunks and states that it did (that is the current implicit `1-9999`
made explicit). Then `SKILL.md` step 8 names the script as the normal path and keeps the prose as
the definition of what it does. `/autopilot`'s "cadence" bullet points at it.

## Acceptance

- Step 8's five preconditions are each one printed line of the script's output.
- A commit attempted on a moved HEAD is refused with both shas printed.
- `/commit` SKILL.md and `/autopilot` SKILL.md reference the script.

## Notes

Filed 2026-09-05 from the hubbub autopilot `/close`. Related: 933 (`--own` range computation),
474 and 860 (overlap-check itself).

- 2026-09-06, head_soccer_v_fable_oneshot autopilot session 706da5d5 (folded in at its `/respawn`): the same chain was hand-typed 19 more times, one Bash call each (verify floor, then `--own` ranges derived as `1-$(wc -l)` per file, overlap-check, foreign-hunk-check, branch and HEAD guards, prefilter gate, pathspec commit). Two drifts the script would remove: `git rev-parse HEAD` was chained into the commit call instead of running as its own call, and the `--own` range was again whole-file (`1-N`), honest only because no peer session existed. Second run in two days with the identical shape; the helper is overdue.
- DONE 2026-09-10 via /loop-todos cycle 3. New skills/commit/commit-pathspec.sh scripts the whole step 8 chain in order: prefilter gate, branch guard, HEAD guard, unpushed-overlap check, working-tree foreign-hunk check, staged-pathspec coverage check, the commit, then rev-parse on its own last line. Two mechanisms carry the value. derive_own_ranges parses each file own git diff HEAD hunk headers into ranges and feeds foreign-hunk-check --own automatically, which is the by-eye arithmetic todos 924 and 933 exist to kill; --own-range still forwards verbatim for a genuinely mixed file. classify_path sorts each path into live, untracked, deleted-staged, deleted-unstaged or unknown, excluding an already-removed path from the two checks that cannot diff it while keeping it in the commit, and auto-adding untracked files. The design rule is that it ADVISES: every judgement branch refuses by default and needs an explicit --force naming the exact check, while the branch guard and the prefilter gate accept no override at all, matching the never-bypass wording in the prose. 18 assertions in skills/commit/test_commit_pathspec.sh, discovered by ci/run_all.py existing glob, covering a clean multi-hunk commit, a pathspec containing a removed path, a foreign hunk that must surface rather than be swallowed, the branch and HEAD guards, the coverage move shape, a secret-scan block, and untracked auto-add. Wiring finished by the orchestrator: skills/commit/SKILL.md step 8 and skills/autopilot/SKILL.md both point at the script, with the prose kept as the source of truth for what each check MEANS since the script mechanises the sequence, not the policy. On 924 and 933: their acceptance is satisfied as a byproduct EXCEPT one line, and the caveat is the honest part. The auto-derived path assumes every current hunk is own and prints that it did so, so it cannot flag a hunk it was never told to exclude; only the explicit --own-range path reports a foreign hunk. That is 964 own accepted design, the current implicit 1-9999 made explicit, and matches 933 own note that a caller-side script cannot be trusted to name foreign hunks it does not know about. Neither todo was archived here: both carry another session uncommitted edits and were left untouched.
