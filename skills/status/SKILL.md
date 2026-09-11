---
name: status
description: Triggers on /status, or asking how far along in-flight work is. Read-only per-item liveness vs tree progress.
argument-hint: "[--deep]"
allowed-tools: Bash, PowerShell, Grep, Glob, Read, TaskStop
---

# /status

> Where is this session actually at, right now, from live evidence, not from memory.

Read-only, on demand. Never edits, commits, or starts anything, and never runs itself
unprompted.

## When this applies

Only useful once the CURRENT session has dispatched background work (subagents via the `Agent`
tool, or under `/delegate` / `/autopilot` / `/batch-todos`) that may still be in flight. If nothing
has been dispatched this session, say that plainly and stop, there is nothing to probe.

## Step 1 - List the work items from this session's own context

Recall each item this session dispatched: its agent id, a short label (todo id or task name), the
paths it was scoped to, and whether a completion report has already been received for it. This
comes from the conversation itself, not a file, no dispatch manifest exists on disk.

## Step 2 - Liveness probe (one throwaway call covers every item)

Call `TaskStop` with a made-up task id. It fails, and the failure message lists every currently
running background agent by id, that list is authoritative. See `refs/delegation-doctrine.md`'s
"Liveness and session budget" section for why this replaces any output-file mtime/size check
(proven wrong in both directions, todo 384). Never substitute an output file's timestamp or size
for this probe.

Cross-reference each item's agent id against that list: present = RUNNING, absent = EXITED (the
run is over, cleanly or silently, the list does not say which).

## Step 3 - Tree evidence, scoped per item

For each item, run `git status --short` and `git diff --stat` scoped ONLY to the paths that item
owns (pathspec arguments, never repo-wide, a repo-wide diff mixes in every other lane's concurrent
edits). Nonzero output is real progress. Zero output means no visible tree progress yet, regardless
of whether the agent is running or exited.

## Step 4 - Health, best-effort, skip if slow

Detect the stack from repo markers (`ci/run_all.py`, `pubspec.yaml` -> `flutter analyze`,
`package.json` -> its lint or typecheck script) and run only the FAST check, never a full test
suite, unless invoked as `/status --deep`. Skip and say so if no fast check exists or it would take
more than a few seconds. This step only corroborates an item already flagged done, it is not a
liveness signal by itself.

## Step 4a - Evidence level, reported instead of a verdict

The single most misleading thing this skill can do is collapse four different states into the word
"done". Written to disk, compiles, tests pass, and reviewed by something other than whoever wrote it
are four separate claims, and only the last one is what the dev usually means. So every item carries
its evidence LEVEL alongside its state, and the level is derived from what was actually observed
this run, never from a subagent's own summary of itself.

| Level | Name | What has to have been seen |
|---|---|---|
| 1 | on disk | tree change under the item's owned paths, nothing more |
| 2 | compiles | the stack's fast check ran green over those paths this run (Step 4) |
| 3 | tests pass | the project's own suite ran green this run, not merely "the agent said so" |
| 4 | reviewed | something other than the agent that wrote the code checked it: a second agent, a real reproduction, or the dev |

Report the level reached, and say so when the next one was not attempted. A level is never inferred
from a builder's report claiming it - a report is a claim about evidence, not the evidence. If the
only source for level 3 is a subagent saying its tests passed, the item is at level 1 or 2 with a
note that a passing run was CLAIMED but not observed here.

Level 4 is rare on purpose. Most finished work sits at 2 or 3, and saying that plainly is the point.

## Step 5 - Classify each item

| Tree change | Agent state | Report received | Verdict |
|---|---|---|---|
| any | any | yes, and health check corroborates | done, reported at its evidence level from Step 4a |
| nonzero | running | no | working |
| zero | running | no | unknown, could be reading or planning, not evidence of a stall by itself |
| nonzero | exited | no | stalled, produced output then stopped, unconfirmed if finished or died |
| zero | exited | no | stalled, no artifacts, likely died before or during start |

Never upgrade "unknown" to "working" or "done" without the matching evidence row. Never report a
subagent's result that was not actually seen, no fabricated or predicted content.

## Output format

Lead with ONE overall verdict line (worst state present wins: blocked, then stalled, then working,
then done, then unknown), then one bullet per item. Bullets, not prose.

```
🔃 working - 2 of 3 items progressing, 1 exited with no tree change

- 🔃 todo 924 (agent a3f1) - skills/close/: 2 files, +48/-3. Running and producing. Evidence level 1 (on disk).
- ❓ todo 933 (agent b7e2) - absent from TaskStop's running list, skills/commit/: 0 files
  changed. No artifacts, unconfirmed whether it died immediately or never started.
- ✅ todo 978 (agent c9d0) - .claude/todos/: 1 file, +12/-0. Evidence level 3 (tests pass): ci/run_all.py 6/6 observed here. Not reviewed by anything but its author.

Unknown: why b7e2 exited with zero output, no report was received either way.
```

**Every state is an emoji marker, never the bare word** - the dev asked for this explicitly, because
he skims the bubble rather than reading it. The five markers, and nothing else:

| Marker | State | Means |
|---|---|---|
| ✅ | done | finished, and its verify floor passed |
| 🔃 | working | running AND the tree is growing under its owned paths |
| ⚠️ | stalled | exited without a report, per Step 5, whether or not it left tree changes |
| ⛔ | blocked | needs the dev's input, for example a pending question card |
| ❓ | unknown | genuinely indeterminate, never softened into one of the other four |

The overall verdict line takes the worst state present, with the same marker. A word may follow the
marker for clarity, but the marker is never dropped.

## Notes

- Reports on THIS session's own dispatches only, not other Conductor peers, `list_peers` is a
  separate, unrelated probe.
- If an item was never dispatched with a scoped path list, say the scope itself is unknown rather
  than guessing a pathspec.
- Complements `/context-left` (session's own token budget) and `refs/delegation-doctrine.md` (the
  full liveness doctrine this skill applies). Neither duplicates the other.
