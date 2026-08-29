<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Get-SentryIssue.ps1's formatted view hides the per-frame path

**Type:** skill-improvement
**Origin:** ai

## Goal

Surface each stack frame's `filename`/`absPath` in the formatted output so triage stops dropping to
`-Raw` plus hand-written JSON parsing.

## Context

Script: `C:\Users\tecno\.claude\scripts\Get-SentryIssue.ps1`.

On 2026-08-26, triaging three `RangeError: Maximum call stack size exceeded` issues in zng-app, the
single load-bearing piece of evidence was **each frame's path**: real dart2js frames resolve to
`.../main.dart.js`, while injected/`eval`'d code reports the page's own document URL. That is what
proved the crashes were not app code.

The formatted output did not show it, so the same workaround was written four separate times in one
session: call with `-Raw`, pipe the JSON into an ad-hoc `python -c` snippet, walk
`entries[].data.values[].stacktrace.frames[]`, and print `filename` / `absPath` / `lineNo`. Four
repetitions of the same parse in one session is the trigger for filing this.

Unverified: the script's source was not read that session, so it is possible a flag already exposes
this and was simply not discovered. Read the script first - if the capability exists, the fix may be
documentation (or a mention in [[reference_sentry_triage_zng_app]]) rather than code.

## Approach

Read `Get-SentryIssue.ps1` first, then either:

- add per-frame `filename`/`absPath` (plus `lineNo`:`colNo`) to the existing frame rendering, or
- add a focused switch, e.g. `-FramePaths`, that prints one compact line per frame, since full paths
  will be noisy in the default view.

Also worth surfacing in the same pass, both used as triage signals that same session: whether
`context`/`pre_context`/`post_context` are empty (Sentry never fetched real source), and the
`mechanism` value.

## Acceptance

- A single invocation shows every frame's path without `-Raw`.
- Re-run against zng-app issues ZNG-APP-AC and ZNG-APP-9G: AC's frames must show the document URL,
  9G's must show `main.dart.js`, with no hand-parsing.

## Notes

- Dropped via /cleanup-todos 2026-08-29: premise false on re-verification. Get-SentryIssue.ps1:144-148 already builds a per-frame location string from filename and lineNo and prints it in the Stack section, which is exactly the capability this todo says is missing.
