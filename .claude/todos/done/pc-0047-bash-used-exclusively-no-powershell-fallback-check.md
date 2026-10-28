<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Sessions default straight to Bash, never actually try PowerShell first

**Type:** skill-improvement
**Origin:** ai

## Goal

Either enforce the stated PowerShell-first rule, or rewrite it to match what actually happens, so
the written rule and practiced behavior agree (same shape of gap as
[[07-no-chaining-rule-is-unworkable-in-powershell]]).

## Context

Global `CLAUDE.md`, Shell Commands: "Default to PowerShell... Fall back to Bash only if a
PowerShell attempt fails or the command is genuinely POSIX-only."

On 2026-08-08, a zng-app session (Shortcut backlog audit + git log cross-referencing) ran every
single shell command through the Bash tool - curl, git, python invocations, grep/sed/tr pipelines
- for the entire session, with zero PowerShell tool calls and no documented PowerShell failure
that would justify the fallback. Nothing about the commands used was genuinely POSIX-only; they
were plain curl/git/python calls that run fine under `powershell.exe` too.

This wasn't surfaced by the model at the time - it only came up because `/close`'s retrospective
went looking. Same failure shape as the chaining-rule todos: an absolute-sounding rule with no
enforcement, silently ignored under normal working pressure (Bash's tool description/quoting
model is just more familiar/ergonomic for curl+grep+sed one-liners than PowerShell's).

## Approach

Pick one, likely alongside whatever gets decided for the chaining-rule todos since both are the
same "unenforced absolute shell rule" pattern:

1. **Add a PreToolUse hook** on the Bash tool that checks whether a PowerShell call for
   equivalent work preceded it in the same session/recent window; warn (or block) if not, unless
   the command matches a POSIX-only allowlist (heredocs, certain POSIX-specific flags).
2. **Narrow the rule** to name the actual reason PowerShell is preferred (Joe's fvm/dart/flutter/
   node/gh tooling config) and explicitly carve out ad-hoc curl/git/python one-liners as
   tool-agnostic, so Bash use there isn't a violation in the first place.
3. **Leave as-is, unenforced** - not recommended, same reasoning as the chaining todos: an
   absolute rule nobody follows trains skimming past global rules generally.

## Acceptance

- The Shell Commands section states a rule that either gets followed or is honestly scoped to
  when it actually matters (Joe's dev-tooling commands specifically).
- If option 1, the hook exists and is verified to fire on a real Bash call with no prior
  PowerShell attempt.

## Notes

- Re-verified 2026-08-08: premise still holds.
- Dropped via /cleanup-todos 2026-08-11: no functional gap - the narrowing would only legalize existing behavior. Confirmed by dev 2026-08-11.

## Notes

Found by `/close`'s Phase 1 retrospective on 2026-08-08 in the zng-app project, filed here per
CLAUDE.md's rule that global `~/.claude` tooling findings never go in a project's own backlog.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: narrow CLAUDE.md's Shell Commands PowerShell-first line to name its actual reason,
  the dev's fvm/dart/flutter/node/gh tooling, and explicitly exempt ad-hoc curl, git and python
  one-liners as tool-agnostic. Unlike todos 07 and 21 this has no competing sibling, and the
  narrowing criterion is already stated in the rule's own text, so it is derived rather than a taste
  call. This was produced by a strict second-pass re-triage that specifically asked whether a
  defensible answer exists without the dev; it concluded yes. Not executed only because the session
  ended.
