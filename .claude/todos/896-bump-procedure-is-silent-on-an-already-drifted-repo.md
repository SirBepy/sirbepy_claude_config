<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 260 added Cargo.toml to the bump list and is done; this is the untreated case where a repo's history predates that fix and contradicts it -->
# The bump procedure is silent on a repo whose version files are already drifted

**Type:** skill-improvement
**Origin:** ai

## Goal

Tell `/commit v` / `bump` / `pushnbump` what to do when a repo's previous `VERSION:` commits
contradict the prescribed file set, so a session stops perpetuating pre-existing drift.

## Context

`done/260-commit-bump-misses-cargo-toml-version.md` already fixed the procedure to include
`src-tauri/Cargo.toml`. The skill now says so plainly. What it does not say is what to do when the
repo's own git history disagrees, and that gap produced a wrong call on 2026-09-02.

Releasing three Tauri repos that day, their previous `VERSION:` commits showed two different shapes.
`windows_taskbar_widgets` moved all five files together. `pomodoro-overlay`'s last six `VERSION:`
commits each touched `package.json` alone. Facing that, the session followed each repo's git
precedent rather than the skill, on the reasoning that copying six consistent prior commits was
safer than a one-file-to-five-file change mid-release.

That was the wrong call, and it left the drift worse. Measured after the releases:

| repo | package.json | tauri.conf.json | Cargo.toml |
|---|---|---|---|
| windows_taskbar_widgets | 0.1.13 | 0.1.13 | 0.1.13 |
| pomodoro-overlay | 0.3.34 | 0.3.16 | 0.3.4 |
| claude_usage_in_taskbar | 0.2.91 | 0.2.3 | 0.1.110 |

Only the repo where 260's fix was actually applied is in sync. The other two are exactly the state
260 was filed to prevent, and 260 documents the cost: `env!("CARGO_PKG_VERSION")` makes the app log a
version six or more releases behind the installed build, and a session reading that log concludes it
has a stale checkout and re-derives its analysis.

Per-repo cleanup is filed separately in each of those two backlogs. This todo is the procedural half:
the skill needs to say that git precedent does not override it.

## Approach

Add one line to the version-bump procedure in `~/.claude/skills/commit/SKILL.md`: before bumping,
compare the current values across `package.json`, any root `.json` with a top-level version, and
`src-tauri/Cargo.toml`. If they disagree, bring them all to the new version in the same commit rather
than copying whatever the last `VERSION:` commit touched, and say so in the summary so the dev sees a
one-file bump became a five-file one.

Name the trap explicitly, since it is what actually misled: a long run of consistent prior commits is
evidence of an unfixed habit, not of a deliberate per-repo convention.

## Acceptance

Running `/commit pushnbump` in a drifted repo brings every version file to the new version in one
commit and reports that it did, instead of reproducing the drift.
