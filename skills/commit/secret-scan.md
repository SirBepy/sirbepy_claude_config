# Secret-scan check

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2).
Read on demand, not part of either skill's always-loaded body.

**Unlike comment-noise and em-dash, a hit here is NOT auto-fixed.** A secret
needs a human decision: is the value real, has it already leaked elsewhere,
does it need rotating. On a hit, STOP the commit and surface the flagged
`file:line`. The dev or agent must remove the literal value, source it from
an env var or secret store instead, then re-run the scan before committing.

What it flags: an added line matching a credential-shaped keyword
(`password`, `passwd`, `secret`, `token`, `api[_-]?key`, `bearer`, case
insensitive) followed by `=`/`:` and a quoted literal at least 6 characters
long. Obvious placeholders (`xxx`, `changeme`, `your-...-here`,
`placeholder`, `dummy`, `<...>`, etc.) and bare env-var reads
(`process.env.X`, `import.meta.env.X` have no quotes, so they never match
the pattern at all) are excluded. Whole-file exclusions: `.env.example` and
any `*.md`.

1. **Mechanical prefilter**, `skills/commit/secret-scan.sh`, same two-mode
   shape as `em-dash.sh`:

   - **Working-tree mode** (`/commit` step 5a): `git diff HEAD` plus every
     untracked file in scope, same untracked-file fold as the other two
     prefilters:
     ```
     bash skills/commit/secret-scan.sh <file> <file> ...
     ```
   - **Range mode** (`/create-pr` drafting subagent, branch vs base):
     ```
     bash skills/commit/secret-scan.sh --range <base>
     ```

   No output = clean. Any output = a real hit, stop and fix it now; there is
   no judge-the-flagged-files step like comment-noise has, because the fix
   is not a style call.
2. Tightness is a deliberate trade-off: it only catches a quoted-literal
   assignment, not an unquoted YAML value or a bare high-entropy string. That
   keeps false positives near zero (0/30 on this repo's own commit history)
   at the cost of not being a full secret scanner - it is a last-line net for
   the exact shape of the 2026-08-12 incident (a hardcoded credential
   literal), not a replacement for not putting secrets in code in the first
   place.
