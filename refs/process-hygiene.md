# Process Hygiene Reference

Detailed orphan-process defense and concurrency rules. CLAUDE.md has the short rules; this file has the full doctrine.

## Why this matters

Joe found 90+ orphan vitest processes from one session at 100% CPU and 90°C. The orphan issue, not concurrency itself, was what burned the CPU.

## Three-layer orphan defense

### Layer 1: subagent prompts that run tests/builds

Mandatory final step in the prompt:

> Run the project's orphan-check script (e.g. `pnpm check-orphans` if it exists, otherwise `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }`). If orphans remain, kill them with `Stop-Process -Id <PID> -Force` before reporting DONE.

### Layer 2: main-agent rule

After every subagent that ran Node commands completes, the main agent runs the same orphan check itself. If orphans are found, dispatch a one-shot cleanup subagent or kill them inline.

### Layer 3: optional Stop hook (recommended)

Configure a Claude Code Stop hook that runs the project's orphan-killer when the session ends. Acts as the last safety net.

## Orphan-check commands

**PowerShell (Windows):**
```powershell
Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' }
```

**Unix:**
```bash
pgrep node
```

**Kill orphans (Windows):**
```powershell
Stop-Process -Id <PID> -Force
```

## Concurrency cap (5)

Never run more than 5 Node-based commands concurrently:

- **turbo:** `--concurrency=5`
- **vitest:** `poolOptions.threads.maxThreads: 5` (or `pool: 'forks'` with `singleFork: true` for clean Windows exit)
- **pnpm:** `--workspace-concurrency=5`
- **Never** run `pnpm dev --parallel` outside of explicit dress-rehearsal use

Joe's hardware can handle 5 fine.

## Long-running dev servers

**Always launch them via the `/supervised-run` skill** (vite, `cargo tauri dev`, `next dev`, `flutter run`, backends, file watchers, etc.). The supervisor owns the process so there are no orphans, logs it centrally so the agent can read its output without a human pasting a terminal, and can spawn outside the agent's sandbox job (on Windows, a bare agent-shell launch is denied `CREATE_BREAKAWAY_FROM_JOB`, which is the real reason a long-lived server won't start under the agent directly). The skill falls back to a plain shell run only if the supervisor is unreachable.

If you ever bypass the supervisor: track the PID and ensure it terminates on session end / Ctrl-C / completion of the parent task.

## Stopping what you started, and closing when done

Joe's standing rule (2026-10-06), to save RAM and CPU on this PC. An idle chat still holds a
`claude` process of 200-330MB, and one idle local API plus its Docker containers measured ~430MB
after 9 hours with zero connections.

- **Servers.** Stop every dev server, watcher, emulator, Docker or Gradle stack this chat started
  as soon as the task no longer needs it, not at session end. A shared one this chat did NOT start
  is stopped only after `list_peers` shows no live chat using it, the same check `/supervised-run`'s
  Stop bullet already requires. A Gradle daemon a busy peer owns stays up: killing it fails that
  peer's next build.
- **The chat itself.** When the task is fully done (verified, committed, nothing left for Joe to
  answer), run `/close` without being asked. Exceptions: a turn that ends on a question card for
  Joe never self-closes, since the answer has nowhere to land; a long run (`/loop-todos`,
  `/autopilot`, `/auto-do-todos`) closes only after its final report, never between cycles; and a
  chat Joe is actively talking to stays open until the conversation is clearly finished.

## Secrets on the command line

A secret passed as a `--dart-define` or an env-prefix argument sits in that process's command line
for its whole lifetime, readable by anything that can enumerate processes. Prefer a file or a real
environment variable instead (2026-08-14, `revaire-mobile`: a live API key sat exposed this way in
an orphaned `flutter run`).

## Red-checking a new test (prove it fails against pre-fix code)

