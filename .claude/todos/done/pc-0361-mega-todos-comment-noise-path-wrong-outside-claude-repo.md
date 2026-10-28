<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /mega-todos' injected commit block gives a comment-noise path that only resolves inside ~/.claude

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix the prefilter invocation in `/mega-todos`' injected commit block so it works in the project repos the skill is actually run in.

## Context

`~/.claude/skills/mega-todos/SKILL.md`, in the verbatim "injected commit block" that every builder prompt is supposed to carry, step 3 says:

```
   Run it via Bash from the repo root, never pasted inline: a bare `$0` in a skill's own body gets
   rewritten by skill-argument substitution, which is exactly why this lives in a script on disk.

   bash skills/commit/comment-noise.sh <FILES>
```

That relative path only resolves when the repo root IS `C:\Users\tecno\.claude`. In any other project - which is every normal `/mega-todos` run - `skills/commit/comment-noise.sh` does not exist and the command fails.

Hit on 2026-08-16 during a 22-todo run in `claude_usage_in_taskbar`. The orchestrator noticed while authoring the dispatches and substituted the absolute path (`bash "C:/Users/tecno/.claude/skills/commit/comment-noise.sh" <FILES>`), so no builder actually broke - but that was a catch, not a guarantee. An orchestrator that pasted the block verbatim, exactly as the skill instructs ("Paste this verbatim into every builder prompt"), would have shipped 20 builders whose comment-noise prefilter silently failed.

The instruction to paste verbatim is what makes this bite: the block is explicitly not meant to be edited per dispatch, so the one path in it that needs editing is invisible.

Same issue applies to the two sibling prefilters the delegation doctrine requires (`em-dash.sh`, `secret-scan.sh`), which the injected block does not mention at all even though `~/.claude/refs/delegation-doctrine.md`'s "Every builder prompt embeds, without exception" list requires all three.

## Approach

1. In `~/.claude/skills/mega-todos/SKILL.md`, change the injected block's step 3 to the absolute path: `bash "C:/Users/tecno/.claude/skills/commit/comment-noise.sh" <FILES>`. Forward slashes work in git-bash on Windows and avoid the backslash-escaping problem.
2. Add `em-dash.sh` and `secret-scan.sh` to the same step, with their differing semantics stated: comment-noise and em-dash are auto-fixed by the builder, a secret-scan hit STOPS the builder and is never auto-fixed.
3. Check whether `~/.claude/refs/builder-preamble.md` has the same relative-path assumption anywhere, and fix it there too if so - that file is the other verbatim-paste source.
4. Grep the rest of `mega-todos/SKILL.md` for any other repo-relative path that assumes the `~/.claude` repo.

## Acceptance

- The injected block's commands resolve when pasted verbatim into a builder working in an arbitrary project repo.
- All three prefilters named, with the secret-scan stop-do-not-fix distinction explicit.
- No remaining repo-relative path in the block.

## Notes

- Surfaced during `/close` Phase 1 on 2026-08-17, from a `/mega-todos` run in `claude_usage_in_taskbar`. Filed here rather than in that project's backlog per CLAUDE.md: a finding about the global tree belongs in this repo's own backlog.
- Done 2026-08-17: the injected commit block's step 3 now uses absolute forward-slash paths (bash 'C:/Users/tecno/.claude/skills/commit/<script>.sh') and names all three prefilters the delegation doctrine requires, with their differing semantics stated - comment-noise and em-dash are auto-fixed by the builder, a secret-scan hit STOPS it and is never auto-fixed. Verified all three scripts exist on disk. Approach steps 3 and 4 came back needing nothing: refs/builder-preamble.md mentions no prefilter and no .sh at all, so it carries no relative-path assumption, and grepping the rest of mega-todos/SKILL.md found no other repo-relative invocation. Not addressed here because it is a different concern in the same block: todo 364, filed by another session mid-run, covers the block failing dispatch-preamble-guard on its marker strings.
