<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The em-dash-exempt marker is honored at write time but not at commit time

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/em-dash.sh` honor the same `<!-- em-dash-exempt -->` marker that
`hooks/todos-em-dash-guard.py` already defines, so a todo that legitimately quotes an em dash can be
committed rather than being writable but permanently unstageable.

## Context

Hit live on 2026-08-25 while clearing the tree ahead of a `/mega-todos` run. Two todos quote an em
dash as evidence:

- `.claude/todos/506-em-dash-guard-tool-result-shifts-scan-boundary-past-tool-use.md:22` quotes the
  exact transcript string the guard failed to catch. The character IS the subject of the todo.
- `.claude/todos/491-skill-name-hook-fires-on-relayed-peer-text.md:26` quotes a peer's
  `post_message` body verbatim as the reproduction record.

`hooks/todos-em-dash-guard.py:37` defines `EXEMPT_MARKER = "<!-- em-dash-exempt -->"` and its module
docstring states the doctrine: "invert the problem instead of guessing intent: allow only if
EXEMPT_MARKER is present in the new content or already on disk." Both files were marked accordingly
and both write cleanly.

`skills/commit/em-dash.sh` has no equivalent. It greps added lines for the raw U+2014 bytes and knows
nothing about the marker, so `prefilter-gate.sh` exits 1 and, per `/commit` step 8, a flagged diff is
structurally unable to commit. Both files are staged and uncommittable as of this writing; the other
55 todos in that sweep landed as `95d47fd`.

The two layers were built at different times (`done/307` shipped the Stop hook, `done/318` shipped
the todos write guard and its exemption, `done/290` shipped the commit-time script) and the exemption
was only ever taught to one of them.

## Approach

1. In `skills/commit/em-dash.sh`, skip any file whose content contains the marker. The awk pass is
   per-file already (`/^\+\+\+ b\//` sets `f`), so the cheapest correct shape is to test each
   candidate path for the marker before emitting its hits, not to filter individual lines.
2. Read the marker string from one place rather than hardcoding it twice. If sharing between Python
   and bash is not worth the indirection, hardcode it in the script but reference
   `hooks/todos-em-dash-guard.py:37` in a comment so the two cannot drift silently.
3. Decide scope deliberately: `todos-em-dash-guard.py` only guards `.claude/todos/`, but
   `em-dash.sh` runs over every committed file. Either honor the marker repo-wide, or restrict it to
   `.claude/todos/` to match the write-time guard exactly. Prefer matching the guard, since a
   repo-wide escape hatch on a rule CLAUDE.md states absolutely is a bigger change than this defect
   needs.
4. Add a case to `hooks/test_todos_em_dash_guard.py` or a sibling covering the script, so
   `ci/run_all.py` sees the exemption path.

## Acceptance

- `bash skills/commit/prefilter-gate.sh .claude/todos/491-*.md .claude/todos/506-*.md` exits 0.
- A todo containing an em dash and NO marker is still flagged.
- `python ci/run_all.py` passes.
- The marker string is not duplicated without a cross-reference between the two definitions.

## Notes

Both affected files are already staged with markers in place, so whoever picks this up can verify the
fix against real content instead of a synthetic fixture.

- 2026-08-26, still open, and the cost is now measurable rather than theoretical: `491` and `506`
  have been staged-and-uncommittable across at least three sessions, and each new session's handoff
  has to carry an explicit "leave these two staged, do not commit them" instruction. That standing
  exception is the recurring cost, not the two files themselves.
- **Heads-up for an unattended run:** Approach items 1 to 3 land in `skills/commit/em-dash.sh` and
  are safe to delegate, but item 4 writes to `hooks/test_todos_em_dash_guard.py`, where
  `hooks/sensitive-file-guard.py` returns `ask` and a subagent has nobody to answer it. Do items 1
  to 3 delegated or inline, then either do item 4 in the main thread with the dev present or park it
  explicitly - do not let a builder discover the block mid-dispatch.
- Approach item 3's scope question got a second data point on 2026-08-26: `refs/builder-preamble.md`
  and `refs/delegation-doctrine.md` both gained prose quoting the prefilter rules and neither needed
  an exemption, which is mild support for restricting the marker to `.claude/todos/` as this todo
  already recommends.
