# Whole-app audit rubric

You are one of ~N parallel auditors sweeping this repo. You own ONE slice. Read it properly, judge it hard, report findings.

## Hard constraints

- **READ ONLY.** Do not edit, create, or delete a single file in this repo. No `git add`, no commit.
- **Never run this project's build, test, or compile command** (e.g. `cargo build/check/test/clippy`, `pnpm build/test`, `vite`, `tsc`, `gradlew`, `go build`). In a repo with a shared build cache, a lockfile, or a live daemon/dev server, an auditor's build invocation can take a global lock or kill a running process that isn't yours to disturb. You are reading source, not compiling it. (A live Tauri/Rust example of exactly this failure mode: `cargo` takes the target dir's lock and can kill a long-lived daemon - see `lenses/tauri-rust.md`.)
- Cheap read-only shell is fine: `cat`, `sed -n`, `grep`, `rg`, `wc`, `git log`, `git show`, `ls`.
- Do not start any long-lived process. Do not background anything.

## What counts as a finding

A finding is a concrete defect, risk, or cost that a competent reviewer would want fixed. Not a style opinion, not "could add tests someday", not a restatement of what the code does.

**Every finding needs a receipt: `path:line` you actually read this dispatch.** A claim with no line number is dropped by the orchestrator, so do not spend output on one. If you suspect something but cannot prove it from the code in your slice, label it `UNVERIFIED:` and say exactly which file outside your slice would settle it.

Do not pad. Ten real findings beat forty soft ones. If your slice is genuinely healthy, say so and report the three most interesting things you found anyway.

## Prior-decision check (do this before reporting anything)

A repeat audit of the same repo will rediscover findings the dev already saw and declined. Before writing up a finding, grep `.claude/todos/done/` (if this project uses the ai-todos-format backlog) or whatever the project's closed-issue archive is, for the file path or the defect's subject. If a matching entry exists and was explicitly rejected or deliberately deferred, say so and cite it instead of re-filing it as new - "already considered, see todo NNN, dev declined because X" is worth one line, not a fresh finding. If the entry was accepted and fixed, and your slice still shows the defect, that IS a new finding - say the fix didn't land or regressed.

## The four lenses (apply all four to your slice)

Each lens below is the stack-neutral core. Phase 2 of the `/audit` skill appends a
matching lens pack from `lenses/` (e.g. `lenses/react-tanstack.md`,
`lenses/tauri-rust.md`) beneath each lens for stack-specific checks. If no pack
matches this project's stack, apply the generic checklist only and note in
"Slice health" what you couldn't check for lack of stack-specific guidance -
that gap is itself worth a line in the orchestrator's report, not something to
paper over by inventing stack knowledge you don't have.

**1. Architecture & code health**
- God-files and god-functions: a file doing four unrelated jobs, a 200-line function with five reasons to change. Flag size only when there's an actual seam to split along - name the seam (e.g. "lines 40-120 are pure parsing, 120-300 are I/O, split there"), never "this file is long" on its own.
- Duplicated logic: the same parsing/formatting/guard implemented in two or more places that will drift apart. Prove it with a grep (`grep -rn '<the distinctive fragment>'`), not an impression - cite both hit locations.
- Leaky boundaries: a UI module reaching into backend internals, a transport layer knowing about business rules, a type defined in three shapes.
- Dead code: unreferenced exports, unreachable branches, feature flags that are always one value, commented-out blocks. Back a dead-code claim with a usage-count grep (`grep -rn '<symbol>'` showing only the definition, zero call sites) - a miscounted grep is the most common false dead-code claim.
- Naming and mental model: does the module name tell you what is inside; are two different things called the same word.
- Abstraction altitude: hand-rolled code where a platform primitive or an existing in-repo helper already does it.
- Convention violations: a finding that the code breaks a documented project rule must quote the exact rule (from `CLAUDE.md`, a style guide, or an ADR) alongside the violating line - a convention finding with no quoted rule is an opinion, not a finding.

