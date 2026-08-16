<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# comment-noise.sh counts markdown headings as comments, so every .md file false-positives

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `skills/commit/comment-noise.sh` reporting a comment-density violation on markdown files whose
only `#`-prefixed lines are headings, so its output stays trustworthy on the many `.md` files this
repo commits.

## Context

Verified 2026-08-15 during an `/auto-do-todos` run. `bash skills/commit/comment-noise.sh
.claude/todos/334-tauri-code-style-300-line-rule-excludes-colocated-tests.md` reported
`9/22 (40%) longest 3`. Grepping that file for `^\s*(//|#)` returns five lines, and every one is a
markdown heading:

```
3:# code-style/tauri.md's 300-line split rule should exclude colocated Rust test modules
8:## Goal
11:## Context
18:## Approach
21:## Acceptance
```

The same run saw `314-flutter-e2e-login-preamble-section.md` flagged at `11/39 (28%)`, also purely
headings. `/commit` step 5a says a comment-noise hit is trimmed without asking, which on a markdown
file means mangling headings to satisfy a check that was never about them. Every builder dispatch in
that run had to carry an explicit "this is a known false positive on `.md`, do not mangle headings"
caveat, which is the tell that the script itself is wrong.

The script is correct on real code. This is only about the language dispatch.

## Approach

Skip or re-scope the check by file extension. A `.md` file's `#` is a heading, never a comment;
inside a fenced code block it may be a comment, which is the only case worth counting there.

Options, in preference order:

1. Skip `.md` files entirely. Simplest, and matches the fact that the comment cap is a code rule.
2. Count only lines inside fenced code blocks for `.md` files, so an over-commented example still
   gets caught.

Whichever lands, mirror it in `skills/commit/comment-noise.md` (the doc that defines the cap) and
drop the per-dispatch caveat from `refs/delegation-doctrine.md`'s comment-noise bullet if it names
this workaround.

## Acceptance

- Running the script over any todo file in this backlog prints nothing.
- Running it over a real code file with a genuinely over-commented block still flags it, proving
  the fix did not just disable the check.
- `/commit` step 5a's "trim it, don't ask" instruction is safe to follow literally again.

## Notes

- Done 2026-08-16, commit 4bed8e1. comment-noise.sh now skips .md and .mdx entirely (option 1, Joe's pick), so a heading is never counted as a comment. Verified against the original bug case (todo 334's file at 8d1df43^ printed 10/26, now prints nothing) and against a constructed 5-line over-commented JS file, which still flags 5/5.
