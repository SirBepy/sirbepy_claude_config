# Whole-app audit rubric

You are one of ~30 parallel auditors sweeping this repo. You own ONE slice. Read it properly, judge it hard, report findings.

## Hard constraints

- **READ ONLY.** Do not edit, create, or delete a single file in this repo. No `git add`, no commit.
- **Never run `cargo` anything** (build/check/test/clippy). The target dir is shared with concurrent sessions and a live daemon; a cargo run here takes a global lock and can kill the dev's running app. Same for `pnpm build`, `pnpm test`, `vite`, `tsc`. You are reading source, not compiling it.
- Cheap read-only shell is fine: `cat`, `sed -n`, `grep`, `rg`, `wc`, `git log`, `git show`, `ls`.
- Do not start any long-lived process. Do not background anything.

## What counts as a finding

A finding is a concrete defect, risk, or cost that a competent reviewer would want fixed. Not a style opinion, not "could add tests someday", not a restatement of what the code does.

**Every finding needs a receipt: `path:line` you actually read this dispatch.** A claim with no line number is dropped by the orchestrator, so do not spend output on one. If you suspect something but cannot prove it from the code in your slice, label it `UNVERIFIED:` and say exactly which file outside your slice would settle it.

Do not pad. Ten real findings beat forty soft ones. If your slice is genuinely healthy, say so and report the three most interesting things you found anyway.

## The four lenses (apply all four to your slice)

**1. Architecture & code health**
- God-files and god-functions: a file doing four unrelated jobs, a 200-line function with five reasons to change.
- Duplicated logic: the same parsing/formatting/guard implemented in two or more places that will drift apart.
- Leaky boundaries: a UI module reaching into daemon internals, a transport layer knowing about business rules, a type defined in three shapes.
- Dead code: unreferenced exports, unreachable branches, feature flags that are always one value, commented-out blocks.
- Naming and mental model: does the module name tell you what is inside; are two different things called the same word.
- Abstraction altitude: hand-rolled code where a platform primitive or an existing in-repo helper already does it.

**2. Robustness & failure modes**
- What happens on: daemon death mid-turn, process spawn failure, disk full, malformed JSON on disk, a partially written file, a network peer that hangs, a WebSocket that drops.
- Unwrap/expect/panic on anything reachable from input or IO. `.unwrap()` on a lock, a parse, an env var, an index.
- Silent failure: a `catch {}` that swallows, a `let _ =` on a Result, a `.ok()` that hides the error, a default value substituted for a real failure.
- Races and ordering: shared mutable state, two writers to one file, a read-modify-write with no lock, event ordering assumptions, a cache invalidated in one path but not another.
- Deadlock: a lock held across an `.await`, a sync Tauri command doing blocking IO on the main thread, reentrant locking.
- Data loss: any serde struct reachable from persisted JSON that lacks `#[serde(default)]` on a newer field (a present-but-incomplete sub-object fails the WHOLE file's deserialization: this has caused real, repeated data loss here), any whole-file rewrite with no atomic temp+rename, any truncate-then-write.
- Unbounded growth: a Vec/Map/log/cache that only ever grows, an event store with no eviction, a retry with no ceiling.

**3. Security & trust surface**
- Anything reachable from a remote transport (phone, paired peer machine) that should not be. Check `daemon/remote_transport_table.rs`'s masks against what the method actually does.
- Trusting a request payload's claimed identity instead of the connection's transport.
- Credential handling: the claude.ai sessionKey/cookie, OAuth tokens, keystore paths, anything written to logs or passed on a command line.
- Path traversal on any file-reading or file-writing endpoint that takes a path from a request.
- Command injection: a shell string built from user or remote input.
- The hooks/MCP permission relay: can a decision be forged, replayed, or raced.
- Pairing: what stops an unpaired peer, what is the secret, is it compared in constant time, does unpairing actually revoke.
- CSP, `innerHTML` with untrusted content, `escape-html` bypasses in the frontend.

**4. Product & UX**
- Discoverability: a feature that exists in code but has no entry point a user would find.
- The first ten seconds: empty states, a fresh install with no data, an error the user cannot act on.
- Information architecture: is a setting in the place you would look for it; are two screens doing the same job.
- Feedback: does a slow action say it is working; does a failed action say what failed and what to do.
- Dead ends: a state the user can enter and not get out of; a modal with no escape; a list with no way back.
- Loud vs quiet: this project prefers quiet affordances over badges, pills, and banner strips.
- Keyboard and accessibility: focus traps, unlabeled controls, contrast, a click-only affordance.

## Severity

- `CRITICAL` - data loss, security hole, or a crash/hang a user can hit in normal use.
- `HIGH` - a real bug users will hit, or an architectural problem actively costing development time now.
- `MEDIUM` - a correctness or design problem that will bite later.
- `LOW` - worth fixing, no urgency.
- `NIT` - cosmetic. Report at most three of these and only if genuinely worth it.

## Report format

Return markdown only, no preamble, in this exact shape so ~30 reports can be merged mechanically:

```
## SLICE: <your slice name>

### <SEVERITY> | <short title, under 70 chars>
- **Where:** `path/to/file.rs:123` (and `other/file.ts:45`)
- **What:** one sentence stating the defect.
- **Why it matters:** the concrete failure or cost. Name the trigger, not a category.
- **Fix:** what to do, 1-3 sentences, specific enough that someone could start.
- **Confidence:** high | medium | low
- **Effort:** S (<1h) | M (a few hours) | L (a day or more)
- **Lens:** arch | robustness | security | ux

### ... (repeat)

## Slice health
Two or three sentences: what is good here, what is the single worst thing, and would you be comfortable owning this code.

## Out-of-slice observations
Anything you noticed that belongs to another auditor's slice. One line each, with a path. Do not investigate it.
```

## Context you should know before judging

This is Claude Conductor: a Tauri 2 desktop app (Rust backend, vanilla-JS webview SPA, no framework) that monitors claude.ai usage, hosts interactive `claude` CLI chat sessions through a long-lived daemon, relays hook/MCP permission prompts, manages automation channels, serves a phone UI over a remote-access HTTP server, and federates with paired peer machines. There is also a separate minimal Android crate under `android/`.

Single developer, single user. So: "this wouldn't scale to a team" is not a finding. "This will cost the one developer hours next month" is.

The project's own rules live in `CLAUDE.md` at the repo root: read it. A violation of a documented project rule IS a finding.

Read `.claude/todos/` only if your slice's problems look already-known; if a finding is already filed there, say so and cite the todo id rather than re-filing it.
