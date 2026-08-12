<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=99295939 -->
# Make the generate skill read Windows user env vars itself

**Type:** skill-improvement

## Goal

Every single invocation of the `generate` skill on Windows needed a hand-written PowerShell prefix to
re-hydrate API keys from the registry. Push that into the script so callers can just run it.

## Context

Skill file: `~/.claude/skills/generate/SKILL.md`; script: `~/.claude/skills/generate/generate.mjs`
(added 2026-08-07, commits `cfffaea` and `3fdf070` in the `C:\Users\tecno\.claude` repo).

`setx` writes an env var to the registry, but Claude's tool calls inherit their environment from the
already-running Claude process, snapshotted at launch. So after Joe set `GEMINI_API_KEY`,
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, `$env:` still saw nothing for the whole session.

The workaround, retyped roughly eight times during todo 533:

```powershell
foreach ($n in @("CLOUDFLARE_API_TOKEN","CLOUDFLARE_ACCOUNT_ID")) {
  Set-Item -Path "env:$n" -Value ([Environment]::GetEnvironmentVariable($n,"User"))
}
node "$env:USERPROFILE\.claude\skills\generate\generate.mjs" ...
```

Forgetting it is not a loud failure - it silently degrades. One run fell through to Pollinations and
produced `sana` mush because only `GEMINI_API_KEY` had been re-hydrated and Cloudflare looked
unconfigured. That is exactly the failure mode the cascade's fallback is designed to hide.

See the `feedback_powershell_for_windows_flags` memory for the general form of this trap.

## Approach

In `generate.mjs`, when a needed key is missing from `process.env` and `process.platform === "win32"`,
read it from the user registry hive before giving up. Options, in preference order:

1. Shell out once to `powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('NAME','User')"`
   via `child_process.execFileSync`, lazily and only for keys that are actually absent. Simple, no
   dependency, costs one process spawn per missing key.
2. Read `HKCU\Environment` via `reg query`. Avoids PowerShell startup cost but needs output parsing.

Wrap it in a small `resolveKey(name)` helper used everywhere `process.env.X` is read for credentials
(`GEMINI_API_KEY`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `POLLINATIONS_API_KEY`). Keep
`process.env` as the first source so Linux/macOS and explicitly-exported values are unaffected.

Then delete the re-hydration prefix from SKILL.md's example command so the documented invocation is
the one that actually works.

## Acceptance

- `node generate.mjs --list-models` works in a fresh tool call with no PowerShell prefix, in a session
  started before the env vars were set.
- Provider selection is not silently degraded by a missing key that exists in the registry - the
  cascade only falls through when a key is genuinely absent everywhere.
- Non-Windows platforms take no extra process spawns.

## Notes


- Relocated from the claude_usage_in_taskbar backlog (was todo #536) on 2026-08-12: the fix targets the global ~/.claude tree, which a project session must not edit.
Related hardening worth considering in the same pass: the cascade currently reports a fall-through
only in stderr text. Since a silent drop to Pollinations/`sana` is the difference between a usable
image and mush, consider making an unexpected fall-through non-zero-exit or clearly flagged in the
returned JSON.
- completed, commit 5c702a7
