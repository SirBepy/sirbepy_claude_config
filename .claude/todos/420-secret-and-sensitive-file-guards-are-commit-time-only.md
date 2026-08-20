<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Secret scanning happens at commit time only, and no guard protects sensitive files from edits

**Type:** task
**Origin:** ai

## Goal

Catch a secret at the moment it is written rather than at commit time, and stop accidental edits to
credential files, lockfiles, and the hook scripts themselves.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current state: `skills/commit/secret-scan.sh` runs as a commit prefilter, and the delegation doctrine
requires every builder dispatch to run it against its own diff. That is a good last line, but it is
the LAST line. A secret written to a file and never committed (a scratch config, a test fixture, a
file the dev opens later) is never scanned. And nothing prevents an edit to `.env`, a private key, or
a hook script.

Three reference implementations, all in `poshan0126/dotclaude/hooks/`:

**`scan-secrets.sh`** - PreToolUse on Edit and Write. Regexes the Write `content` and the Edit
`new_string` for AWS keys, GitHub and Slack tokens, `sk-...` keys, PEM blocks, credentialed
connection strings, and generic `password=`/`secret=` literals, while **excluding `process.env` and
`os.environ` references** so config plumbing does not trip it. Emits `ask`, not `deny`, so it stays
overridable.

**`protect-files.sh`** - PreToolUse Edit/Write deny on `.env*`, `*.pem`, `*.key`, `*.crt`, `*.p12`,
`*.pfx`, `id_rsa`, `credentials.json`, lockfiles, `*.gen.ts`, `*.min.js`, `.git/`, `secrets/`. The
part worth stealing outright: **it self-protects, denying edits to `.claude/hooks/*` and asking on
`settings.json`.** Nothing here stops an agent from editing the guard that constrains it.

**`IvanKuzyshyn/dotfiles` gitleaks via `core.hooksPath`** - a real git hook running
`gitleaks protect --staged --redact`. Different layer entirely: it catches secrets that never pass
through Claude at all, including manually-staged files and edits made outside any Claude session.

Two existing pieces to reconcile with, not duplicate: `hooks/shell-content-write-guard.py` already
blocks shell-based file writes (which is why `Set-Content` is banned), and `.gitignore` already has
belt-and-suspenders `.env` exclusions.

## Approach

1. Read the three reference scripts. Note that `scan-secrets.sh` uses `ask` rather than `deny` on
   purpose; match that, since a false positive that hard-blocks a legitimate write is worse than a
   prompt.
2. Build the write-time secret scanner as a PreToolUse hook on Write and Edit. Reuse the regex set
   from `skills/commit/secret-scan.sh` rather than authoring a second, divergent pattern list. **If
   the patterns live in two places they will drift**; extract them to one shared source if the shapes
   allow it, and say so in the commit message if they do not.
3. Build the sensitive-file guard. Start from `protect-files.sh`'s list, then add the self-protection
   case, which is the highest-value part: deny edits to `hooks/*` and ask on `settings.json` and
   `settings.local.json`. Check first whether this collides with legitimate workflows, since hooks
   here ARE edited regularly by the dev, so this probably needs to be `ask`, not `deny`.
4. Evaluate gitleaks separately and honestly. It is a third-party binary, so it goes through the
   package-safety check in CLAUDE.md first. Its value is covering non-Claude edits, which no
   Claude-side hook can ever reach. If adopted, wire via `core.hooksPath` so it is not per-repo.
5. Fixture tests for both hooks, following the existing `hooks/test_*.py` convention. Negative cases
   matter most here: `process.env.API_KEY` must NOT trip the scanner.

## Acceptance

- Writing a fake AWS key to a scratch file triggers the scanner; writing `process.env.AWS_KEY` does
  not.
- Attempting to edit a `.pem` or `.env` file is caught.
- Attempting to edit a file under `hooks/` prompts rather than silently succeeding.
- Regex patterns exist in ONE place, or the reason they cannot is written down.
- Real test output pasted, not claimed.

## Notes

Do not make the secret scanner `deny`. Every false positive on a `deny` guard costs a workaround,
and workarounds outlive the guard.

The self-protection case is the one genuinely novel idea here and the easiest to skip because it
feels paranoid. It is not: an agent that can edit its own guards has no guards.
