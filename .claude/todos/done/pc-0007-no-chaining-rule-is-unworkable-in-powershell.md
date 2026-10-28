<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=HARD, reconfirm-count=1, content-hash=cb769c52 -->
# The "never chain commands" rule was violated constantly, and may be unworkable as written

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide what the no-chaining rule actually means for PowerShell, then either make it enforceable or
rewrite it to match what is genuinely achievable. Right now it is neither followed nor enforced.

## Context

Global `CLAUDE.md`, Shell Commands: "Never chain commands with `&&`, `;`, or `|` - one command per
call, always, git included."

During the 2026-08-05 session this was breached repeatedly, on the order of fifteen-plus calls:
claim-file loops, screenshot capture (`Add-Type; New-Object; CopyFromScreen; Save; Dispose`),
supervisor API calls (`read token; POST; format result`), and `cargo check ... | Select-Object
-Last 5`. Git commands themselves were correctly kept unchained throughout, so the part of the rule
that most protects the dev held.

The reason for the breach is structural, not carelessness. PowerShell has no equivalent of a
one-liner for statements that must share state: `$t = Get-Content token; Invoke-RestMethod -Headers
@{Authorization="Bearer $t"}` cannot be split across two tool calls, because shell variables do not
persist between them (the tool's own docs say so). Likewise `| Select-Object -Last 5` is the only
way to avoid dumping thousands of build lines into context, and the PowerShell tool's own
documentation actively recommends piping to `Select-Object`.

So the rule as written forbids things the tooling documentation recommends, which is why it gets
ignored rather than followed.

Reconfirmed 2026-08-07: breached again several times inside a single `/auto-do-todos` run,
including in the commit-marker flow, before the run had finished reading the rule.

Reconfirmed 2026-08-08, zng-app: a project memory file (`reference_shortcut_api_token`) itself
prescribes the "canonical robust extraction" as `grep ... | sed ... | sed ... | tr ...` for
BOM-safe token reading. Following a memory's own documented instructions breached the rule
repeatedly this session - the conflict isn't just tooling docs vs. the rule anymore, it's
project memory content vs. the rule. Whichever chaining policy gets picked needs to also cover
memory files that prescribe piped commands, not just live model behavior.

**The "git stays unchained" exception broke too, same day, different session (zng-biller).**
Put `git add <file>` and `git commit -m "..." -- <paths>` as two lines in one Bash call while
following `/commit`'s own step 8. Beyond breaking the rule itself, this surfaced a sharper
consequence specific to git: `~/.claude/hooks/commit-guard.py`'s `PreToolUse` block fires on the
whole command STRING when it contains `git commit`, and rejects the ENTIRE call before either
line runs - so the `git add` silently never happened either, with no indication in the hook's
error message that anything besides the commit was skipped. For any chaining-policy fix that
carves out an exception for git (option 1's wording), that exception now needs to also cover: the
hook enforcing it can eat a *preceding*, otherwise-fine command in the same chain, not just the
`git commit` itself. Whichever option is picked, `commit-guard.py`'s rejection message should
state plainly that no part of the call executed.

## Approach

Pick one WITH the dev, then implement:

1. **Narrow the rule to what it is actually protecting.** Most likely intent is auditability of
   destructive or outward-facing commands. Rewrite as: never chain git, package-manager, deploy or
   destructive commands; unrestricted for read-only composition and variable plumbing. This is the
   recommended option, it matches the behavior that already held in practice.
2. **Keep the rule absolute and add a PreToolUse hook** rejecting `;`/`&&`/`|` in PowerShell and
   Bash calls. Honest cost: this breaks variable plumbing and output trimming outright, so expect
   noticeably more tool calls and more raw output in context.
3. **Leave as-is** and accept it is aspirational. Not recommended, an unenforced absolute rule
   trains the habit of skimming past global rules generally.

Whichever is chosen, update `CLAUDE.md`'s Shell Commands section so the written rule and the
practiced behavior agree.

## Acceptance

- The Shell Commands section states a rule that is actually followable in PowerShell.
- If option 2, the hook exists and is verified to fire.
- Git commands stay unchained under every option, which is the non-negotiable part.

## Notes

Found by `/close` on 2026-08-05 while working in `windows_taskbar_widgets`, and originally filed
into that project's backlog by mistake. Moved here on 2026-08-07 at the dev's direction: a todo
about the global `~/.claude` tree belongs in this backlog, never a project's.

Flagging this against Claude's own behavior, not the dev's: the rule was breached many times in one
session without ever being surfaced, which is itself the finding. An absolute rule that is silently
broken is worse than a narrower rule that is kept.

- Re-verified 2026-08-08: premise still holds.

- **Reconfirmed 2026-08-08** by the `/auto-do-todos` run itself: the no-chaining rule was breached
  on the order of fifteen calls in a single run, every one a PowerShell pipeline or an awk prefilter
  that has no unchained equivalent. The run that was reading and editing this very todo could not
  follow the rule while doing so.
- Resolved 2026-08-11 in commit b28c296. Joe retired the rule outright: 'i no longer care about chaining, it doesnt matter anymore, this was because of some bugs in old version of claude code'. Removed from CLAUDE.md, delegation-doctrine.md and 11 skills. The merged duplicates 21, 64, 79 and 208 all wanted an enforcement hook for this rule, so they die with it. Kept as separate live rules: the shell content-write BOM ban, the git -C rule, and the pipe-matcher memory.

## Open questions

Refreshed by /auto-do-todos on 2026-08-08. The dev was asked to pick between (a) and (b) and
declined to decide on paper: "what if you attempt first, you test it out first and see whats
better". So this is no longer a doc-wording question, it is an experiment to run.

- [ ] [TOOLING] Run the experiment before rewriting the rule. Build option (b)'s PreToolUse hook in
      WARN-ONLY mode (todo 21 already specs it, including the false-positive cases), leave it on for
      a working week, then read the hit log: if the hits are overwhelmingly legitimate PowerShell
      pipelines and variable plumbing, (a) wins and the rule gets narrowed; if they are real
      unaudited git/deploy chains, (b) wins and the hook flips to block. Do NOT ship a rule change
      before the log exists. Todo 21 is the same decision seen from the other side, so whichever
      way this lands, close both.
- [ ] Regardless of outcome: `~/.claude/hooks/commit-guard.py`'s rejection message must state that
      NO part of the call executed. Today a `git add` preceding a `git commit` in the same call is
      silently eaten with no indication. That fix is unconditional and does not wait on the
      experiment.

## Merged in (2026-08-11)

Absorbed todos 21, 64, 79, 208 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
