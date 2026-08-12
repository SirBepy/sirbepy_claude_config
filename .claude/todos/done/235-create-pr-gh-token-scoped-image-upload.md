<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=61a6914c -->
# create-pr: replace the gh auth switch dance in drafting-rules.md's image upload with a GH_TOKEN-scoped call

**Type:** skill-improvement

## Goal

`skills/create-pr/drafting-rules.md`'s public-repo image-hosting path currently tells the
dev to run `gh auth switch --user SirBepy` before uploading a screenshot to
`SirBepy/pr-assets`, then switch back - because the global `gh-account-switch.sh` hook
auto-switches `gh`'s active account to match the CURRENT repo's origin remote, which is
wrong when the current repo isn't SirBepy's (zirtue/fibo/revaire cwd) but the upload
target (`pr-assets`) always is. Replace this manual switch-then-restore dance with a
single `GH_TOKEN`-scoped call using `gh auth token --user SirBepy`, which bypasses the
hook's cwd-based account inference entirely.

## Context

`skills/create-pr/drafting-rules.md` (as of 2026-08-01), "Image hosting" section:

- Lines 131-135:
  ```
  - `gh` account: the global PreToolUse hook switches accounts by the CURRENT
    repo's origin, but pr-assets lives under SirBepy. From a non-SirBepy repo
    (zirtue/fibo/revaire cwd), the active account won't have push rights - run
    `gh auth switch --user SirBepy` first, upload, then switch back (or just
    re-run any repo-scoped gh command and let the hook restore it).
  ```
- The upload call itself (lines 118-124):
  ```powershell
  $b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("<abs path>.png"))
  gh api --method PUT /repos/SirBepy/pr-assets/contents/<repo-name>/<branch-slug>/<file>.png -f message="ASSET: <repo> <branch> screenshot" -f content=$b64 --jq .content.download_url
  ```

The global hook (`~/.claude/hooks/gh-account-switch.sh`, described in global CLAUDE.md's
"gh CLI Account" section) auto-switches based on the repo's `origin` remote before EVERY
`gh` command runs. `gh auth switch --user SirBepy` fights that hook: it's a manual
account change that the hook will silently revert on the very next `gh` call from a
non-SirBepy cwd, which is exactly the fragility this todo exists to remove. `gh auth
token --user SirBepy` instead reads SirBepy's stored token directly and lets it be passed
explicitly via the `GH_TOKEN` environment variable for a single command, without ever
touching the active-account state the hook manages - so the hook's cwd-based switching
logic never gets involved and never needs restoring afterward.

## Approach

1. Read `skills/create-pr/drafting-rules.md`'s full "Image hosting" section before
   editing (lines ~95-136 in the version described above).
2. Replace the `gh auth switch --user SirBepy` / switch-back instruction with:
   ```powershell
   $ghToken = gh auth token --user SirBepy
   $env:GH_TOKEN = $ghToken
   gh api --method PUT /repos/SirBepy/pr-assets/contents/<repo-name>/<branch-slug>/<file>.png -f message="ASSET: <repo> <branch> screenshot" -f content=$b64 --jq .content.download_url
   ```
   (or fold the `$env:GH_TOKEN` assignment inline before the `gh api` call - either way,
   never chain with `&&`/`;`/`|` per the global shell rule, keep them as separate
   PowerShell tool calls). Note `$env:GH_TOKEN` set this way only affects the current
   PowerShell tool-call session state per the harness's per-call shell semantics -
   confirm during implementation whether it needs to be set in the SAME call as the `gh
   api` invocation (likely yes, since shell state does not persist between separate tool
   calls per the Bash/PowerShell tool descriptions) and adjust the drafted command
   accordingly.
3. Update the surrounding prose (lines 131-135) to explain the new mechanism instead of
   the switch/restore dance - name why it's immune to the hook (never touches the active
   account) and drop the "or just re-run any repo-scoped gh command and let the hook
   restore it" fallback line, since there's nothing to restore anymore.
4. **Verify once against a public non-SirBepy repo** (per this todo's original ask) -
   from a repo whose origin maps to a DIFFERENT gh account per the hook's mapping (e.g.
   a zirtue-corp or revaire repo), run the new `gh auth token --user SirBepy` + `GH_TOKEN`
   upload flow and confirm: (a) the upload succeeds and returns a working
   `download_url`, (b) the hook did not get triggered into switching the active account
   as a side effect, (c) a subsequent ordinary `gh` command in that same repo still uses
   the repo's own correct account afterward (proving no lingering `GH_TOKEN` env leakage
   broke the hook's normal behavior for that repo).

## Acceptance

- `drafting-rules.md` no longer instructs `gh auth switch --user SirBepy` anywhere.
- The documented upload flow uses `gh auth token --user SirBepy` + `GH_TOKEN` instead.
- A real test run from a non-SirBepy repo confirms the upload works and leaves the active
  `gh` account/hook behavior for that repo undisturbed afterward.

## Notes

- completed, commit 00737e5. Doc/mechanism landed; the Acceptance line asking for a live upload from a non-SirBepy repo was not run, since this unattended run forbids write gh calls.

## Merged in (2026-08-11)

Absorbed todos 33 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
