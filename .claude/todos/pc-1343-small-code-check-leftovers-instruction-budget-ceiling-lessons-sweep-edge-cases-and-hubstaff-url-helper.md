<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep of backlog and done/ for CEILING_TOKENS, lessons_sweep, dailyUrl found only done/pc-1281 (the CLAUDE.md trim that shrank the file) and nothing for the others. -->
# Small /code-check leftovers: budget ceiling, lessons sweep edge cases, HubStaff URL helper

**Type:** task
**Origin:** ai
**Summary:** Lower the instruction-budget ceiling to the trimmed CLAUDE.md size and fix four small leftovers the push-gate review found but did not apply.

## Goal

Close the loose ends the 2026-11-08 push gate review left as judgment calls.

## Context

- `ci/check_instruction_budget.py:19-21`: `CEILING_TOKENS = 6558`, a ratchet whose own comment says to lower it when CLAUDE.md shrinks. Commit 79cac37 cut CLAUDE.md from about 6755 to 5172 tokens, so 1386 tokens of rules could creep back in unflagged. Lowering needs no say-so; the margin to leave is the dev's call (memory note: headroom near 0 before the trim).
- `skills/cleanup-memory/lessons_sweep.py:286-297` (promote UPDATE branch) and `:216-227` (`lesson_text`): `paths` and `skills` carry over from the prior lesson on UPDATE, `repos` does not, and `lesson_text` cannot write `repos`. A hand-edited lesson with only `triggers.repos` loses its trigger block when re-promoted without `--path`/`--skill`. The CLI has no `--repo`, so only hand-edited lessons are hit.
- `skills/cleanup-memory/lessons_sweep.py:74-84` `client_basenames` re-reads `refs/client-repos.txt` with the same filter as `hooks/_client_repo.py:58-63` `load_client_slugs`. It is read separately on purpose (fail-closed control with its own error handling), so decide whether sharing is worth it.
- `skills/clockify-reconciliator/scripts/hs_addtime.cjs`: the `daily?date=...&filters[user]=...` URL template is inlined in `makeAttempt` (about line 56) and again in `main` (about line 96); the pre-range file had one `dailyUrl` helper. `test_hs_retry.cjs` reaches `makeAttempt` only.
- Unwritten-rule notes only: `d-cargo-sweep-auto.ps1` log lines still say "D:" although `-Drive` is a parameter; `lessons_sweep.py` `build_index` uses `.rstrip(" -")`, which would also strip a genuine trailing "-"; `skills/recall/recall.py` re-warns on stderr every run for a malformed sub digest; `lessons/local-gpu-runs-gentle-limits.md:37` links `[[gemma4-26b-unstable-on-ollama]]`, which exists only as a per-project memory.

## Approach

Lower `CEILING_TOKENS` to CLAUDE.md's current token count plus a small margin; carry `prior["repos"]` through `lesson_text` (with a test) or document that UPDATE rewrites triggers; hoist `dailyUrl(org, user, date)` in `hs_addtime.cjs` and extend `test_hs_retry.cjs` to cover `main`'s first URL.

## Acceptance

`python ci/check_instruction_budget.py` passes at the new ceiling; `python skills/cleanup-memory/test_lessons_sweep.py` (or its sibling in `hooks/test_lessons.py`) covers the `repos` carry-over; `node skills/clockify-reconciliator/scripts/test_hs_retry.cjs` passes.
