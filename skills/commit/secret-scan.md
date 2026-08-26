# Secret-scan check

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2).
Read on demand, not part of either skill's always-loaded body.

**Unlike comment-noise and em-dash, a hit here is NOT auto-fixed.** A secret
needs a human decision: is the value real, has it already leaked elsewhere,
does it need rotating. On a hit, STOP the commit and surface the flagged
`file:line`. The dev or agent must remove the literal value, source it from
an env var or secret store instead, then re-run the scan before committing.

What it flags, from `hooks/secret-patterns.txt` (todo 420's single source,
shared with the write-time `hooks/secret-write-guard.py` so the two lists
can never drift): AWS access keys, GitHub/Slack tokens, `sk-...` keys, PEM
private-key blocks, credentialed connection strings, and a generic
credential-shaped keyword (`password`, `passwd`, `secret`, `token`,
`api[_-]?key`, `bearer`, case insensitive) followed by `=`/`:` and a quoted
literal at least 6 characters, containing no whitespace, comma, or `)`.
Obvious placeholders (`xxx`, `changeme`, `your-...-here`, `placeholder`,
`dummy`, `<...>`, etc.) and bare env-var reads (`process.env.X`,
`import.meta.env.X` have no quotes, so they never match the generic rule at
all) are excluded from that generic rule only. Whole-file exclusions:
`.env.example` and any `*.md`.

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

   A named path invisible to git (gitignored, or missing entirely) still
   gets scanned: it produces no `git diff HEAD` and no `ls-files --others`
   entry, so without this it would silently pass as "clean" while never
   having been read (todo 460). It is scanned via `git diff --no-index`
   against `/dev/null`, the same call the untracked-file branch already
   uses, so a caller who explicitly names a gitignored path still gets it
   audited instead of a dead end.
2. Tightness is a deliberate trade-off: the generic rule only catches a
   quoted-literal assignment, not an unquoted YAML value or a bare
   high-entropy string. It is a last-line net for known credential shapes,
   not a replacement for not putting secrets in code in the first place.
   Measured against **22,992 real Write/Edit calls** from this machine's own
   transcripts (todo 420): the six prefixed shapes fired 0 times outside this
   phase's own fixtures, and the generic rule fired on 35 calls, of which the
   large majority were genuine hardcoded credentials (real JWTs and passwords
   in scratch verification scripts). Roughly 4 were noise, and 6 more were
   removed by adding an ISO-8601-timestamp branch to the allow row.

3. A write-time counterpart, `hooks/secret-write-guard.py`, reads the same
   pattern file and `ask`s before the secret is even saved to disk, so this
   commit-time scan is the last line, not the only one.

## Editing `hooks/secret-patterns.txt`

Tab-separated, three columns: `kind` (`pattern` or `allow`), `name`, `ERE`. `#`
and blank lines are ignored. An `allow` row is applied only to the
`generic_assignment` rule's captured value, never to the prefixed shapes: a
literal `AKIA...` key stays a hit no matter what surrounds it.

**Two different regex engines read this file** - Python's `re` in the hook, gawk
ERE in `secret-scan.sh` - so every pattern must be in the intersection of both:

- No POSIX bracket classes. `[[:space:]]` is forbidden (Python cannot parse it);
  write `[ \t]`. `[[:alnum:]]` is forbidden; write `[a-z0-9]`.
- No `\b`, `\d`, `\w`, `\s`, no lookahead or lookbehind, no non-greedy `?`, no
  named groups. Plain ERE only.
- **Write every pattern lowercase.** Both readers lowercase the line before
  matching (awk via `tolower()`, the hook via `.lower()`), so no
  case-insensitivity flag is needed and none is applied. An uppercase letter in a
  pattern makes it dead.
- Anchor on a distinctive literal prefix or delimiter, never a bare length rule.

`hooks/test_secret_write_guard.py` asserts the no-POSIX-class rule and that every
shipped pattern compiles under Python, so a violation fails CI rather than
silently going dead on one of the two readers.

Its fixtures deliberately split each fake credential across a string
concatenation (`"AKIA" + "IOSFODNN7EXAMPLE"`). The runtime string the guard sees
is identical, but no single source LINE contains a complete match, so this
scanner does not flag its own test suite. Adding a fixture as one literal will
block the next commit that touches the file.
