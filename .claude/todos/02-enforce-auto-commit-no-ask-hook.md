<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=2, content-hash=73c83fc0 -->
# Enforce "no asking before commit in full-auto repos" mechanically, not via memory recall

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop Claude from asking permission (via `AskUserQuestion`, a passive "let me know if you want /commit run" report line, or silently ending the turn with the change staged-but-uncommitted) before committing in any repo whose `CLAUDE.md` `@import`s `~/.claude/snippets/full-auto.md`, once the turn already satisfies `auto-commit.md`'s conditions. This has recurred SEVEN times, all in the same project (`claude_usage_in_taskbar`) so far - see `feedback_auto_commit_full_auto_projects.md` in that project's auto-memory (occurrences dated 2026-07-12 through 2026-07-30) - despite the memory already documenting the rule clearly each time.

## Context

This is filed HERE (global `~/.claude/todos/`), not in `claude_usage_in_taskbar`'s own backlog, because the root cause and fix live outside that repo - in `~/.claude/snippets/auto-commit.md` and/or a global hook - and any full-auto-imported project is equally exposed, not just this one. (Originally mis-filed as that project's local todo `307-enforce-auto-commit-no-ask-hook.md`; Joe caught it during `/close` on 2026-07-30 - "why would it be in this project specifically???" - and it was moved here.) Passive memory recall at "draft the end-of-turn report" time has proven unreliable across 7 separate sessions - the memory is read, understood, and then not applied at the actual decision point anyway. That's an enforcement gap, not a "be more careful" fix.

Two distinct failure shapes have been observed, both need covering:
1. **Invitation phrasing** - an explicit `AskUserQuestion`, or a passive "let me know if you want /commit run" / "ready for /commit whenever" closing line. (Occurrences 1-6.)
2. **Silent omission** - the turn ends with zero commit-related sentence at all; the diff is just left staged. This slipped past any fix that only targets literal invitation phrasing, since there's no commit-adjacent clause to catch. (Occurrence 7, 2026-07-30.)

## Approach

Ideas to evaluate in whichever session picks this up (not yet decided - this is the capture, not the design):

- A `Stop`-hook-style check (mirroring how `project_turn_status_marker.md` describes the Stop hook already enforcing the `cc-status` marker) that inspects the just-finished turn: if a non-gitignored file was edited/written in a full-auto-imported repo, verification ran and passed, and the turn is ending WITHOUT a `/commit` (or equivalent skill) invocation having happened (i.e. `HEAD` didn't move and no chained commit is pending), block or warn - same enforcement shape as the existing marker-less-turn block. This shape catches BOTH failure modes above (it doesn't care whether the turn asked or just said nothing).
- Alternatively, a lighter-weight self-check woven directly into `auto-commit.md`'s own text as an explicit, impossible-to-skip step ("before ending ANY turn that touched a non-gitignored file in a full-auto repo, stop and check: does this turn's change satisfy every auto-commit condition? If yes, the ONLY valid action is running `/commit` - no question, no offer, no silent omission, no mention of asking").
- Consider whether this needs to be a hook at all, or whether the repeated failure is specifically about the LLM's own turn-ending behavior in a way no external hook can intercept before the text is already sent - in which case the fix is purely a system-prompt/skill-text strengthening, not tooling. Given occurrence 7 (silent omission, no interceptable "commit-related sentence" to hook on), a hook that inspects the ACTUAL git state (HEAD vs. dirty working tree) rather than parsing the response text is the more robust option - it doesn't rely on the failure manifesting as specific wording.

## Acceptance

- A cold session in a full-auto-imported repo, given a fully-verified single-file change, runs `/commit` without any `AskUserQuestion` call, any "let me know if you want to commit" phrasing, AND without silently ending the turn with the change left uncommitted.
- Whatever mechanism is chosen must not block or slow down commits in NON-full-auto repos (this behavior is opt-in via the `full-auto.md` import).

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] [ARCH] Ship the auto-commit enforcement hook, or leave enforcement on memory plus /close nudges? This exact design already went 7 rounds of /iterate-it plus a solo high-effort rate-it and topped out at 5/10, not shipped (see `done/211-auto-commit-enforcement-hook.md`). Re-confirmed 2026-08-12: Stop hooks fire for EVERY session including subagents, and nothing in the Stop payload (`session_id`, `transcript_path`, `stop_hook_active`, `last_assistant_message`) distinguishes a subagent whose own rules FORBID committing from the main session that should commit. Options: (a) ship a non-blocking reminder-only hook scoped to the single-session no-worktree case, accepting false reminders on subagent and foreign-repo stops; (b) leave enforcement as it is and do not reopen without a confirmed way to detect subagent-ness from the Stop payload; (c) spike only the detection question first, then decide. Recommended: (b), because a 5/10 verdict plus an unresolved detection gap is not a shipping signal, and (a) just trades a wedge for recurring noise.

## Notes

Seven prior occurrences (with exact Joe quotes) are preserved in `feedback_auto_commit_full_auto_projects.md` in `claude_usage_in_taskbar`'s project auto-memory - read that file first, it has the full incident history and is more detailed than this todo needs to restate. All seven occurrences happened in that one project so far; if this recurs in a different full-auto project, log it there too and cross-reference back to this todo rather than duplicating the fix design.

**2026-07-29 update (from the prior, now-superseded project-local todo):** sixth occurrence happened, then Joe asked Claude to "figure out why" and Claude offered exactly the two options this todo already sketches (Stop-hook guard vs. keep relying on memory). Joe deferred the decision to a separate chat instead of answering inline there. Whoever picks this todo up next: search recent sessions/memory for whether that conversation already settled on an approach before re-presenting the same two options.

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: new Stop hook `hooks/auto-commit-guard.py`, same shape as the existing
  `hooks/status-marker-guard.py`. Fires when a done-status marker appears in a repo whose
  `CLAUDE.md` imports `full-auto.md` AND the tree has tracked, non-gitignored dirty files with no
  matching fresh commit. Block, do not warn, naming `/commit`. Wire into `settings.json`'s `Stop`
  array. It inspects git state rather than response text, which is what catches both the
  invitation-phrasing and the silent-omission failure shapes. This was produced by a strict
  second-pass re-triage that specifically asked whether a defensible answer exists without the dev;
  it concluded yes. Not executed only because the session ended.

## Merged in (2026-08-11)

Absorbed todos 67, 211 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
