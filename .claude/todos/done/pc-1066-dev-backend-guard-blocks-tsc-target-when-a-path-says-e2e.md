<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=e8180b31 -->
<!-- duplicate-checked: hits are other guards (em-dash, cargo pipe, shell write, sensitive file); none covers dev-backend-guard's e2e/target matching -->
# dev-backend-guard blocks a plain `tsc --target es2022` because a file path contains "e2e"

**Type:** task
**Origin:** ai

## Goal

`hooks/dev-backend-guard.py` stops treating a TypeScript compile as an e2e run against a dev
backend just because one of the compiled file paths contains `e2e`.

## Context

Hit 2026-10-02 in the cueline repo (`/auto-do-todos` run). This command was blocked:

```
npx tsc --noEmit --strict --skipLibCheck --module esnext --moduleResolution bundler --target es2022 --types node e2e-tauri/*.ts playwright.tauri.config.ts
```

The guard printed its Twilio/CloudWatch incident text and called `es2022` an "e2e suite target".
Cause, read in the hook this session: `E2E_ENTRYPOINT_RE = re.compile(r"run-all|e2e")`
(`hooks/dev-backend-guard.py:78`) matches the `e2e-tauri/` path argument, and `E2E_TARGET_RE`
(`:81-82`) matches tsc's own `--target es2022`. The comment at `:75-77` already knows `--target` is
also a tsc/cargo/vite flag, but the entrypoint check is satisfied by any substring in the segment,
including a file path. cueline is not a zng repo and has no dev backend.

Workaround used: a scratch tsconfig file, so `--target` no longer appeared on the command line.

## Approach

1. Require the e2e entrypoint to be a script/command token (`npm run e2e*`, `pnpm e2e*`,
   `run-all`), not any substring of the segment, or exclude segments whose executable is `tsc`.
2. Consider scoping the whole guard to zng repos (cwd or `origin` under `zirtue-corp`), since its
   incident and its local/dev vocabulary are zng-specific.
3. Add a self-test case for the command above.

## Acceptance

- The command above is allowed; the guard's existing zng e2e-against-dev cases still block.

## Notes

- Completed by /loop-todos cycle 1 (2026-10-05), test-first (RED against HEAD, then GREEN).
