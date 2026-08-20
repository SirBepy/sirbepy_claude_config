<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The statusline runs npx on every launch, so it needs the network to start

**Type:** task
**Origin:** ai

## Goal

Replace the per-launch `npx` fetch with a local script or binary, so the statusline works offline and
does not add network latency to every session start.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current `statusLine` config invokes `npx -y ccstatusline@latest`. Three costs, in order of how much
they actually matter:

1. **A network dependency on session start.** Offline or on a bad connection, the statusline either
   stalls or falls back. `npx` does cache, so this is not a fetch every single time, but `@latest`
   forces a registry version check.
2. **`@latest` means the statusline can change without any action here.** An upstream release alters
   the display, or breaks it, with no pin and no diff to review. That sits oddly next to the package
   safety rules in CLAUDE.md, which require a pinned version past any known fix for anything added
   deliberately.
3. Startup latency on every launch, small but paid constantly.

Two reference implementations:

- **`repos/ZacheryGlass_.claude/statusline.go`** - 456 lines, cross-compiled to `.exe` and darwin
  binaries. Reads the same JSON-on-stdin schema, caches git info with a 600s TTL and per-session state
  under `~/.claude/.statusline_cache`, no network call at all.
- **`repos/davidbaines_claude_configs/configs/statusline-model-colours/`** - a plain local Python
  script colouring by model cost tier and context percentage. Much smaller, no build step.

The Python variant is the better fit here: Python is already a dependency (27 hooks are Python), it
needs no cross-compilation, and it is editable in place. A Go binary means a build step and a
committed binary, and the repo's gitignore allowlist would need an exception for it.

Related existing surface: `aiusage-hook.ps1` and `aiusage-hook.sh` already exist, and `/context-left`
already reports remaining context. Check what those do before writing anything, since the data the
statusline needs may already be computed somewhere.

## Approach

1. Capture the current behavior before replacing it, or the replacement has nothing to match. Run the
   existing statusline and record exactly what it displays, plus the JSON schema it receives on stdin
   (the harness docs describe it; confirm against a real invocation).
2. Read the Python reference for the colouring and context-percentage logic, and skim the Go one for
   its caching approach (the 600s git TTL is the useful idea, independent of language).
3. Check `aiusage-hook.*` and `/context-left` for reusable computation. Do not write a second
   context-percentage calculation next to an existing one.
4. Write a local Python statusline. Requirements: no network, cache git state with a TTL, and degrade
   gracefully rather than erroring if anything is unavailable, since a crashing statusline is worse
   than a plain one.
5. Point `settings.json` at it. Note that `settings.local.json` is currently untracked (todo 415), so
   confirm which file actually carries `statusLine` before editing.
6. Compare side by side against the recorded baseline before removing the npx config.

## Acceptance

- The statusline renders with the network disabled, verified by actually disabling it or blocking the
  registry, not by assuming.
- Output is equivalent to the recorded baseline, or the differences are deliberate and listed.
- No second context-percentage implementation is introduced.
- A deliberately broken input degrades to a plain statusline instead of erroring.
- `git status` shows the config change in the tracked settings file.

## Notes

Do not commit a compiled binary. The gitignore is allowlist-based and a binary in a config repo is a
supply-chain surface for no benefit at this size.

Keep it boring. A statusline that fails is a permanent visual annoyance, and this one runs on every
launch.
