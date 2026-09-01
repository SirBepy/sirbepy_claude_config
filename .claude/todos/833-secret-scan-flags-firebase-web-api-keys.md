<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=8, reconfirm-count=1, content-hash=ca9d15bf -->
<!-- duplicate-checked -->
# secret-scan flags Firebase web API keys, which are public by design

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `secret-scan.sh` blocking commits on a `AIza...` Firebase web API key. It is not a credential,
it must be in client source for the app to work, and today it forces a stop-and-ask on every commit
that touches a Firebase config.

## Context

Hit 2026-08-29 in the `countoff` project, wiring Firestore sync. The gate exits 1 on:

```
src/lib/firebase.ts:18: apiKey: 'AIzaSyCMxWyGRJScXgsl1qa_nNbUdIs5o86w83Y'
```

`skills/commit/secret-scan.md` is explicit that a secret-scan hit is the one prefilter that is never
auto-fixed or worked around, so the correct behaviour was to stop and surface it. That is the right
default and should not change. The problem is narrower: this particular shape is guaranteed to be a
false positive, and it will recur on every Firebase project.

Why it is genuinely not a secret:

- A Firebase web API key identifies the project to Google's endpoints. It carries no authorisation.
- It cannot be kept private: the browser bundle must contain it, so it is readable by anyone who
  loads the page.
- Access is enforced by Firestore security rules plus the signed-in user plus the project's
  authorised domains, none of which the key affects.

The residual risk is real but different in kind: an unrestricted key can be pointed at other enabled
Google APIs in the same project, which is why Google recommends API key restrictions. That is a
project-configuration matter, not a source-control one, so it does not belong in a commit gate.

## Approach

- Add an `allow` row to `hooks/secret-patterns.txt` for the Firebase web key shape. Per that file's
  own rules the pattern must be plain ERE, lowercase, no `\b`/`\d`/`\w`/`\s`, no lookaround, and it
  applies only to the `generic_assignment` rule's captured value.
- Keep it tight. `aiza[a-z0-9_-]{35}` is the documented Google API key shape; do not widen it to
  every `AIza`-prefixed string in arbitrary context.
- Consider whether the allow row should be conditional on the assignment target being `apikey`, so a
  Google API key assigned to some other name still trips the scanner.
- Update `skills/commit/secret-scan.md` with a line naming this as a known-benign shape and why, so
  the next session does not re-litigate it from scratch.

## Acceptance

- A commit touching a file containing `apiKey: 'AIza...'` passes `prefilter-gate.sh` with exit 0.
- A real credential shape (`AKIA...`, `github_pat_...`, a bare `sk-...`) still trips the scanner in
  the same file.
- `python ci/run_all.py` passes, including the hook self-tests that read `secret-patterns.txt`.

## Notes

Filed from a `countoff` session, so it was written here rather than acted on: global `~/.claude` work
needs the dev's say-so in the session that does it.

The countoff commit that surfaced this was held pending his decision rather than being pushed past
the gate, which is the behaviour the current rule intends.
