# create-pr drafting rules

Subagent-only rubric for `/create-pr` step 2 - the main agent never applies
this directly, it only points the drafting subagent here. Read this file in
full when dispatched as that subagent.

### Auto-tier rubric (for the subagent to apply in step 2)

   Raw line count is a weak signal (a 700-line deletion is still *tiny* to
   explain). Tier on **how many distinct things a reviewer must understand**:
   - **Tiny** - one concern (docs, config, a single fix). Body = a TL;DR only:
     2-4 sentences, what + why. No headers, no bullets, no sections.
   - **Small/medium** - a few related changes. One-sentence "why" on top, then
     2-5 "what" bullets (only when there's genuinely more than one thing), then
     a `**Verify:**` line if there's something to check.
   - **Large** - multiple concerns / a new subsystem. Same light top, then a
     collapsed `<details><summary>Detail</summary>…</details>` block for
     context / approach / risk. The surface stays short; depth hides until clicked.

   **Title.** Conventional prefix reused from `/commit` (`FEAT FIX REFACTOR CHORE
   DOCS TEST STYLE DATA`). Derive from the commits; if they span prefixes, pick
   the one that names the dominant change. One line, no trailing period, says
   what changed - not how.

### Comment-noise check (for the subagent to apply in step 2)

See `skills/commit/comment-noise.md` for the cap definition and the mechanical
prefilter command (shared with `/commit`'s step 5a) - its range mode is
`git diff <base>`, not `<base>..HEAD`, so a re-run after step 2b's trims sees
the trim instead of stale hits. No output = `clean`, and the check is done - do not read a
single comment. Otherwise **judge only the flagged files**: read those diffs
and list the specific offending blocks (`file:line`, first line, line count).
A 5+ line block that genuinely documents one hard constraint can survive - say
so and why. Do not review comments in files the prefilter didn't flag; they
are in budget.

Never edit the comments in the subagent. Report; step 2b trims.

### Secret-scan check (for the subagent to apply in step 2)

See `skills/commit/secret-scan.md` for what it matches. Same range-mode
command as comment-noise, `git diff <base>`:
```
bash skills/commit/secret-scan.sh --range <base>
```
No output = `clean`. Any output is a hit, not a style call - report it to the
dev directly and do not draft the PR body until the value is removed and
replaced with an env var or secret-store read. Never trim or edit a flagged
line yourself.

### Visual scan rules (for the subagent to apply in step 2)

   It recommends, it never captures/uploads/embeds itself; that's step 3's
   job, gated on the dev's yes:
   - **Frontend / UI files** (`frontend/src/**`, `*.tsx`, `*.css`) → recommend
     `screenshot`, naming the most representative route to capture.
   - **Sensitive-content guard (public path only):** the pr-assets repo is
     PUBLIC. If a captured screenshot shows secrets, tokens, customer data, or
     anything Joe wouldn't want on a public URL, do NOT upload - fall back to
     the manual flow (local PNG path, dev drags it into the PR box himself,
     GitHub's own drag-drop upload is private-repo-safe). The private
     same-repo path below has no such exposure; the guard doesn't apply there.
   - **Schema / pipeline / data-flow files** (`domain/models/**`,
     `backend/**/pipelines/**`, `schema_manager.py`, `migrations/**`) →
     recommend `mermaid` and draft the fenced ` ```mermaid ` block inline in
     the body now (cheap, no capture/upload step needed) - GitHub renders it
     natively. Keep it to the nodes that changed, not the whole system.
   - Nothing matches → recommend `none`. Silence is correct; never pad with a
     diagram for its own sake.
   - Never auto-embed a screenshot or keep a mermaid block without the dev's
     explicit per-item yes (step 3). Do not silently substitute an
     existing/repurposed screenshot.

### Slack announcement block (opt-in per repo, for the subagent to apply in step 2)

   If the repo contains `.github/workflows/slack-announce.yml`, append a
   collapsed block to the PR body (after the main content). Format below is
   the default; a repo's `.claude/pr-style.md` overrides it where they differ:

   ```
   <details>
   <summary>📣 Slack Message on Merge</summary>

   <!-- slack-announce-start -->
   <blurb>
   <!-- SLACK_IMAGE_HERE -->
   <!-- slack-announce-end -->

   </details>
   ```

   If the visual scan recommended `screenshot`, leave the literal placeholder
   line `<!-- SLACK_IMAGE_HERE -->` (mirrors `<!-- IMAGE_HERE -->` in the main
   body - the image doesn't exist yet at draft time) so step 3 can splice the
   same `![...](url)` line in here too once approved. If no screenshot was
   recommended, omit the placeholder line entirely - don't leave a stray
   comment in the rendered block.

   The blurb: 1-3 casual first-person sentences from Joe's voice ("Just shipped
   X - it does Y"), aimed at teammates, not reviewers. **Slack-mrkdwn-safe
   plain text only**: no markdown links, no `**bold**`, no headers - the
   workflow posts it verbatim as Slack mrkdwn. Image lines must be exactly
   `![...](url)` at line start; the workflow parses them into Slack image
   blocks and strips them from the text. The dev can edit the block on GitHub
   before merging; the workflow posts whatever is between the markers at merge
   time. No workflow file in the repo → skip this step entirely, never ask.

## Image hosting

Pick the path by the CURRENT repo's visibility (`gh repo view --json isPrivate`):

- **Public repo → `SirBepy/pr-assets`** (the public path, below).
- **Private repo → the repo's own orphan `assets` branch**, if its
  `.claude/pr-style.md` documents one (fibo does) - follow that file exactly:
  upload via the contents API with `-f branch=assets`, embed via the
  same-origin blob URL `https://github.com/<owner>/<repo>/blob/assets/<path>?raw=true`.
  That URL form bypasses GitHub's camo proxy (served off the viewer's own
  session), so it renders in private-repo PR bodies; `raw.githubusercontent.com`
  URLs do NOT. No sensitive-content concern - nothing leaves the private repo.
- **Private repo without a `pr-style.md` hosting convention → manual fallback**
  (local PNG path, dev drags it into the PR box). Suggest setting up an assets
  branch as a follow-up rather than inventing one silently.

### The public path (pr-assets)

Screenshots embed via the dedicated public repo `SirBepy/pr-assets` - GitHub
proxies PR-body images through camo, which can't authenticate, so for public
hosting images must live at a public URL (this also makes them work in Slack
webhooks). Files are kept forever; they're tiny.

Upload via the contents API, no clone needed. `-f content=$b64` fails past a
small size (PowerShell's per-argument limit), and `-f`/`--raw-field` never
reads `@<path>` from a file - it sends the literal string. Use a JSON payload
file with `--input` instead, written BOM-less or `gh` rejects it (one
PowerShell call per image):

```
$payload = @{
  message = "ASSET: <repo> <branch> screenshot"
  content = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("<abs path>.png"))
} | ConvertTo-Json
$payloadPath = "<temp path>\payload.json"
[System.IO.File]::WriteAllText($payloadPath, $payload, [System.Text.UTF8Encoding]::new($false))
gh api --method PUT repos/SirBepy/pr-assets/contents/<repo-name>/<branch-slug>/<file>.png --input $payloadPath --jq .content.download_url
```

- Path convention: `<repo-name>/<branch-slug>/<descriptive-name>.png`. Unique
  filenames only - a PUT to an existing path fails without its blob sha; if
  re-shooting, suffix `-2`, `-3`.
- The command prints the final `https://raw.githubusercontent.com/...` URL;
  embed it as `![<what it shows>](<url>)` in the PR body.
- `gh` account: the global PreToolUse hook switches accounts by the CURRENT
  repo's origin, but pr-assets lives under SirBepy. From a non-SirBepy repo
  (zirtue/fibo/revaire cwd), the active account won't have push rights - scope
  the token instead of switching the active account, so the hook's
  cwd-based inference never gets involved and never needs restoring:
  ```
  $env:GH_TOKEN = gh auth token --user SirBepy
  gh api --method PUT repos/SirBepy/pr-assets/contents/<repo-name>/<branch-slug>/<file>.png --input $payloadPath --jq .content.download_url
  ```
  Set `$env:GH_TOKEN` in the SAME PowerShell call as the `gh api` call -
  shell state doesn't persist across separate tool calls.
- Remember the sensitive-content guard (Visual scan rules above): public URL, public repo.
