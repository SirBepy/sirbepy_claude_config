# /close Phase 2: choosing the scope arg for /code-check

Read on demand from `skills/close/SKILL.md` Phase 2.

Determine scope arg - identify THIS session's own commits, never everything unpushed (a shared
branch with concurrent sessions makes `unpushed` review other sessions' work; an in-session push
makes it resolve empty - two symptoms of one root cause):

- Recall every sha THIS session's own `/commit`/`git commit` calls produced earlier in this
  conversation (each reports its sha on success) - never re-derive from `git log` timestamps or
  `@{u}..HEAD`, both of which conflate concurrent sessions or go empty post-push.
- Zero recalled: call `list_peers`. No other active session on this worktree: pass `uncommitted`
  (unchanged - covers working-tree-only changes). One or more active: `uncommitted` has no sha to
  filter by, so a peer's dirty files enter scope unattributed (2026-08-31,
  claude_usage_in_taskbar - 5 own files plus 5 peer files, zero commits made). Pass the file list
  THIS session itself edited or wrote this turn (already known from its own Edit/Write calls in
  context, deduped) with a `files:` prefix instead, e.g. `files:a.ts b.ts` - same attribution
  problem `shas:` already solves for the commit branch, applied where there's no sha to filter by.
  If this session made zero edits at all, skip Phase 2 and print why rather than passing an empty
  scope.
- One or more recalled: pass the list as the scope arg with a `shas:` prefix, e.g.
  `shas:abc1234 def5678`. The prefix is required even for a single sha: a bare lone sha is read
  as a range and diffs sha-to-working-tree, which is empty right after a commit. `/code-check`
  resolves it to the union of files each commit touched, reviewing exactly this session's commits
  regardless of push state or how many other sessions share the branch.
- Can't determine this session's own commits at all (e.g. resumed/forked, no commit history
  visible in context): SKIP Phase 2 and print why, rather than falling back to
  `unpushed`/`uncommitted` and silently reviewing the wrong scope.

Invoke `/code-check` with that scope arg via the Skill tool. It handles the analysis and writes the todos directly. Read its summary line (`code-check: N findings ...`) to extract the finding count for the Phase 4 counter.

`/code-check` dispatches the analysis itself, into a subagent that did not write this session's code - see its "The analysis runs in a fresh subagent, always" section. Do not pass it what this session was trying to achieve, and do not summarise the work for it. Scope is the only input it gets from here; the reasoning behind the code is exactly what must not travel.
