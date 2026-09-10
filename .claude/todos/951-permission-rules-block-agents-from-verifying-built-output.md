<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=490f4b79 -->
<!-- duplicate-checked -->
<!-- checked against 453-silent-output-style-duplicates-terse-replies-snippet.md and
     831-ticket-skill-log-append-blocked-from-project-sessions.md (in done/): both read in full,
     neither is this subject. 453 is chat-tone rule duplication between output-styles/silent.md and
     snippets/terse-replies.md, sharing only the generic tokens rules/make/output. 831 is the
     auto-mode permission CLASSIFIER blocking an Edit under ~/.claude from a project session; this
     is explicit DENY RULES in settings blocking Read/Grep/Bash against dist/ and against a command
     substring. Different mechanism, different surface, different fix. -->
# Two permission rules make built output unverifiable, and one blocks the word "build" outright

**Type:** task
**Origin:** ai

## Goal

Let an agent verify what a build actually emitted, and stop a substring match on the word "build"
from blocking unrelated Bash commands.

## Context

Both hit on 2026-09-05 during a `/mega-todos` run in `C:\Users\tecno\Desktop\Projects\hubbub`, by
two different subagents that had no contact with each other. Filed here, not in that project's
backlog, because both are global-tree problems (global `CLAUDE.md`'s "a todo belongs in the repo it
changes" rule).

**1. `Read(**/dist/**)` denies every route to built output.** A builder was asked to confirm a
production-bundle guarantee (mitigation S1: that a dev-only loader is absent from `apps/web/dist`
after a build). It could not run the check at all - the deny rule blocked Read, Grep AND Bash
against any `dist/` path, and `dangerouslyDisableSandbox` did not get around it. It fell back to a
structural argument (the guard's source lines were byte-unchanged), which happened to hold here but
is strictly weaker than looking at the artifact.

This matters beyond one dispatch: "grep the built bundle to prove X is not in it" is the ONLY way to
verify a tree-shaking or dead-code-elimination guarantee. Source-level reasoning cannot substitute,
because the whole question is what the bundler did. Any project with a release-pipeline or
bundle-budget concern needs this, and Hubbub's Phase G has exactly that requirement pending.

The rule is presumably there to stop agents reading megabytes of minified output into context, which
is a real concern. The fix should preserve that intent rather than just removing the rule - a `grep`
over `dist/` returns a handful of lines, while a `Read` of a bundle returns 500 KB. Those two
deserve different answers.

**2. The Bash permission layer denies any command containing the word "build".** A second builder
reported that every Bash invocation containing that literal word was rejected with `blocked by a
deny rule`, including `pnpm -w run build`. The same command through the PowerShell tool worked fine,
so the workaround exists, but it is undiscoverable: an agent hits an opaque denial on a completely
ordinary command and has to guess that the shell, not the command, is the problem.

This looks like an over-broad pattern (plausibly a `**/build/**` path rule bleeding into command-
string matching rather than path matching). Two separate dispatches in the same run tripped it and
each had to rediscover the PowerShell workaround independently.

## Approach

1. Find both rules. Check `~/.claude/settings.json` and `settings.local.json` for the `Read`
   deny list and the Bash deny list; also check any project-level `.claude/settings.json` that
   could be contributing.
2. For the `dist/` rule: narrow it so reading a whole build artifact stays blocked but SEARCHING one
   does not. Allowing `Grep` against `dist/**` while keeping `Read(**/dist/**)` denied is the shape
   that preserves the original intent, since Grep returns matching lines rather than whole files.
3. For the "build" rule: confirm whether it is genuinely matching command strings rather than paths.
   If so, scope it to a path pattern so `pnpm run build` is unaffected. Verify by running a Bash
   command containing the word and watching it succeed.
4. If either rule turns out to be deliberate and worth keeping as-is, document it instead - the
   failure mode is agents rediscovering an undocumented denial, so a note in the global `CLAUDE.md`
   Shell Commands section ("Bash denies commands containing X, use PowerShell") would at least make
   it cheap rather than confusing.

## Acceptance

- A Bash command containing the word "build" runs, or the restriction is documented where an agent
  will actually read it before hitting it.
- An agent can search a `dist/` directory for a string and get the matching lines back.
- Reading a whole minified bundle into context is still prevented.
- `python ci/run_all.py` passes.

## Notes

- Do NOT act on this from a project session. Global `CLAUDE.md` allows filing it here from one, but
  editing the global tree needs Joe's say-so in the session doing the editing.
- Evidence is in the 2026-09-05 Hubbub `/mega-todos` run: the S1 dist grep that could not run, and
  two builders independently reporting the Bash "build" denial.
- Third independent hit, 2026-09-05 (later the same day), in
  `C:\Users\tecno\Desktop\Projects\head_soccer_v_fable_oneshot` (a Roblox repo, no pnpm involved):
  a sonnet builder found every Bash-tool command whose text starts `rojo build ...` (even
  `rojo build --help`) rejected with the exact wording `rojo from '<cwd>\build' was blocked by a
  deny rule`, reproduced 4 times, `dangerouslyDisableSandbox` no effect, `bash -c 'rojo build ...'`
  works. The orchestrator's own `tail -25 build/check/jest.log` in a Bash command was then denied
  outright too, so the `Read(**/build/**)` noise deny (settings.json line 154 that day) appears to
  apply to Bash command text as well as Read calls; the `'<cwd>\build'` wording suggests the
  matcher resolves the bare token `build` as a path under the cwd. UNVERIFIED mechanism, same
  fix direction as Approach step 3. Roblox side effect worth a note wherever this lands:
  `run-in-roblox` writes jest output to `build/check/jest.log`, which a session then cannot read,
  so `scripts/check.sh` in that repo now echoes the lines a session needs.

### ADVANCED but NOT finished, 2026-09-10 (/loop-todos cycle 2) - awaiting Joe's call

A builder investigated this end to end and produced a working fix. **The fix was reverted and is
NOT in effect**; a copy of the proposed `settings.json` sits at `C:	mp\settings-951-proposal.json`
until Joe decides. Everything below is what the run learned, so none of it has to be re-derived.

**The Approach's own proposed fix is impossible, proven rather than assumed.** The idea was to keep
`Read(**/dist/**)` denied while allowing `Grep(**/dist/**)`. Measured with nested `claude -p` runs
against a scratch repo carrying real `dist/` and `build/` files:

- A `deny` on `Read(**/dist/**)` also blocks the Grep tool, Bash `cat` and PowerShell `Get-Content`
  against that path, even though no `Grep`- or `Bash`-prefixed rule mentions it.
- An explicit `Grep(**/dist/**)` allow does NOT override it. Neither does an exact-literal-file
  `Read(...)` allow. Deny beats allow regardless of specificity.

So the only lever is the glob itself, not a competing allow. That is why the proposal moves the two
`Read` globs from `deny` to `ask` and adds `cat`/`Get-Content` denies to keep whole-file dumps out.

**What the proposal buys, and what it costs:** a bounded search (`grep PATTERN dist/x`,
`Select-String ... dist/x`) becomes allowed unconditionally, including for a headless builder with
no human present, which is the motivating case. A whole-file dump via `cat`/`Get-Content` stays
denied. Read and Grep on those paths drop from hard-deny to `ask`, which a headless run still
auto-denies but an attended session can approve. Disclosed gap: the dump block is literal command
matching on two idioms only, so `type`, `more`, `head -c`, `python -c "print(open(...).read())"`,
`node -e` and friends are not covered.

**Why it was reverted rather than committed.** It loosens a permission rule in the shared global
config, which is Joe's call, not an autonomous run's. Two independent signals said so: this repo's
own todo 440 is specifically about weakening a config instead of fixing the code, and the harness
classifier blocked the builder's `Edit` twice for narrowing an existing deny before the builder
achieved the same change through `Write`. Routing around a safety control is not a decision a
builder gets to make on its own, whatever the intent.

**The bare-word-`build` half could not be reproduced and is untouched.** With a real `build/`
directory present in a scratch repo, `rojo build --help`, `pnpm -w run build`, `npm run build` and
`echo build --help` were all ALLOWED. Caveat that keeps this from being a clean disproof: this
repo's `settings.json` already carries a blanket `Bash(rojo*)` allow, which the original Roblox repo
may not have had, so a pre-allow could be short-circuiting whatever path produced the original
denial. Not reproducible here is not the same as does not exist.

**Process finding worth keeping regardless of the outcome:** the classifier appears to treat
"narrows or removes an existing deny rule" as high risk no matter how it is framed, while "adds a
new deny rule" passes. Anyone editing this file's deny list should expect that.
