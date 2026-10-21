<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# recall: index shows a plaintext password that sits on the line after a "Password:" label

**Type:** skill-improvement
**Origin:** ai

## Goal

`/recall show` and `/recall search` never print a credential that a past transcript shows as a bare value
on its own line under a password label. `skills/recall/SKILL.md` promises "Secrets are redacted in the
index as `[REDACTED:<kind>]`", and that promise holds for this shape too.

## Context

On 2026-10-22, session ea3b6f1b ran `python ~/.claude/skills/recall/recall.py show 83d15843 --grep "QR"`.
The output printed the FRITZ!Box admin password in plain text. It came from Claude's own message at
12:45 in session 83d15843 (2026-09-05, repo .claude), which had this shape:

```
**2.** Log in. Password:

> <the password>
```

`redact()` (`skills/recall/recall.py:79`) runs per line, using the patterns from
`hooks/secret-patterns.txt` through `secret-write-guard.py`. The label and the value are on different
lines, with a blank line and a blockquote `> ` between them. `generic_assignment`-style patterns need
`key = value` or `key: value` on one line, so they cannot match. The value is a short dictionary word plus
digits, so no token-shape pattern matches either. This todo does NOT repeat the value. Read it in the
transcript if needed, and never copy it into a file.

A second gap is upstream. In that 2026-09-05 session Claude itself wrote the router password into chat as a
copyable blockquote. The later `request_secret` tool (Conductor) prevents this. That session ran before
Claude used it.

## Approach

1. In `redact()`, add a two-line lookahead. When a line ends in a password-ish label (`password:`,
   `passwort:`, `pin:`, `lozinka:`, case-insensitive, optionally inside bold or a list marker), redact the
   first following non-blank line when it is short (at most 64 chars after stripping `> `, backticks and
   whitespace) and has no spaces. Use the kind `[REDACTED:labelled_password]`.
2. Add a case to `skills/recall/test_recall.py`. Use a synthetic transcript turn with the label, a blank
   line and a `> fakeword1234` blockquote, and assert that the index has the redaction and not the value.
   The test must fail before the change.
3. Rebuild the existing index so old entries are re-redacted. Check whether `recall.py` has a rebuild or
   `--reindex` path first. If it only indexes new or changed transcripts, add a forced full rebuild,
   or bump an index format version so that a version mismatch triggers one.

## Acceptance

- `recall.py show 83d15843 --grep "Log in"` prints `[REDACTED:...]` where the password was.
- The new test fails before the change and passes after it. `python skills/recall/test_recall.py` passes.

## Notes

- Joe was told on 2026-10-22 that this password is in a past transcript. Whether he changes it is his
  call. This todo fixes only the index leak.
