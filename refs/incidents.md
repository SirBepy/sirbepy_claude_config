# Why these rules exist - the incident record

Every rule in the global `CLAUDE.md` has something behind it. This file holds the stories, dates
and quotes; `CLAUDE.md` holds the rules themselves.

**Read this when a rule looks arbitrary, or when you are about to argue with one.** Not routinely.
The rule is always complete without the story, which is exactly why the stories live here: they
explain, they never instruct. If something in this file reads like an instruction, it is in the
wrong file.

Split out of `CLAUDE.md` on 2026-08-22 by todo 424, which cut 412 tokens of narrative off the
always-loaded budget without moving a single rule.

---

## Shell Commands - never write file CONTENT through the shell

Two incidents, both the UTF-8 BOM that Windows PowerShell 5.1 prepends even with `-Encoding utf8`:

- `gh secret set` (2026-07) rejected the value outright.
- `%APPDATA%\com.sirbepy.taskbar-widgets\settings.json` (2026-08-05): the BOM made the app fall
  back to `Settings::default()` and **silently rewrite Joe's strip**.

The second one is why the rule is a hard ban on the mechanism rather than a "be careful with
encoding" nudge. The shell path is what makes the bug reachable.

## Packages - resolve the tree before checking advisories

`tauri-plugin-clipboard-api` passed a by-name check clean. Post-install, `npm audit` immediately
flagged its transitive `valibot@0.40.0` for a known high-severity ReDoS. A pre-install, name-keyed
lookup could never have surfaced it, because the CVE is filed against the sub-dependency's own name.

## Process Hygiene - never leave orphan child processes

90+ orphan vitest processes pegged the CPU at 100% and 90 degrees C.

## Code Style - the comment cap

2026-07-29: a sidebar PR shipped six- to nine-line block comments on nearly every hunk, while the
same files on `develop` carried two-liners. The reaction:

> STOP WRITING THESE BIGGASS UNNECESSARY ASS COMMENTS

## Execution Discipline - the unverified-claim rule

Recurred **5 times in one project** despite being memory-documented after each one. A wording-only
fix had already failed once for this exact class of rule, which is the em-dash enforcement history
in miniature: the fix that worked there was a hook (`hooks/em-dash-guard.py`), not louder prose.

## Execution Discipline - the outbound receipts rule

2026-08-14: a ticket was filed for work already done, and Joe looked stupid in front of his team.

Ticket creation is now enforced at the tool layer (`/ticket`'s ground check, plus
`hooks/shortcut-create-guard.py` and `hooks/linear-create-guard.py`). The chat half has no tool
call to hook, which is why it stays a prose rule.

## Testing floor - why e2e is never run unprompted

Decided 2026-08-18. Joe wanted fewer automatic tests, but e2e was never in the fast floor to begin
with, and a per-task "want a test?" card would violate the front-load rule. So the rule landed as
"say it in one line and stop", which is neither running it nor asking about it.

## AI todos - no global work from a project session

2026-08-07: an `/auto-do-todos` run inside `windows_taskbar_widgets` executed three global-tooling
todos and committed into `~/.claude`. Joe:

> you shouldnt be doing global stuff from a repo unless i explicitly tell you

## Global Knowledge Vault - the obsidian-git fallback

The plugin silently died 2026-06-11. Seven weeks of daily notes sat unbacked-up until 2026-08-01.
That is the whole reason a manual backup commit is permitted at all, and why the permission is
gated on evidence the plugin is actually dead rather than on convenience.

## Memory Discipline - index/file desync

2026-08-13: three entries were dropped by deleting an index line while the memory file stayed on
disk, so the memory silently stopped loading. Restored by hand. Reproduced, not hypothetical.

## Subagent model - why every dispatch names sonnet explicitly

2026-07-08: an 8-way code-review fan-out plus its verifiers all default-inherited Fable 5 and
burned a painful chunk of Joe's tokens. Inheriting the session model multiplies cost by N on a
fan-out for no gain.

## AI todos - the harness auto-mode classifier false-positives on archival notes

2026-09-04, mid `/mega-todos` wave-1 barrier: `skills/mega-todos/archive-batch.ps1 -Items
"999999|filed by /mega-todos on 2026-09-04..."` was denied with "Reason: Blocked by classifier" (the
first sighting, during the actual run, read "Remove-Item on system path '/mega-todos' is blocked.
This path is protected from removal."). No `Remove-Item` verb, and no `/mega-todos` path, appeared
anywhere in the command; the word was prose inside the `-Items` note. `grep -rn "protected from
removal" hooks/ ci/` returns nothing - this is not a hook in this repo, it is the Claude Code
harness's own auto-mode command classifier.

Probed by varying one thing at a time against real scripts, id `999999` (never resolves, so nothing
is ever actually deleted): a bare `/mega-todos` string, a real `Remove-Item` next to one, and a
throwaway script with a disguised internal `Remove-Item` all passed clean. Only the real
`archive-batch.ps1` - whose own docstring reads "no delete to stage" and which really does delete a
claim file via `complete-todo.ps1` - was denied, and only when its note carried the leading slash;
the identical call with `mega-todos` (no slash) in the note passed clean. Calling `complete-todo.ps1`
directly with the same slash-worded note also passed clean, so the trigger is not the slash alone -
it needs a script whose own visible deletion behavior the classifier can read, plus a slash-prefixed
word elsewhere in that same call.

Workaround: drop the leading slash from any `/slash-command` name written into a `-Note` or `-Items`
archival string (`mega-todos` instead of `/mega-todos`). Verified reproducible one way (blocked with
the slash, clean without it, same script, same nonexistent id) but not proven deterministic across
scripts - it is read as a semantic classifier, not a fixed regex, so a future session hitting a
variant shape should re-probe rather than assume this list of triggers is exhaustive.