Never `git stash` a fix to prove its test is non-vacuous, a shared checkout may hold a peer
session's own uncommitted work in the same tree. Use `skills/close/red-check.ps1 -FixPaths
<paths> -TestCommand "<cmd>"` instead: it checks out HEAD into a detached worktree (the same
trick `/commit` step 6 uses for its baseline comparison), overlays every other dirty file
(the new test included) on top, and runs the test there. The live tree is only ever read.

## A red test run in a shared checkout needs two mechanical checks first

Two roles, same incident class: READING a contended result, and CAUSING one.

**Reading.** 2026-09-23/24, `zng-app` session `7c08e909`: a `fvm flutter test` run reported 2
failures and was relayed to the dev as the real state of the tree, attributed to a peer's
in-flight work (correctly - the files were dirty). The attribution was right and the verdict was
wrong: a peer had a hung `fvm flutter test` process running ~20 minutes against those exact
files, the run sampled a file mid-edit, and a re-run gave `All tests passed!`. The rule "retry a
red run before reporting it" already existed in memory and still did not fire, because it has to
be remembered mid-flow - the same failure shape as a rule that gets skipped under load. Make it
mechanical instead of remembered:

- `git status --short <path of each failing test file and its source>` - any dirt means the run
  may have read a file mid-edit.
- A live-test-process probe (`Get-CimInstance Win32_Process` filtered to the runner on Windows,
  `pgrep` on Unix) - a concurrent run means the result is contended.
- If either fires: re-run before reporting anything, and say the first run was discarded and why.

**Causing.** 2026-09-26, `cueline` session `4252077a`: a peer announced a full `vitest run` and
asked this session to hold. The session held the RUNNER (started nothing of its own, said so on
the channel) and then edited a store file and its test file while the peer's suite was mid
collection. No phantom failure resulted, but only because the run had already passed that file
before the edit landed - ordering luck, not safety. The peer's own framing: holding the runner does
not help if the tree moves, because the suite reads each file when it reaches it, so a run that
starts before your write and finishes after it tests a mixture of both versions. "I am holding off
running tests" reads as sufficient cooperation and is not - before editing a file, check for a live
runner in this checkout too, with the same probe above.

**Scope.** Both checks are overhead that cannot fire in a solo repo, so gate them on the same
signal `/commit` already uses: more than one live marker in `hooks/.session-markers/`, or a
non-empty `list_peers`. Do not widen this into a general flaky-test policy - the claim is narrow
and evidenced: concurrent edits and runs in the same checkout produce phantom failures, nothing
broader.

**Rejected:** a `PostToolUse` hook on test-runner output. It would have to parse arbitrary runner
output to know a run was red, and the two checks above are cheaper and already mechanical without
one.

## Challenge an instruction that reverses a ticketed decision

Trigger, narrowly: Joe gives an instruction that changes behaviour in a file whose current shape
came from a ticket Claude can name (discoverable via `git log -S <the behaviour>` plus the
commit subject's ticket id, which this repo's commit convention guarantees). On that trigger,
quote the ticket line the instruction would undo and confirm before making the change, rather
than obeying and silently dropping the requirement. Not "check every instruction" - that is too
broad to survive; the trigger is a traceable file-to-ticket link, not a vibe.

Worked example, sc-55729 (desktop share sheet): the ticket's ISSUE 2 asked that the "Link copied"
confirmation stay visible, because a desktop user about to switch tabs might miss it. A first fix
(`92688f9`) answered that by not auto-closing the sheet. Joe later told a different session "don't
keep the confirmation up" - a perfectly reasonable instruction on its face, with nothing in it
signalling a ticket requirement was attached. That session complied (`bea5f50`): a two-second
timer now reverts the copy label, so the confirmation itself disappears two seconds after the
copy - the opposite direction from the ticket's unwithdrawn complaint. Joe caught it only
afterwards: "oh i didnt realise he asked that the copied confirmation must stay visible, i told
another ai not to do that, whoops." By then the commit was pushed. Joe's own words on why this
needs to be a standing rule, not a one-off correction: "we should honestly add a rule that
whenever i tell you to do smth, check if there was a good reason why you did it (like the ticket
says to do it this way) and then ask me if im sure i wanna ignore the ticket" (2026-09-23). The
loss was silent: no test failed, no reviewer objected, and the ticket looked satisfied because the
visible half of the ask (which buttons show) was done correctly - the requirement lived one level
down, in the ticket body, not in the code, the commit message, or the conversation handed to the
session that complied.

Response shape: a question card quoting the ticket line, not a refusal and not a warning printed
before proceeding anyway. This does not license re-litigating ordinary instructions or overriding
a standing approval the dev already gave - it fires only on the narrow trigger above, once, and
proceeds on Joe's answer.

## Subagent commit handoff (READY_TO_COMMIT marker)

Subagents cannot invoke skills, so they must NEVER commit (the global rule covers the verbatim "stage only" dispatch sentence). For **background** subagents specifically: have them write a short `READY_TO_COMMIT.md` marker (or similar report-back doc) listing what they staged, so when the completion notification arrives the main agent knows there is staged work waiting and can run `/commit` against it.
