<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=4, reconfirm-count=1, content-hash=233ab586 -->
<!-- duplicate-checked -->
# `/commit`'s secret scan fires on self-evidently fake placeholder values

**Type:** task
**Origin:** ai

## Goal

Stop `prefilter-gate.sh` blocking a commit on a value whose own text says it is not a credential,
without weakening the rule that catches real hardcoded secrets in test and scratch files.

## Context

Hit 2026-08-21 during an `/auto-do-todos` run in the `hubbub` repo. A new relay test asserted that
a WRONG token is rejected:

```ts
const out = await room.handleMessage("s2", { t: "attachScreen", token: "not-the-real-token" }, 0);
```

`secret-scan.sh`'s `generic_assignment` rule read `token: "<value>"` and blocked the commit.
`/commit` step 5a says a secret-scan hit is the one prefilter that is never auto-fixed, so the run
could not simply trim it, and an unattended run has nobody to ask.

The workaround applied was to hoist the literal to a differently-named const so the pattern no
longer matches:

```ts
const BOGUS = "not-the-real-token";
...
{ t: "attachScreen", token: BOGUS }
```

That works, but it is renaming a variable to dodge a scanner, and it needed a code comment to
explain why, which is exactly the kind of comment the comment-noise rule exists to prevent.

**The obvious fix is the wrong one.** Do NOT exempt `*.test.*` files. `secret-scan.md`'s own
measurement (todo 420, 22,992 real Write/Edit calls) says the generic rule's true positives were
largely "real JWTs and passwords in scratch verification scripts" - precisely the file class a
test-file exemption would blind.

## Approach

1. Add an `allow` row to `hooks/secret-patterns.txt` matching values that are self-evidently
   placeholders, keyed on the VALUE, not the file: something covering `not-`, `fake`, `dummy`,
   `example`, `placeholder`, `changeme`, `xxx`. The `allow` column already applies only to
   `generic_assignment`'s captured value, so prefixed shapes like `AKIA...` stay hits regardless.
2. Respect the two-engine constraint documented in `secret-scan.md`: plain ERE only, lowercase,
   no `\b`/`\d`/`\w`/`\s`, no POSIX bracket classes, no lookaround.
3. Add a fixture to `hooks/test_secret_write_guard.py` both ways: a placeholder value passes, and
   a real-looking secret that merely SITS NEAR the word "example" still fails.

## Acceptance

- `token: "not-the-real-token"` does not trip the gate.
- A real hardcoded JWT or password still does, including in a `.test.ts` file.
- `python ci/run_all.py` passes.

## Notes

- Worth is genuinely modest: this fired once across a long multi-repo run, and the workaround took
  under a minute. File it as a papercut, not a priority. The reason to fix it at all is that the
  workaround pushes toward renaming code to satisfy a linter, which is a bad habit to encode.
- Do not touch this from a project session; it is global-tree work.
