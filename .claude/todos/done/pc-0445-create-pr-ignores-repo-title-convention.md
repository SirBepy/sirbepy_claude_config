<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=3, content-hash=d66836c5 -->
<!-- duplicate-checked -->
# /create-pr titles PRs in its own style instead of the repo's

**Type:** skill-improvement
**Origin:** ai

## Goal

`/create-pr` should title a PR the way the target repo already titles PRs,
instead of applying its own global `FEAT:` / `FIX:` prefix convention
everywhere.

## Context

Found 2026-08-20 on `revaire-mobile`. `/create-pr` produced:

```
FEAT: Choose an ephemeral bundle from a list and flag a superseded build
```

Every one of the 11 most recent merged PRs in that repo uses conventional
commits with a scope and the Linear ticket id:

```
chore(tooling): store .fvmrc in fvm's own byte format (REV-5343)
feat(design): land the Figma production sync plugin as standalone tooling (REV-5237)
fix(flight): sharpen card divider rendering and details alignment (REV-5236)
ci(release): separate develop and production release identities (REV-5331)
```

Joe noticed and asked for the rename. Corrected by hand to
`feat(ephemeral): choose a bundle from a list and flag a superseded build (REV-5312)`.

Two compounding problems:

1. The skill has no step that looks at how the repo actually titles PRs. Its
   `## Prefixes` list is stated as if universal.
2. The rename could not be applied through normal means. `hooks/pr-guard.py`
   blocks raw `gh pr edit` unless `/create-pr` wrote a fresh
   `.pr-marker-<suffix>`, and its `CLAUDE_PR_HOOK_BYPASS=1` escape reads the
   hook process's own env, so a session cannot set it from inside a command
   string. The only sanctioned path was re-running `/create-pr` in edit mode,
   which regenerates the whole body when all that was wanted was a title. Joe
   approved a `gh api --method PATCH .../pulls/<n>` instead.

## Approach

1. In `/create-pr` step 1 (preconditions, already runs cheap single-line
   commands), add a title-convention probe:
   `gh pr list --state merged --limit 10 --json title --jq '.[].title'`.
   One call, ~10 short lines.
2. Feed those titles to the drafting subagent as the convention to match, and
   say explicitly that they outrank the skill's own `## Prefixes` list. Note in
   `drafting-rules.md` that the prefix table is the FALLBACK for a repo with no
   discernible pattern, not the default.
3. If the observed titles carry a ticket id and the branch name contains one
   (`rev-5312-...` -> `REV-5312`), include it. That is where the `(REV-5312)`
   suffix comes from.
4. Separately, give `/create-pr` a title-only edit path that writes the marker
   and edits just the title, so a rename never forces a full body regeneration.
   That closes the pr-guard gap that made this awkward to fix.

Rejected: hardcoding a per-repo convention into each project's `CLAUDE.md`.
Reading the last 10 merged titles works in every repo with zero setup and stays
correct when a team changes convention.

## Acceptance

- Running `/create-pr` on a `revaire-mobile` branch proposes a
  `type(scope): lowercase (REV-XXXX)` title without being told to.
- Running it on a repo whose merged PRs use bare sentence titles does NOT force
  a conventional-commit prefix on them.
- A title-only rename is possible through the skill without regenerating the
  body, and without needing `CLAUDE_PR_HOOK_BYPASS`.
- The probe adds at most one `gh` call to step 1.

## Notes

- The Slack announcement that prompted the review was about CI workflow names,
  not PR titles. The title convention came from reading the merged PR list, not
  from any documented rule, which is exactly why an automated probe beats
  documentation here.
- Related surface: `hooks/pr-guard.py` deliberately does not gate
  `gh pr comment` / `gh pr review`. A title-only edit arguably belongs in that
  same not-gated category; worth deciding when step 4 is built.
- Done via /mega-todos 2026-09-01 (f1f14b4): create-pr probes the repo own merged-PR title convention before titling instead of assuming a prefix.
