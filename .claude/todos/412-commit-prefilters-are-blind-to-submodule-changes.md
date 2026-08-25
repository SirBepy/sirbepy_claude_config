<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The commit prefilters silently pass on every submodule change

**Type:** skill-improvement
**Origin:** ai

## Goal

`comment-noise.sh`, `em-dash.sh` and `secret-scan.sh` return empty for any file inside a git
submodule, so a commit touching only submodule files passes all three gates without any of them
having read a single line of the diff. The gate reports clean and means nothing.

## Context

Found 2026-08-20 during a `/mega-todos` run in `claude_usage_in_taskbar`, by the builder landing
todos 81, 205 and 450 inside the `vendor/tauri_kit` submodule.

All three scripts resolve a diff via `git diff HEAD -- <path>` against the PARENT repo's index. A
parent repo tracks a submodule as a single gitlink entry holding one SHA, not as a tree of files, so
that command returns nothing for `vendor/tauri_kit/README.md` even when the file has real
uncommitted changes inside the submodule. Confirmed directly by the builder: it ran
`git diff HEAD -- vendor/tauri_kit/README.md` in the parent and got empty output while a real diff
existed in the submodule working tree.

**This is a silent pass, not an error**, which is the dangerous shape: `prefilter-gate.sh` exits 0
and the caller reads that as "three gates cleared". Of the three, `secret-scan.sh` is the one that
matters most - it is the only prefilter whose whole purpose is to stop a commit, and it is exactly as
blind here as the other two.

That builder noticed and compensated by hand-checking every changed block, then reported it. Nothing
guarantees the next one does.

`/mega-todos`'s own injected commit block and `refs/builder-preamble.md` both instruct builders to
invoke the scripts with parent-relative paths, which is the invocation shape that produces this
no-op. So the skill text is part of the problem, not just the scripts.

Duplicate-guard note: the write hook flagged `done/02-enforce-auto-commit-no-ask-hook.md` and
`done/225-close-skill-unpushed-scope-empty-after-commit-push.md`. Both were read; they are about
asking before committing and about `/close`'s Phase 2 scope respectively, sharing only the generic
words "commit" and "silently". Distinct subject, filed deliberately.

## Approach

1. Reproduce first, in any repo with a submodule: change a file inside the submodule, run
   `bash skills/commit/secret-scan.sh <submodule-path>/<file>` from the parent root, confirm empty
   output and exit 0. **Do not write a fix before seeing the empty output** - the whole finding is
   that it looks like a pass.
2. Decide the behaviour. Two candidates, and the choice is the real work here:
   - **Detect and re-run inside the submodule.** If a passed path resolves inside a submodule
     (matches a `git submodule status` entry), re-run the diff with
     `git -C <submodule-root> diff HEAD -- <rel>`. Correct, but each script needs submodule awareness.
   - **Detect and refuse.** Print a loud "prefilter cannot see inside a submodule, check by hand" and
     exit non-zero. Cheaper and safer, but it makes every legitimate submodule commit noisy.
   Recommended: detect-and-re-run, with detect-and-refuse as the fallback if path resolution turns out
   to be fragile. A gate that silently passes is worse than one that loudly refuses, but a gate that
   actually reads the diff beats both.
3. Whichever lands, fix the instruction text too: `skills/mega-todos/SKILL.md`'s injected commit block
   and `refs/builder-preamble.md` currently tell builders to use parent-relative paths.

## Acceptance

- A deliberately planted secret in a submodule file makes `secret-scan.sh` exit non-zero. Prove it by
  planting one, running the script, and removing it - a green run on an unmodified submodule proves
  nothing, which is precisely the bug being fixed.
- The same for an over-long comment block (`comment-noise.sh`) and an added em dash (`em-dash.sh`).
- A normal, non-submodule commit's behaviour is byte-identical to today.
- `prefilter-gate.sh`'s exit code still reflects all three.

## Notes

- Scope check before starting: this only matters for repos that actually vendor a submodule.
  `claude_usage_in_taskbar` (`vendor/tauri_kit`) is the known one.
