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
- Shipped 2026-08-21. Three new files plus one shared pattern source: hooks/secret-patterns.txt (single source, three tab-separated columns, read by BOTH the Python hook and secret-scan.sh's awk), hooks/secret-write-guard.py and hooks/sensitive-file-guard.py (PreToolUse on Write/Edit/MultiEdit/NotebookEdit), their two test suites, and an additive ask() helper in _hooklib.py. Both guards emit ask, never deny, per Joe's call: measured over 22,992 real Write/Edit calls from this machine's transcripts, a deny would have eaten 22 legitimate .env.local writes and 3 legitimate lockfile writes. Pattern-file constraint that matters for anyone editing it: two regex engines read it, so no POSIX bracket classes, no backslash-b/d/w/s, no lookaround, and every ERE is written lowercase because both readers lowercase the line first. FINAL measurement of the shipped set over 22,992 writes: the six prefixed shapes (AKIA, aws_secret, ghp_, sk-, xox, PEM) fired 0 times outside this phase's own fixtures; conn_string_creds fired once on a real credentialed E2E_DATABASE_URL, which is a correct catch; generic_assignment fired on 35 calls and the dump showed the large majority were GENUINE hardcoded credentials, real JWT access/refresh tokens and real passwords in scratch verification scripts across zng-app and fibo. So the rule was NOT tightened below the 5-hit target it was given: doing so would have deleted real detections. Roughly 4 hits were noise and 6 more were removed by adding an ISO-8601 branch to the allow row, since accessTokenExpiresAt timestamps are never credentials. Sensitive-file rules cost 311 prompts across all 22,992 historical writes (1.35 percent), of which 288 are the hooks/settings self-protection rule, the highest-frequency rule in the set and the one Joe explicitly wanted. secret-scan.sh before/after, proven on a planted probe: the OLD script reported 1 finding, the NEW script reported 5 (AKIA, generic, ghp_, xox, connection string) while correctly skipping the changeme placeholder, the process.env reference and the ISO timestamp; a clean tracked diff still returns empty with exit 0, so /commit behaviour is unchanged. Both guards proven LIVE by a nested claude -p that quoted their feedback verbatim. gitleaks was DECLINED on Joe's call: the Claude-side hook plus the commit prefilter cover every path Claude takes, and a global core.hooksPath would reach client repos, which the personal-tooling rule forbids. The ls-files --exclude-standard blind spot was deliberately NOT touched, it is todo 460's job, and it reproduced live during this work: a probe planted at the repo root returned empty with exit 0 from both the old and new scripts because the deny-all .gitignore hides it. The builder subagent died mid-dispatch on a session limit; the orchestrator finished the missing re-measurement, the before/after proof and the sk_key line-start fix inline.
