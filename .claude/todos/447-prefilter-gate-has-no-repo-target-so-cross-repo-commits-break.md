<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# prefilter-gate.sh has no repo target, so the commit skill's cross-repo path breaks it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/prefilter-gate.sh` (and the three scripts it wraps) work when the commit
targets a repo other than the shell's cwd, and fail with a readable message instead of raw `git`
errors when it cannot.

## Context

Hit 2026-08-20 in a revaire-mobile worktree session. `/commit`'s step 5a was run as
`cd ~/.claude-personal/skills/commit && bash prefilter-gate.sh <absolute paths into the other
repo>`. Every wrapped script called git against paths outside its own cwd, so the run printed six
copies of:

```
fatal: <path>: '<path>' is outside repository at 'C:/Users/tecno/.claude'
```

and exited 1. Re-running from inside the target repo with repo-relative paths exited 0 immediately.

Two things make this worth fixing rather than filing as user error:

1. **The failure is indistinguishable from a real hit.** `prefilter-gate.sh`'s contract is "exit 0
   = clean, non-zero = something flagged", and its output was section headers (`=== comment-noise.sh
   ===` etc) with `fatal:` spam above them. A cold session reading that could easily conclude a
   secret was detected and start "fixing" a non-problem, which is the one prefilter the skill says
   to STOP on.
2. **The skill already promises this path works.** `skills/commit/SKILL.md`'s Rules section says
   that when a repo other than cwd is named, `git -C <path>` is used "for every git command this run
   issues, not just some of them" - added by [[done/22-commit-skill-explicit-repo-path-param]]. Step
   5a's scripts are git commands issued by that run, and they have no way to honour it.

## Approach

1. Add an optional `-C <repo-root>` / `--repo <path>` flag to `prefilter-gate.sh` that it forwards
   to `comment-noise.sh`, `em-dash.sh`, and `secret-scan.sh`; each uses `git -C "$repo"` instead of
   bare `git`. Check whether the three scripts already share a git invocation helper before adding
   the flag in three places.
2. Absent the flag, resolve the repo from the first path argument (`git -C "$(dirname "$1")"
   rev-parse --show-toplevel`) rather than assuming cwd. That fixes the observed invocation with no
   caller change at all, which matters because the failing call shape came from following SKILL.md
   literally.
3. Distinguish exit codes so a usage failure cannot be misread as a finding: keep `1` for "a
   prefilter flagged something" and use a distinct code (e.g. `2`) for "could not run" - then say so
   in SKILL.md step 5a, which currently documents only "Exit 0 = all three clean, non-zero = at
   least one prefilter flagged something".
4. Update SKILL.md step 5a's example invocation to show the repo-relative form, since the current
   text does not say which cwd the command assumes.

## Acceptance

- Running `prefilter-gate.sh` from a different repo's cwd with absolute paths into the target repo
  exits 0 on a clean diff, with no `fatal:` output.
- A genuine comment-noise or em-dash hit still exits 1 and prints its labelled section.
- An unrunnable invocation (bad path, not a repo) exits with the new distinct code and one plain
  English line, not raw git errors.
- The existing same-repo invocation used by every normal commit is unchanged - that is the hot path
  and must not regress.

## Notes

- Related but distinct: [[412-commit-prefilters-are-blind-to-submodule-changes]] is about which
  changes the prefilters can SEE inside a repo they resolved correctly; this one is about resolving
  the repo at all.
- Second manifestation, 2026-08-20, claude_usage_in_taskbar session: cwd WAS the target repo, but
  `bash skills/commit/prefilter-gate.sh <files>` (SKILL.md's own literal invocation text) failed
  with "No such file or directory" - the script doesn't live at any repo-relative path at all, only
  under the skill's own base directory (`~/.claude/skills/commit/` or the `-personal` mirror), which
  the SKILL.md text never says. Sharpens item 4's fix: the example invocation needs the actual
  resolvable path (or a `$CLAUDE_SKILL_DIR`-style variable), not just "show the repo-relative form" -
  there IS no repo-relative form, the script isn't in the target repo's tree.
