<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=4, reconfirm-count=1, content-hash=bf69839b -->
<!-- duplicate-checked -->
# Every guard is app-layer, so a buggy hook is a bypassed hook

**Type:** task
**Origin:** ai

## Goal

Evaluate the native `sandbox.*` settings namespace, so file and network limits are enforced by the OS
rather than only by regex hooks that fail open when their pattern misses.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

All 41 hooks are app-layer pattern matchers. Each one fails open: a path or command it does not match
proceeds normally. That is the correct design for advisory guards, but it means there is no layer
underneath them. A guard with a gap in its regex is a guard with a hole, and nothing catches what falls
through.

Reference: `repos/shanraisshan_claude-code-best-practice/best-practice/claude-settings.md:466-525`
documents a native `sandbox.*` namespace:

- `filesystem.allowWrite` / `denyWrite` / `denyRead`
- `network.allowedDomains` / `deniedDomains` / `strictAllowlist`
- `credentials.files[].mode: "mask"` to strip or mask secrets from a sandboxed subprocess's environment

This is the setting behind the `dangerouslyDisableSandbox` parameter that already appears on the Bash
and PowerShell tools in this environment, which means **sandboxing is already active in some form
here** and the config surface for tuning it is simply unused. Establishing what the current effective
sandbox actually is, is therefore the first job, not the last.

`repos/TheoBrigitte_claude-config/bin/claude-sandbox.sh` shows the heavier version of the same idea:
a bubblewrap user-namespace container with read-only binds for system paths, a mutable bind only for
`~/.claude`, `.claude.json`, `.gnupg` and `$PWD`, an unshared PID namespace, and process death tied to
the parent. Linux-only, so not portable here, but the allowlist-bind model is the concept: name what
is writable instead of enumerating what is not.

Why this pairs with existing work rather than replacing it:

- Todo 420 adds a write-time secret scanner. `credentials.files[].mode: "mask"` addresses the same
  risk from underneath, by removing secrets from the subprocess environment entirely.
- Todo 419 adds a destructive-command blocker. `filesystem.denyWrite` makes the worst outcomes
  impossible rather than merely blocked.
- `network.allowedDomains` is the one with no app-layer equivalent at all. Nothing here currently
  constrains where a subprocess can connect.

Real risk to respect: an over-tight sandbox breaks working tooling in ways that are hard to diagnose,
because the failure is a permission error from a subprocess rather than a guard message. This repo runs
Flutter, Rust, Node, Playwright, adb and gh, all of which touch wide swathes of the filesystem and the
network. A `strictAllowlist` here would be a large blast radius.

## Approach

1. Establish the current state first. Determine what sandboxing is actually in effect today, given
   `dangerouslyDisableSandbox` exists as a tool parameter. Check `settings.json` and
   `settings.local.json` for any `sandbox` key, and check whether the harness applies a default. **Do
   not configure a sandbox before knowing what is already running.**
2. Verify the documented keys against this harness version. The reference is a third-party summary of
   docs, and settings keys move. Confirm each key is real before building a config around it.
3. Inventory what would break. List the tooling that legitimately needs broad filesystem and network
   access: package managers, Flutter and Dart, cargo, Playwright browser downloads, gh, adb, the MCP
   servers. This list is the constraint that decides whether anything here is adoptable.
4. Start with the narrowest useful setting rather than a full policy. `credentials.files[].mode:
   "mask"` is the best first candidate: it targets a specific risk, has a small blast radius, and
   complements todo 420 rather than duplicating it.
5. If filesystem or network rules are attempted, use deny-specific rather than strict-allowlist.
   `denyWrite` on a handful of genuinely dangerous paths is adoptable; `strictAllowlist` on a machine
   running four toolchains is not, and would be reverted within a day.
6. Test by attempting a real blocked operation and confirming a clear failure, then run a normal build
   and confirm it still works. Both halves.

## Acceptance

- A written statement of what sandboxing is in effect BEFORE any change.
- Each configured key verified to exist in this harness version, not taken from a third-party doc.
- A list of tooling that needs broad access, produced before any restriction is applied.
- Any adopted setting proven twice: a blocked operation fails clearly, and a normal build still
  passes with real output pasted.
- No `strictAllowlist` without an explicit, separately-argued case.

## Notes

The honest likely outcome is that only `credentials.files[].mode: "mask"` is worth adopting, and that
filesystem and network policy is not, given four toolchains on one machine. Reporting that is a
success, not a failure to deliver.

The point of this todo is a layer underneath the hooks, not a replacement for them. Do not weaken any
existing guard on the theory that the sandbox now covers it.
