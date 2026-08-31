<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=2, content-hash=303aa837 -->
<!-- duplicate-checked -->
# The CI ubuntu portability probe will show a red X forever

**Type:** task
**Origin:** ai

## Goal

Decide what to do about `.github/workflows/ci.yml`'s `portability-probe` job, which is expected to
fail on every single run from now on. Either make it pass, or delete it, but do not leave a job that
is permanently red for a known and accepted reason.

## Context

Filed 2026-08-20, immediately after todo 423 shipped CI to this repo.

`.github/workflows/ci.yml` has two jobs. `checks` runs on `windows-latest` and is the blocking one.
`portability-probe` runs the same `python ci/run_all.py` on `ubuntu-latest` with
`continue-on-error: true`, and exists to answer one question empirically: are the 13
`hooks/test_*.py` suites portable, given they had only ever run on Windows?

**It answered the question on its first run.** Real result from run `32382799312` (sha `2d5f23d`):

- `checks` on windows-latest: **success**.
- `portability-probe` on ubuntu-latest: **failure**, and the run's overall conclusion was still
  **success**, which proves `continue-on-error` does keep it from blocking.

12 of the 13 suites pass on Linux. The one that does not is `hooks/test_todo_duplicate_guard.py`,
failing exactly two cases:

```
[FAIL] path: real double-.claude absolute path: 'C:\\Users\\tecno\\.claude\\.claude\\todos\\363-x.md' -> None
[FAIL] path: relative backslash path: '.claude\\todos\\363-x.md' -> None
```

Those two cases assert on deliberately Windows-shaped backslash paths. Failing them on POSIX is
correct behavior for a guard on a Windows-only machine, not a defect in the guard.

So the probe has already delivered its entire value. What remains is a job whose red X carries no
information, and a red mark that means nothing is exactly how a whole CI setup stops being trusted.
That is the specific failure mode todo 423 was written to avoid.

## Approach

Three options, in rough order of preference:

1. **Skip the two Windows-only cases on POSIX** in `hooks/test_todo_duplicate_guard.py`, gated on
   `os.name` or `sys.platform`, and print them as SKIPPED rather than silently dropping them (a
   silently reduced case count is how a suite quietly stops testing anything). Then the probe goes
   green and becomes a real portability signal that would catch future rot.
2. **Delete the `portability-probe` job.** It answered its question; the answer is written down here
   and in the workflow's own comment. This is the cheapest option and loses only future rot detection.
3. Keep it and accept the red X. Weakest option, and the reason this todo exists.

Whichever is chosen, update the comment above `portability-probe` in `.github/workflows/ci.yml`,
which currently states the question as still open.

**Never edit the hook that is guarding the running session in place.** `todo-duplicate-guard.py` is a
live `PreToolUse` hook on `Write` into `.claude/todos/`. Follow 423's proven procedure: copy to a
scratch tree, reproduce, fix and verify there, then install and re-run `python ci/run_all.py`.

## Acceptance

- `python ci/run_all.py` still exits 0 on Windows, with every `hooks/test_*.py` suite discovered. A
  dropped suite is a regression, so state the discovered count. Expect **11**, not the 13 quoted
  above: todo 416 deleted the two spike suites on 2026-08-20, after the run this todo cites.
- If option 1: a real `ubuntu-latest` CI run where `portability-probe` concludes **success**, linked.
  The two skipped cases must be visible as skipped in that run's log, not absent.
- If option 2: the job is gone and the workflow still concludes success on a real run, linked.
- The workflow comment no longer describes an open question that has been answered.

## Notes

Do not "fix" this by removing the two backslash cases from the test. They cover a real bug class on
the only platform this config actually runs on: `.claude/todos/` path matching with a doubled
`.claude` segment. Skipping them off-platform is fine, deleting them is not.

- **Advanced but NOT finished, 2026-08-31, `/mega-todos` batch 3, commit `1a7005c`.** Option 1 landed:
  the two Windows-only backslash cases in `hooks/test_todo_duplicate_guard.py` now skip on POSIX via a
  platform check and print as SKIPPED rather than being silently dropped, and the comment above the
  `portability-probe` job in `.github/workflows/ci.yml` no longer states the question as open. The
  cases still execute and pass on Windows.
- **Unmet: the linked green ubuntu-latest CI run.** That needs a push, and pushing was not authorised
  in the session that did this work. Nothing else blocks it.
- Correction to this todo's own text: it says `ci/run_all.py` should discover exactly 11 suites. That
  number is now stale. The count was 16 when batch 3 started and is **21** after todo `501` added five
  new guard suites in the same batch. Use the observed number, not 11.
- The builder also saw `ci/run_all.py` exit 1 mid-run on `test_status_marker_guard.py`. That was a
  transient: todo `501` was writing that exact file concurrently. The orchestrator's barrier run
  immediately afterwards was green at 21/21, so there is nothing to chase there.
- Next run: push, link the green ubuntu run, archive.
