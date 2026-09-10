<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=9, reconfirm-count=1, content-hash=a9ae656f -->
<!-- duplicate-checked -->
# /code-check drops `.md` from scope, so it reviews nothing in the `~/.claude` repo

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/code-check` produce a real review when the scope is markdown, in a repo where markdown IS the
artifact. Today a standalone `/code-check` on a skill/hook-doc change stops after Step 0 and reports
nothing, which reads as "clean" rather than "not reviewed".

## Context

Observed 2026-09-05 in the `~/.claude` repo. The session committed one new file,
`skills/loop-todos/SKILL.md` (146 lines), and ran `/code-check shas:907beab` on it.

`skills/code-check/SKILL.md`'s "Filter to code files" section says:

> After resolving, filter to code files only. Drop: `.md`, `.json`, `.toml`, `.yaml`, `.yml`,
> `.gitignore`, anything under `.for_bepy/`, `.claude/todos/`, or `memory/`.
>
> If the filtered list is empty (and Step 0 produced no findings): print "No code files in scope."
> and stop.

In this repo that drop list eliminates almost every diff there is: skills, refs, snippets, and
`CLAUDE.md` are all `.md`. A skill change therefore gets Step 0 (description budget) and nothing
else, and Step 4's project-convention pass never runs, even though Step 4 is where the value sits
for a prose artifact governed by `bepy-skill-creator`'s written FAIL/WARN checklist.

The session only got a real review by overriding the filter by hand in the dispatch prompt: it told
the subagent to run Steps 0 and 4 in full regardless, and named `bepy-skill-creator/SKILL.md`,
`CLAUDE.md` and `close/ai-todos-format.md` as the binding docs. That override found a genuine
BLOCKER (the new skill instructed writing into a `## Decisions` section that
`close/ai-todos-format.md` never defines; fixed in `2aa34b2`). An unmodified `/code-check` run would
have printed "No code files in scope." and missed it.

The filter is right for a normal product repo, where a `.md` really is documentation. It is wrong
for a config repo whose deliverable is markdown.

## Approach

In `skills/code-check/SKILL.md`, make the filter conditional rather than absolute. Rough shape:

- Keep the existing drop list as the default.
- Add a prose-artifact branch: when a scoped `.md` is a `SKILL.md`, or sits under a repo whose
  deliverable is markdown, keep it in scope for Steps 0 and 4 and explicitly skip Steps 1-3 (size,
  DRY, dead code do not apply to prose) with a printed line saying so, rather than dropping the file
  and stopping.
- For Step 4's "discover the binding docs" list, name `skills/bepy-skill-creator/SKILL.md` as the
  binding written convention for any `SKILL.md` in scope. It already has the FAIL/WARN checklist;
  Step 4's quote-the-rule requirement works against it unchanged.
- Decide, and write down, how the branch is detected. Options: hardcode the `~/.claude` repo root,
  key off the filename being `SKILL.md`, or read a per-repo opt-in marker. Filename-keyed is the
  narrowest and needs no new config.

Do not widen this into "review every `.md`". A README edit in a product repo should still drop out.

## Acceptance

- `/code-check` invoked on a scope containing only a `SKILL.md` runs Steps 0 and 4 and prints a
  finding count, never "No code files in scope."
- Steps 1-3 are visibly skipped with a stated reason, not silently.
- `/code-check` on a `.md`-only scope in a normal product repo still drops out as it does today.
- `python ci/run_all.py` passes.

## Verify

Re-run the exact case that surfaced this: `/code-check shas:2aa34b2` from the `~/.claude` repo root.
It must review `skills/loop-todos/SKILL.md` against `bepy-skill-creator`'s checklist without any
hand-written override in the dispatch prompt.

## Notes

`/close` Phase 2 already skips itself when only docs changed, so this gap is only reachable through
a standalone `/code-check` invocation, which is exactly how it was hit here.
