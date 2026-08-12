<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Guard repo-scoped commands against a silently-reset working directory

**Type:** skill-improvement

## Goal

Make it structurally impossible for a cross-repo session to run `flutter` / `dart run build_runner` against the wrong ZNG repo, instead of relying on the agent to remember which directory the shell is in.

## Context

Real incident, 2026-07-31, session driven from `zng-app` while editing `zng-biller`. The shell's working directory reset between tool calls after a `Push-Location`/`Set-Location`, without any error, three times:

1. `flutter analyze` ran in `zng-app` and reported 3 errors that did not exist; they were an artifact of `--no-pub` resolution in the wrong package. This was nearly reported to Joe as "your develop branch is broken."
2. `flutter test <absolute path to a zng-biller test>` failed with `Undefined name 'IntercomService'`, because package resolution came from `zng-app`.
3. **Destructive:** `dart run build_runner build --delete-conflicting-outputs` executed in `zng-app` and deleted 8 tracked generated files (`lib/gen/assets.gen.dart`, `lib/gen/fonts.gen.dart`, and six `*_provider.g.dart`). They were committed, so `git checkout --` recovered them, but nothing warned beforehand and an uncommitted equivalent would have been unrecoverable.

The relevant skills (`verify`, `flutter-bump`, `flutter-e2e`, `ios-run`, and the `/close` -> `/code-check` path) all assume the shell is already in the right repo. The global CLAUDE.md rule "Never chain commands" also removes the usual `cd X && cmd` idiom, which pushes toward exactly the stateful `Set-Location` pattern that failed here.

## Approach

1. Add a rule to the shell-commands section of `~/.claude-personal/CLAUDE.md`: any repo-scoped build/test/codegen command must pin its directory in the same invocation, e.g. `Start-Process -FilePath <sdk binary> -ArgumentList ... -WorkingDirectory <abs repo path> -NoNewWindow -Wait -RedirectStandardOutput <file>`, rather than relying on a previous `Set-Location`. Note this is the sanctioned alternative to `cd X && cmd`, which the no-chaining rule forbids.
2. Add a hard rule that `--delete-conflicting-outputs` is never passed unless the working directory is pinned in that same command, and that `--build-filter=<single .g.dart path>` is the default for codegen in a repo where another session may hold generated files.
3. Consider a `PreToolUse` hook: match `flutter`/`dart run build_runner` invocations that carry neither an absolute path argument nor `-WorkingDirectory`, and reject with a message naming the risk. This is the only option that actually enforces it rather than documenting it.
4. Cross-check the ZNG skills listed above and update any that instruct a bare `flutter <cmd>`.

## Acceptance

- A repo-scoped command issued without a pinned directory is either impossible (hook) or unambiguously against a written rule.
- `--delete-conflicting-outputs` cannot run without an explicit directory in the same invocation.
- Verified by deliberately issuing a bare `flutter test` from a cross-repo session and observing the guard fire.

## Notes

- Shipped 2026-08-11, wired in commit f9055ac. hooks/flutter-workdir-guard.py hard-blocks build_runner --delete-conflicting-outputs when no directory is pinned in the same invocation, and also when the pinned path has no pubspec.yaml. Everything else warns and allows. Known coverage gap: ios-run.sh runs its codegen inside an SSH heredoc on the remote Mac, invisible to the hook.
