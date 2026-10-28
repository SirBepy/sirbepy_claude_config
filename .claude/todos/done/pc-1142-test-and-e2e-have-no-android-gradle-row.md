<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=0ba10827 -->
# /test and /e2e have no row for native Android (Gradle) projects

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/test` detect a native Android/Gradle repo and run its fast checks, and make `/e2e` recognise
its instrumented suite, so sessions in such repos stop hand-assembling Gradle commands.

## Context

Surfaced 2026-10-08 during an unattended `/loop-todos` run in
`C:\Users\tecno\Desktop\Projects\annoying_stopwatch` (Kotlin + Jetpack Compose, `gradlew.bat`,
`app/build.gradle.kts`). `skills/test/SKILL.md` Step 1's detection table has rows for Flutter, Node,
Rust/Tauri and Roblox only; a repo with `gradlew`/`settings.gradle(.kts)` and no `package.json`
falls through to "none of the above". The session ran the fast checks by hand five times:

```
gradlew.bat -p <root> "-Dorg.gradle.java.home=C:\Program Files\Eclipse Adoptium\jdk-21.0.2.13-hotspot" testDebugUnitTest lintDebug assembleDebug --console=plain -q
```

Two gotchas any row has to encode:
- `$env:JAVA_HOME` does not persist between tool calls; the JDK must be passed inline as
  `-Dorg.gradle.java.home=...` (recorded in that project's `run-mechanics` memory).
- `connectedDebugAndroidTest` (the instrumented suite) needs a booted emulator and UNINSTALLS the app
  when it finishes, so it belongs in `/e2e`, not in `/test`'s fast floor.

## Approach

1. `skills/test/SKILL.md` Step 1: add a row, marker `gradlew` or `settings.gradle(.kts)` at the repo
   root, stack "Android / Gradle", command `gradlew testDebugUnitTest lintDebug assembleDebug`, with a
   Step 3 bullet covering the inline-JDK rule (find the JDK path from the project's own memory or
   `JAVA_HOME` once, then pass it inline).
2. `skills/e2e/SKILL.md`: add a delegate-table row for Android instrumented tests
   (`connectedDebugAndroidTest`) that requires a booted device and notes the uninstall side effect.

## Acceptance

- `/test` in annoying_stopwatch states "Android / Gradle" as the detected stack and runs unit tests,
  lint and a debug build without the session supplying the command.
- `/e2e` in the same repo runs `connectedDebugAndroidTest` against a booted emulator, or reports
  "no device" plainly instead of "no suite".

## Notes

- Done 2026-10-08: /test Step 1 has an Android / Gradle row plus a Step 3 inline-JDK bullet, /e2e Mode A has a connectedDebugAndroidTest row (needs a booted device, says 'no device' not 'no suite', notes the uninstall). Verified: the row's exact command in annoying_stopwatch exited 0; frontmatter check OK.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved to build as written.
