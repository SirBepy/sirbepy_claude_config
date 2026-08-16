# Builder Preamble

The literal paste source for `refs/delegation-doctrine.md`'s "Canonical builder preamble": copy
the block below into every builder dispatch prompt instead of retyping it from memory. See the
doctrine file for why (drift history, the `bdb0323` incident).

```
Windows. PowerShell for shell commands. Working directory: <WORKING_DIR>.

<STAGING_LINE>

Never run `git stash`, `git reset`, or `git checkout` on paths you don't own - other agents'
uncommitted work shares this tree. To compare against clean state, use `git show HEAD:<file>`.
Stage changed files by name, never `git add -A`.

Clean up only the exact files you created, by exact name, never by glob or wildcard: never touch
`hooks/.commit-marker-*` (the guard consumes those itself) or `hooks/.session-markers/` (a live
session's commit depends on it).

<GLOBAL_EDIT_BAN>

If this dispatch captures screenshots, save them under `.for_bepy/screenshots/<pid>-<start-ticks>/`,
the id the orchestrator resolved once via `rename-session.ps1 -GetId` (never a bare or hand-picked
subfolder name, and never one you derive yourself) - that's what leaves files `/close` can never
prove ownership of and therefore never clean up.

<OFF_LIMITS>

<ORPHAN_CHECK>

Your final message is your entire return value. ALL commands, including the verify floor
(build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background` is
FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn while
anything is still running is a failed dispatch. Any command that may exceed 120 seconds MUST pass
an explicit `timeout` (up to 600000ms): the tool's default is 120s and the harness auto-backgrounds
past it, so omitting `timeout` backgrounds your build whether you intended it or not. The only case
allowed to end a turn with something unfinished is a foregrounded command that outlives its own
600000ms cap: report the partial output plus the exact command still in flight, don't end a turn on
bare "still waiting" with nothing else.
```

## Placeholder table

| Placeholder | Substitute with | Delete entirely when |
| --- | --- | --- |
| `<WORKING_DIR>` | the dispatch's actual working directory | never - always filled |
| `<STAGING_LINE>` | `Stage your changes but do NOT commit. The main agent will run /commit after your report-back.` by default, or `Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.` for a repo sharing a git index with concurrent sessions (e.g. zng-app, zng-biller) | never - always filled |
| `<GLOBAL_EDIT_BAN>` | `Never edit files under \`~/.claude/\` (skills, hooks, settings, global CLAUDE.md) even if the task description points at one - that requires the dev's explicit say-so in the CURRENT session, which a subagent can't verify; if a task seems to require it, stop and report back instead.` | the session's own working directory IS `~/.claude` itself (dev opened the session there, so global work is the whole point and the ban would refuse the assigned task) |
| `<OFF_LIMITS>` | the per-dispatch OFF LIMITS file list | never - always filled |
| `<ORPHAN_CHECK>` | the mandatory final-step text from `refs/process-hygiene.md` (Layer 1) | the dispatch runs no Node commands |

## Read-only opt-out

A dispatch that is genuinely read-only (a scout, an Explore-style search) and captures no
screenshots can skip the screenshot-id requirement by adding the literal line `READ-ONLY DISPATCH`
anywhere in the prompt. This is an explicit marker the orchestrator sets, not something inferred
from the dispatch's content: `hooks/dispatch-preamble-guard.py` checks for that exact string, it
never guesses whether a dispatch is read-only. Never add the marker to a dispatch that does capture
screenshots.
