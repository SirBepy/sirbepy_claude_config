<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=5233abda -->
# Skill arg substitution clobbers `$0` inside shell snippets, breaking /commit's comment-noise check

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the harness's skill-argument substitution from destroying `$0` inside embedded shell/awk
snippets, so `/commit`'s comment-noise prefilter is runnable as written instead of needing manual
reconstruction on every single commit.

## Context

Observed 2026-08-07 in the `windows_taskbar_widgets` project, across 6 commits in one session.

`~/.claude/skills/commit/SKILL.md` step 5a embeds an awk script that uses `$0` (awk's "the whole
current line"). When the skill is invoked as `/commit pushnbump`, the body that reaches the model
has every `$0` replaced by the literal argument string:

```
/^\+\+\+ b\// { f=substr(pushnbump,7); run=0; next }
...
| awk '$1=="??"{print substr(pushnbump,4)}'
```

`substr(pushnbump,7)` is not valid awk against a line, so the command cannot be run as printed. A
bare `/commit` with no args presumably substitutes empty string, which is equally broken.

This is a harness-level templating collision, not a typo in the skill: `$0` is being treated as the
"all arguments" positional placeholder (the same convention as `$ARGUMENTS`/`$1`), and shell and awk
both legitimately use `$0` for something else entirely.

Cost observed: the comment-noise check is mandatory on every commit ("always runs, no size/skip
gate"), so this fires constantly. Each time, the model must notice the corruption and hand-rebuild
the awk script from intent, which is exactly the kind of silent-reconstruction step that eventually
gets skipped instead. `~/.claude/skills/create-pr` carries a range-mode variant of the same command
(per `commit/comment-noise.md`), so it is very likely affected identically.

## Approach

Pick one, in rough order of preference:

1. **Escape at the source.** Rewrite the awk in `commit/SKILL.md`, `commit/comment-noise.md` and
   `create-pr` to avoid a bare `$0`: awk's `substr($0,7)` can be written as `substr($NF+0?$0:$0,7)`
   (ugly) or, much better, the whole prefilter can be moved into a real script file
   (`~/.claude/skills/commit/comment-noise.ps1` / `.sh`) that the skill simply CALLS. A script on
   disk is never arg-substituted, and it also removes ~15 lines of inline shell from the skill body,
   which is a token win on every commit.
2. **Escape at the placeholder.** If the harness supports an escape (`$$0`, `\$0`), apply it to
   every embedded shell snippet and note the rule in `bepy-skill-creator` so new skills do not
   reintroduce it.
3. **Narrow the substitution.** If the harness's placeholder set is configurable, drop `$0` from it
   and rely on `$ARGUMENTS` alone. Verify no existing skill depends on `$0` meaning "all args".

Option 1 is the only one that does not depend on harness behaviour Claude cannot change, and it is
the same move `close/complete-todo.ps1` and `close/claim-todo.ps1` already made for their own
multi-step sequences. Prefer it unless the escape in option 2 is confirmed to exist.

## Acceptance

- `/commit pushnbump` prints a step 5a command that runs verbatim, with no manual reconstruction.
- The same holds for a bare `/commit` and for `/create-pr`'s range-mode variant.
- A grep across `~/.claude/skills/**` for a bare `$0` inside a fenced shell/powershell block returns
  nothing, or only occurrences that are verified safe.

## Notes

- Do NOT "fix" this by telling the model to be careful and rebuild the script. That is the current
  de facto behaviour and it is exactly what makes the check skippable under pressure.
- Worth checking whether any other skill embeds `$0`, `$1`, `$2` in shell for non-argument purposes.
  `awk`, `sed` and PowerShell `$_`-adjacent idioms are the likely places.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: move the comment-noise awk prefilter out of `commit/SKILL.md` and
  `commit/comment-noise.md` into a real script, `skills/commit/comment-noise.sh`, invoked with the
  pathspec as an argument. This eliminates the argument-substitution collision entirely, the same
  move `close/complete-todo.ps1` already made. Option 1, the todo's preferred fix. This was produced
  by a strict second-pass re-triage that specifically asked whether a defensible answer exists
  without the dev; it concluded yes. Not executed only because the session ended.

- **Reconfirmed 2026-08-08.** The awk prefilter block was hand-pasted 13 times in one
  `/auto-do-todos` run, once per commit. Every paste is a fresh chance for the `$0` substitution bug
  this todo describes.
- completed, commit 0796403

## Merged in (2026-08-11)

Absorbed todos 56, 57, 249 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
