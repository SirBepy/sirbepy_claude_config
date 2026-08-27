<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=5, reconfirm-count=1, content-hash=40b606ea -->
<!-- duplicate-checked -->
# Nothing stops loosening a lint or compiler config instead of fixing the code

**Type:** task
**Origin:** ai

## Goal

Block edits to lint, build and compiler configs during a task whose goal was to make the code pass,
so "make the error go away" cannot become "raise the threshold".

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

The failure mode is well known and CLAUDE.md already gestures at it: the testing floor says every fast
check must pass, and `astral-sh/uv`'s AGENTS.md states the sharper version outright, "NEVER assume
clippy warnings or test failures are pre-existing". Neither prevents the easiest way to make a check
pass, which is to edit the check. Loosening a `tsconfig` strictness flag, adding a lint disable to
`.eslintrc`, raising a coverage threshold, or excluding a failing file all satisfy the letter of the
floor.

Nothing in the 41 hooks blocks config-file edits generically. Existing guards are the inverse shape:
they block bad *commands* (package manager, flutter workdir) rather than protecting specific *files*.
Todo 420 adds a sensitive-file guard for credentials; this is the same shape for a different reason.

Reference: `repos/brain-bootstrap_claude-code-brain-bootstrap/dot-claude/hooks/config-protection.sh`.
A PreToolUse hook on Write, Edit and MultiEdit that hard-blocks edits to biome config, `.eslintrc`,
`tsconfig`, `pyproject.toml`, `Cargo.toml`, `go.mod` and `.idea/`.

The obvious problem with copying it as-is: **those files get edited legitimately all the time.**
Adding a real dependency touches `Cargo.toml` and `pyproject.toml`. Configuring a new project touches
`tsconfig`. A blanket block would fire constantly and get disabled, which is the pattern to avoid
(same reasoning as todo 419's severity-dial note).

So the useful version is narrower and the design question is what narrows it:

- **By intent, not by file.** The problem is not editing `tsconfig`, it is editing `tsconfig` while
  the current task is "make typecheck pass". That is hard to detect mechanically, but todo 427 is
  already building exactly this signal: a session-scoped flag file set when source files were edited,
  used to decide whether the verify floor should run. A related flag could mark "a check is currently
  failing", and config edits could be gated only then.
- **By hunk direction.** Adding a dependency to `Cargo.toml` is not the same edit as removing a lint
  rule. A guard could allow additions to dependency sections while flagging removals from rule or
  strictness sections. More precise, more work, and language-specific.
- **`ask` rather than `deny`.** The cheapest version that still works: prompt on any config edit,
  which surfaces the decision to Joe without blocking legitimate work.

## Approach

1. Read `config-protection.sh` for its file list, then discard its blanket-deny approach.
2. Read todo 427 first. If its flag-file mechanism lands, this guard can key off "a check is failing
   right now", which is the version that actually targets the failure mode instead of the file. **That
   sequencing is the main decision in this todo.**
3. If 427 has not landed, ship the `ask` version. Prompt on edits to the config file list, with a
   message naming the specific concern ("is this fixing the config, or avoiding a failing check?").
   Cheap, honest, and not disable-bait.
4. Build the file list from what this machine actually uses: `tsconfig`, `.eslintrc`, biome,
   `analysis_options.yaml` (Dart, which the reference omits and which matters here), `pyproject.toml`,
   `Cargo.toml`, `pubspec.yaml`, and any vitest or jest config. Do not include `.idea/`, which is not
   in use.
5. Consider the higher-value variant if the hunk-direction approach looks tractable for even one
   language: flag removals from a strictness or rules section while allowing dependency additions. Only
   attempt this if step 4's list has an obvious candidate; do not build six language parsers.
6. Fixture tests, including the negative cases that matter most here: adding a dependency must pass,
   removing a lint rule must be caught.

## Acceptance

- Adding a dependency to `Cargo.toml` or `pubspec.yaml` is not blocked.
- Removing a strictness flag or lint rule is caught (blocked or asked, per the chosen design).
- Dart's `analysis_options.yaml` is covered, not just the JS and Rust files from the reference.
- The guard is `ask`, or it is `deny` gated on a failing-check signal. **Not a blanket deny.**
- Fixture tests pass with real output, including negatives.

## Notes

A blanket deny on `tsconfig` and `Cargo.toml` will be disabled within a week and then protects
nothing. The whole value here is in narrowing it correctly, which is why this depends on 427.

If 427 does not land and the `ask` version proves noisy in practice, closing this todo is a legitimate
outcome. An ignored prompt is worse than no prompt.
