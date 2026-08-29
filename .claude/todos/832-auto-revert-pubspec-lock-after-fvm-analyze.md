<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=6, reconfirm-count=2, content-hash=7728921b -->
<!-- duplicate-checked -->
# Stop hand-reverting pubspec.lock after every fvm flutter analyze

**Type:** skill-improvement
**Origin:** ai

## Goal

Remove the manual `git checkout -- pubspec.lock` step that every zng-app session repeats after
running `fvm flutter analyze` or `fvm flutter run`.

## Context

Surfaced 2026-08-28 in a zng-app session. `fvm flutter analyze` and `fvm flutter run` both run an
implicit `pub get` that rewrites `pubspec.lock` (this session saw `matcher`, `meta`, `test_api`
and `vector_math` bumped every single time). The lock churn is unrelated to any change being made,
and zng-app's own `.claude/commit-style.md` explicitly names `pubspec.lock` as a file to leave
uncommitted:

> "a lock file like `pubspec.lock` that got touched as a side effect of running
> `flutter analyze`/`pub get`, leave it uncommitted and ask first"

The existing memory `reference_zng_app_pubspec_lock_churn` documents the behaviour, so every
session knows about it - and then still runs the revert by hand. It was done 4+ times in this one
session alone. Knowing about a chore is not the same as not having to do it.

This is a global-tooling item, not a zng-app one: the same pattern applies to any Flutter repo
where the lock is committed and analyze rewrites it.

## Approach

Options, cheapest first:

1. A `PostToolUse` hook matching Bash/PowerShell commands containing `flutter analyze` or
   `flutter run`, which checks whether `pubspec.lock` is the ONLY newly-dirty file and, if so,
   reverts it and prints one line saying it did. Must not fire when the lock was already dirty
   before the command, and must not fire when other files changed in the same window, since that
   suggests a genuine dependency change.
2. If a hook proves too blunt (concurrent sessions sharing the checkout make "newly dirty" hard to
   attribute), settle for a line in the zng-app `verify` skill instead and close this as won't-do.

Check `hooks/` for an existing PostToolUse example that inspects git state before writing a new
one.

## Acceptance

- [ ] Running `fvm flutter analyze` in zng-app leaves `git status` free of `pubspec.lock`
- [ ] A genuine `pubspec.yaml` dependency change still updates the lock and leaves it dirty
- [ ] `python ci/run_all.py` passes
