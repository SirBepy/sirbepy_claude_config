<!-- duplicate-checked: 806 (done/) shipped foreign-hunk-check.sh itself, the COMPARISON half. This is the residual gap in what it shipped - the script takes `--own` line ranges as an argument, so the caller still hand-derives them, which is the "stop being a per-file manual read" half of 806's own Goal that did not land. 474 (done/) is the sibling overlap-check script and takes shas, which are recallable; only the line-range variant has this problem. 290 is the em-dash prefilter, different script. -->
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# foreign-hunk-check still makes the caller hand-derive its --own line ranges

**Type:** skill-improvement
**Origin:** ai

## Goal

Finish what todo 806 started: running `/commit` step 8's working-tree diff
check should not require anyone to read a `@@` header.

## Context

806 shipped `skills/commit/foreign-hunk-check.sh` (commit `49fd7a2`) and closed.
It delivered the comparison, but its interface takes the caller's own line
ranges as an argument:

```
foreign-hunk-check.sh -C <repo> --own <file>:<a>-<b>[,<a>-<b>...] <files>
```

806's Goal was for this to "stop being a per-file manual read", and its Approach
assumed "the harness knows which files/edits this session made". The shipped
script does not derive that, so `/commit` step 8 says the ranges are "recalled
the same way step 1a's own-commit list already is" - and a model cannot recall
exact line numbers after a session of edits.

What actually happens, done twice on 2026-09-04 in claude_usage_in_taskbar
across two `/commit` invocations in one session:

1. `git diff -U0 -- <files> | grep -E '^\+\+\+|^@@'`
2. read each `@@ -old +new,count @@` header
3. hand-convert `+N,M` to `N-(N+M-1)`, and a bare `+N` to `N-N`
4. paste the result back as `--own`

Steps 2 and 3 are transcription with a silent failure mode: a wrong range makes
the check report `clean` while genuinely foreign hunks ride along, which is the
exact outcome the gate exists to prevent. Nothing verifies the transcription.

Not the same problem as `overlap-check.sh` (todo 474, also done): that one takes
shas, which the model genuinely does hold in context. Only the line-range
variant is unrecallable.

## Approach

1. Teach `foreign-hunk-check.sh` to derive the current working-tree hunk ranges
   itself from `git diff -U0`, which is the same parse it already performs one
   step later. The caller then declares only what it did NOT write, or nothing
   at all in the common single-session case.
2. If `--own` must stay the interface for compatibility, ship a sibling that
   prints a ready-to-paste `--own` argument for a pathspec, and have step 8 call
   that rather than describing the manual recipe in prose.
3. Update `skills/commit/SKILL.md` step 8 to call whichever lands, and drop the
   "recalled the same way" wording, which asks for something unreliable.

Rejected: "be more careful when reading the diff". The gate exists precisely
because eyeballing a shared checkout is unreliable, so a manual transcription
step inside it is self-defeating.

## Acceptance

- `/commit` step 8 runs without the caller reading a single `@@` header.
- A missing range no longer silently passes: dirty a file with two separate
  hunks, declare only one, and confirm the other is still reported.
- The existing exit-code contract (0 clean, 1 foreign hunks, 2 could not run)
  is unchanged, and 806's sub-hunk case
  (`foreign-hunks-inside-your-hunk`) still fires.

## Notes

- Surfaced 2026-09-04 during `/close` in claude_usage_in_taskbar, a repo that
  routinely runs several Conductor sessions against one checkout, which is the
  same setting that produced 806.
- Related: [[806-shared-worktree-foreign-hunk-check-helper]] (done, shipped the
  script), [[474-commit-step-8s-overlap-check-should-be-a-script]] (done, the
  sha-based sibling).
- 2026-09-06, video_editor (Cueline) `/autopilot` run: the gate was skipped
  outright, not transcribed, on three commits of 60+ brand-new files (scaffold,
  MCP crate, timeline). Every file was untracked, so `--own` would have been
  "the whole file" for each of 60 paths, and no peer session existed
  (`list_peers` empty each time). Skipped with a stated reason in the run
  summary. Second data point for the same gap: for an all-new-files pathspec
  the script should accept "untracked = wholly mine" without ranges, or the
  auto-derive in step 1 should treat an added file as one own hunk.

### REOPENED 2026-09-11 (/loop-todos): the arithmetic went away, the safety property went with it

An audit pass reported this todo satisfied by `skills/commit/commit-pathspec.sh`. It is not, and the
way it is not is worse than the original gap.

`commit-pathspec.sh:211-236` derives own-ranges by passing EVERY hunk of `git diff HEAD` to
`foreign-hunk-check.sh` as `--own`. The check therefore reads back the exact set it was handed and
cannot report a foreign hunk under any input. It then prints `clean` and the commit proceeds.

Reproduced on a scratch repo, one working tree, two hunks (`1-4` written by "me", `7-10` standing in
for a peer):

- `foreign-hunk-check.sh -C <repo> --own f.txt:1-4 f.txt`
  -> `f.txt: foreign-hunks-present 7-10`, exit 1. Correct.
- `commit-pathspec.sh -C <repo> ... -- f.txt` (no `--own-range` declared)
  -> `auto-derived own-range 1-4,7-10 (every current hunk assumed own, todo 924/933)`
  -> `[foreign-hunk-check] clean` -> `[commit] committed`.

Todo 933's Notes already recorded this exact shape happening in the wild on 2026-09-05, before the
script shipped: a caller-side loop passed every hunk as `--own` and the check printed `clean` on a
file holding a peer session's six uncommitted lines. That note names the rule the script then broke:
own-unless-told-otherwise is wrong.

Acceptance item 2 of this todo, and item 2 of 933, both fail on the auto-derived path.

**933 is folded into this todo** (archived 2026-09-11): same ask, same file, same fix. Its own data
point is quoted above.

**Proposed fix, no dev decision required.** Keep auto-derivation, since removing the hand arithmetic
is the point of both todos, but stop laundering it into a `clean` verdict. `hooks/.session-markers/`
already holds one live marker per active session in this checkout, which is exactly the concurrency
signal that decides whether an auto-derived range is trustworthy:

- one live marker: this session is alone in the tree, every hunk really is its own, `clean` is true.
- two or more: a peer shares the tree, so an auto-derived range proves nothing. Print an explicit
  unverified verdict and require either a declared `--own-range` or an explicit waiver flag.

A check that cannot fail must never report success.
- Fixed 2026-09-11 by a loop-todos run, with 933 folded in. Auto-derivation stays, so neither todo's hand-arithmetic goal is undone; what changed is that the verdict can no longer claim more than it proved. commit-pathspec.sh now counts live files in hooks/.session-markers/ (the same directory write-session-marker.ps1 owns, prune-on-write, so a lingering marker can only inflate the count toward a safe refusal and can never make a shared tree look solo). One or zero markers means this session is alone and the auto-derived range really is its own, so clean is true. Two or more means a peer shares the tree, so the run prints UNVERIFIED and refuses, offering a declared --own-range or an explicit --force foreign-hunk. A caller-declared range and an untracked file are both always trusted; the untracked exemption is deliberate, since a new file has no HEAD baseline for a peer's lines to hide inside, and gating it would reproduce the 60-new-file annoyance this todo's own Notes recorded. Verified independently by the orchestrator on two scratch repos with an identical two-hunk file: one marker gave auto-derived clean and a commit, two markers gave UNVERIFIED, a refusal, and HEAD unmoved. Suite is 22/22 with the marker directory injected so it never reads the real one.