**2. Robustness & failure modes**
- What happens on: process death mid-operation, spawn failure, disk full, malformed data on disk, a partially written file, a network peer that hangs, a connection that drops.
- Unwrap/panic/unhandled-exception on anything reachable from input or IO - a parse, an env var, an index, a lock.
- Silent failure: a swallowed catch block, a discarded error result, a `.ok()`/`?:` that hides the error, a default value substituted for a real failure.
- Races and ordering: shared mutable state, two writers to one resource, a read-modify-write with no lock, event ordering assumptions, a cache invalidated in one path but not another.
- Deadlock: a lock held across an await/yield, blocking IO on a UI/main thread, reentrant locking.
- Data loss: a schema change that isn't backward-compatible with data already on disk, a whole-file rewrite with no atomic temp+rename, a truncate-then-write.
- Unbounded growth: a collection/log/cache that only ever grows, an event store with no eviction, a retry with no ceiling.

**3. Security & trust surface**
- Anything reachable from an untrusted or remote caller that should not be. Check the access-control surface against what the method actually does, not what its name implies.
- Trusting a request payload's claimed identity instead of the connection's own authenticated transport.
- Credential handling: tokens, cookies, keystore paths, anything written to logs or passed on a command line.
- Path traversal on any file-reading or file-writing endpoint that takes a path from a request.
- Command/query injection: a shell string or query built from user or remote input without escaping.
- A permission or approval relay: can a decision be forged, replayed, or raced.
- Pairing/handshake flows: what stops an unauthorized peer, what is the secret, is it compared in constant time, does revocation actually revoke.
- CSP, `innerHTML`/raw-HTML injection with untrusted content, output-escaping bypasses.

**4. Product & UX**
- Discoverability: a feature that exists in code but has no entry point a user would find.
- The first ten seconds: empty states, a fresh install with no data, an error the user cannot act on.
- Information architecture: is a setting in the place you would look for it; are two screens doing the same job.
- Feedback: does a slow action say it is working; does a failed action say what failed and what to do.
- Dead ends: a state the user can enter and not get out of; a modal with no escape; a list with no way back.
- Loud vs quiet: match the project's own stated affordance style if `CLAUDE.md` or a design doc names one; otherwise note the house style you observed and judge against it.
- Keyboard and accessibility: focus traps, unlabeled controls, contrast, a click-only affordance.

## Severity

- `CRITICAL` - data loss, security hole, or a crash/hang a user can hit in normal use.
- `HIGH` - a real bug users will hit, or an architectural problem actively costing development time now.
- `MEDIUM` - a correctness or design problem that will bite later.
- `LOW` - worth fixing, no urgency.
- `NIT` - cosmetic. Report at most three of these and only if genuinely worth it.

## Report format

Return markdown only, no preamble, in this exact shape so many reports can be merged mechanically:

```
## SLICE: <your slice name>

### <SEVERITY> | <short title, under 70 chars>
- **Where:** `path/to/file.ext:123` (and `other/file.ext:45`)
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

## Project-specific context (fill this in before dispatching - Phase 2)

Replace this whole section with a short, concrete description of the actual
project before copying this file into `.for_bepy/audit/RUBRIC.md` (or the
project's scratch equivalent):

- What the project is (one or two sentences): the stack, what it does, what runs where.
- Who uses it and how many: a single-developer tool calibrates severity differently than
  a multi-tenant product - "this wouldn't scale to a team" is not a finding for the former,
  it may be a HIGH for the latter. Say which this is.
- Where the project's own rules live (`CLAUDE.md`, a style guide, an ADR directory) - auditors
  must read it, and a violation of a documented project rule IS a finding.
- Which lens pack(s) from `lenses/` apply, if any. Note any genuinely project-specific
  checks that don't belong in a reusable pack (a single sensitive file, a known footgun)
  directly here instead of inventing a one-off pack for them.
- Whether `.claude/todos/` (or wherever this project's backlog lives) exists, so the
  prior-decision check above has somewhere to look.
