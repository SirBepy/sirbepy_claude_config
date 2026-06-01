# E2E testing policy

Projects that `@import` this snippet have a browser end-to-end suite (Playwright). It opts the project into routine e2e. The global verification floor still runs FIRST and must pass - e2e is an ADDITIONAL gate, never a replacement for the floor.

## Trigger (mechanical, zero judgment)

Run e2e when you changed app source (`src/**`, excluding `*.test.*` / docs / config) in the current working session - i.e. the diff exists against the branch's last-pushed commit (or against where the session started if nothing is pushed yet) - OR when Joe asks. Never gate e2e on self-judged user-impact; "did this really change behavior" is a banned trigger (it is the same size/impact self-judgment the floor forbids).

## Scope

- **Routine handover** (the trigger above): run only the change-affected specs, using the project's affected-spec command (e.g. `<e2e cmd> --grep <file-pattern>` for Playwright, or a custom `--only-changed` wrapper if the project has one; confirm what git baseline the filter diffs against and that it matches the trigger window). Fast enough that skipping is never permitted, however small the edit.
- **Full suite** (the project's plain `<e2e cmd>`, no filter): run before merge, on release, or whenever Joe asks. Never gate the full suite on self-judged user-impact.

## Execution

Dispatch e2e to a **background subagent**. The sub health-checks the project's configured dev port: if a dev server is already serving (e.g. supervisor-owned), it ATTACHES to that server and must NOT tear it down; only if that port fails its health check does it self-start the dev server, wait for ready, and tear down ONLY its own server on exit (pass or fail). If the subagent exits non-zero or times out without confirming teardown, the main agent checks for orphan processes (via supervisor `GET /procs` or `pgrep`) and stops any proc whose start time matches the run. It returns ONLY overall pass/fail + per failing spec its name and first error line - no logs dumped into the main agent's context. Parallel self-starting e2e subs rely on dynamic-port allocation to avoid port collisions.

## Per-project specifics

Each importing project's CLAUDE.md fills these in (a snippet can't carry project-specific commands):

- Affected-spec command: `<e2e cmd> --only-changed`
- Full-suite command: `<e2e cmd>`
- Dev server start command + configured port: `<dev cmd>` on port `<port>`
- Source glob that triggers e2e (default `src/**`)
