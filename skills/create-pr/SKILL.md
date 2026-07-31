---
name: create-pr
description: Triggers on /create-pr only. Drafts a human-light PR for the current branch, scales the body to the diff, suggests visuals, previews locally, and creates it on approval.
argument-hint: "[base-branch] [--draft] [--no-checks]"
---

# /create-pr

> Draft a PR a human can read in ten seconds, preview it locally, create it on approval.

## North star

A PR description is for the **reviewer**, not for an AI and not for the author.
Write the least that lets a person understand **what changed and why** without
opening the diff. Length tracks the change: a docs tweak gets two sentences, a
new subsystem gets a short structured body. When in doubt, write less.

**The "why" is the only part the diff can't show - lead with it. Everything a
reviewer could read straight off the diff is noise; cut it.**

## Procedure

**Context-cost rule: step 2's drafting, and step 3's screenshot capture, run
in a subagent - never the main agent.** Gathering full diffs, reading every
commit message, running lint/build, and especially base64-encoding a
screenshot for upload are all intermediate material - easily 50-150k tokens
of raw bytes that add zero value once the final ~150-word body + one image
URL exist. None of that belongs in the main agent's context. The main
agent's job is: the cheap precondition checks (step 1), the two live approval
gates (step 3's visual y/n, step 5's final y/n - subagents cannot call
`AskUserQuestion`, so these can never move), and the actual `git push` / `gh pr
create`. Everything else - drafting, checking, tiering, titling, screenshotting,
uploading - is a subagent's job. Model: always `model: 'sonnet'` explicitly
per the global subagent-model rule; never inherit.

1. **Preconditions (main agent, cheap - single-line outputs only).**
   - Refuse if on `main`/`master` - PRs come off a feature branch.
   - Base = first positional arg, else `main`.
   - Require `gh` (`gh --version`) and a GitHub remote (`gh repo view`). If
     either is missing, say so and stop.
   - Check whether a PR already exists for this branch (`gh pr view`) - just
     note yes/no, don't fetch its body yet. Existing PR → the subagent will
     regenerate (edit mode) instead of drafting fresh.
   - **Size gate:** run `git diff --stat <base>..HEAD` (one command, cheap).
     If it touches a single file with a small hunk count - the shape of a
     Tiny-tier PR per the Auto-tier rubric below - skip the subagent dispatch
     in step 2 entirely and draft inline in the main agent instead: gather
     (log/diff/commits), fast-check, tier, title, and write the preview file
     yourself. The whole point of subagent delegation is dodging 50-150k
     tokens of raw diff/log bytes on a large change; a single-file diff never
     approaches that, so the subagent's fixed dispatch overhead would cost
     more than it saves. Every multi-file or ambiguous-size diff still goes
     through step 2 as normal.

2. **Dispatch the drafting subagent (`general-purpose`, `model: 'sonnet'`) -
   skip this step entirely if the size gate above routed to inline drafting.**
   One call, foreground (its report is needed before anything else can happen).
   Give it: the branch name, the base branch, whether a PR already exists
   (edit vs. create framing), and an instruction to read this skill file
   (`C:\Users\tecno\.claude-fibo\skills\create-pr\SKILL.md`) in full for the
   detailed rules (auto-tier thresholds, title prefixes, anti-bloat rules,
   image-hosting conventions, Slack-block format) rather than re-explaining
   them inline. Its job, all read-only except the final file write:
   - **Gather**: `git log --oneline <base>..HEAD`, `git diff --stat <base>..HEAD`,
     `git diff --name-only <base>..HEAD`, and the actual commit messages - the
     PR body is a *synthesis* of them, not a concatenation. Check for
     `.claude/pr-style.md` and follow it if present (overrides this file's
     defaults - image hosting target, Slack format, anything else).
   - **Fast checks** (skip if `--no-checks` was passed): run only the checks
     the project HAS (typecheck / lint / build - not slow e2e). A failure is
     **not** an abort the subagent can act on - it must come back and report
     the failing command + output verbatim so the main agent can abort and
     show the dev. Do not draft a PR for a red branch.
   - **Comment-noise check** (always, not skippable by `--no-checks` - it costs
     nothing and no linter can do it): see "Comment-noise check" below. Report
     the offenders as `file:line` + the block's first line + line count, or
     `clean`. Never rewrite them itself - the main agent gates it.
   - **Auto-tier** (see the tiering rubric below) and **title** (conventional
     prefix, one line).
   - **Visual scan** - inspect the changed-files list and decide what to
     *recommend*, per the "Visual scan" rules below, but do NOT capture or
     upload anything itself:
     - Frontend/UI files touched → recommend `screenshot`, name the route to
       capture.
     - Schema/pipeline/data-flow files touched → draft the mermaid block
       inline in the body now (cheap, no upload needed) and recommend
       `mermaid` so the main agent can ask whether to keep it.
     - Neither → recommend `none`.
     If recommending `screenshot`, leave a literal placeholder line
     `<!-- IMAGE_HERE -->` exactly where the image markdown should go once
     captured.
   - **Draft the body** per the tiering rubric + anti-bloat rules below, and
     the Slack announcement block below if `.github/workflows/slack-announce.yml` exists.
   - **Write** the final body to `.for_bepy/pr_preview/<branch-slug>.md`
     (gitignored personal space - create the folder if missing).
   - **Return** (short - this is what crosses back into the main agent's
     context, keep it to a few lines): title, tier, base, checks status
     (pass, or the exact failure to show the dev), the comment-noise verdict
     (`clean`, or the offender list), visual recommendation + reason, and
     confirmation of the file path written. Do NOT return the full diffs,
     commit log, or check output in the happy-path case - the file on disk is
     the artifact; the return value is just enough for the main agent to act on.

2b. **Comment-noise gate (main agent).** If the verdict was `clean`, continue.
   Otherwise TRIM THE OFFENDERS FIRST, before the preview - do not ask whether
   to, do not offer to do it later, and never open the PR with them in. Cut to
   the constraint/gotcha/measurement the code can't show and delete the rest;
   if a whole block only restates the code, delete the whole block. Then
   re-run the project's fast checks, amend or add a commit via `/commit` (per
   the global rule, never a raw `git commit`), and only then continue. Say what
   was trimmed in one line - the dev does not need the before/after text.

3. **Visual approval (main agent - live gate, cannot delegate).** If the
   subagent recommended `none`, there's nothing to ask - continue to step 4.
   Otherwise ask the dev a short, dedicated y/n (separate from and before the
   step 5 approval gate - never fold the two together):
   - `mermaid` → "keep the mermaid diagram in the body?" On no: strip the
     block from the preview file (small `Edit`, main agent does this itself -
     it's a few lines, not worth a subagent round-trip). On yes: leave it.
   - `screenshot` → "embed a screenshot of `<route>`?" On yes: **dispatch a
     second, small subagent** (`general-purpose`, `model: 'sonnet'`) to bring
     the app up (reuse a running `/supervised-run` instance if one already
     serves the route, else start one), capture the screenshot, `Read` it to
     self-verify, run the sensitive-content guard (below), then upload it per
     the "Image hosting" rules and return ONLY the final embeddable image URL
     (or, if the guard tripped, a note to fall back to the manual
     drag-and-drop flow instead). The screenshot bytes and the upload's
     base64 payload never need to touch the main agent's context - only the
     URL string comes back.
   - On yes, splice the returned URL into `<!-- IMAGE_HERE -->` and, if
     present, `<!-- SLACK_IMAGE_HERE -->` too (`Edit`, main agent - both are
     a few characters in a small file). On no: delete both placeholder lines
     (an image line with nothing to show is worse than no image line).

4. **Render + emit preview markers (main agent, cheap - the file is small).**
   - `Read` the finished `.for_bepy/pr_preview/<branch-slug>.md` and render it
     inline in the chat so the dev reads it exactly as a reviewer will.
   - State the tier, the base branch, and any visual outcome.
   - **Emit the Claude Conductor in-app preview markers.** Base64-encode the
     body file's contents and the commits-JSON (built from the subagent's
     reported commit list) via PowerShell:
     ```
     $body = [System.IO.File]::ReadAllText("<absolute path to the preview .md>", [System.Text.Encoding]::UTF8)
     [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($body))
     ```
     (Always `ReadAllText` with explicit UTF8, never `Get-Content -Raw`: PS 5.1
     reads BOM-less UTF-8 files with the ANSI codepage and mangles non-ASCII
     characters like `→` into mojibake inside the base64 marker.)
     ```
     $commitsJson = '[{"sha":"abc1234","msg":"headline"},...]'
     [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($commitsJson))
     ```
     Then emit these three lines as PLAIN TEXT in your response (not in a code
     block, not in a blockquote - raw text so the app parser strips them from
     the chat display and shows the PR card instead):
     ```
     <cc-pr-title:TITLE_GOES_HERE>
     <cc-pr-body:BASE64_BODY>
     <cc-pr-commits:BASE64_COMMITS_JSON>
     ```
     The title must not contain `>` characters. The base64 values must be
     single lines with no spaces or line breaks.

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

The cap: **2 lines typical, 4 lines hard, per comment block**, and added comment
lines under **~25%** of a file's added lines once that file adds 20+ lines (below
that the ratio is noise - a 5-line constants file with one 2-line why-comment is
fine, and the block cap already covers it). Matches the global CLAUDE.md Code
Style rule; if a number changes, change it in both. A block earns its place ONLY
by naming a constraint, a gotcha, or a measurement the code cannot show.
Restating the next line, narrating steps, labelling JSX sections, or parking
design rationale in code all fail; rationale goes in the PR body.

1. **Mechanical prefilter** (one command, no judgment, run it verbatim):

   ```
   git diff <base>..HEAD | awk '
   /^\+\+\+ b\// { f=substr($0,7); run=0; next }
   /^\+/ && !/^\+\+\+/ {
     l=substr($0,2); add[f]++
     if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#|--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
     next
   }
   { run=0 }
   END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }' | sort
   ```

   No output = `clean`, and the check is done. Do not read a single comment.
2. **Judge only the flagged files.** Read those diffs and list the specific
   offending blocks (`file:line`, first line, line count). A 5+ line block that
   genuinely documents one hard constraint can survive - say so and why. Do not
   review comments in files the prefilter didn't flag; they are in budget.

Never edit the comments in the subagent. Report; step 2b trims.

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

5. **Confirm, then create (main agent - live gate, cannot delegate).**
   Pre-flight: have you already asked step 3's visual y/n as its OWN question
   (skippable only when the subagent recommended `none`)? If not, STOP and do
   it first - do not fold it into this step's question. This gate is **not
   skippable even when `/create-pr` is invoked as the tail of a bundled
   instruction** (e.g. "commit X onto its own branch and /create-pr") -
   bundled phrasing is not pre-approval. Always show the preview and wait for
   an explicit `AskUserQuestion` answer for THIS preview before calling `gh pr
   create`, every single time, no exceptions for how the invocation was phrased.

   Ask the dev to approve the previewed body (AskUserQuestion).
   Only on approval:
   - Push the branch if it isn't on the remote yet (`git push -u origin <branch>`).
     This is implied by the dev invoking `/create-pr`; still announce it, since it's
     an outward-facing action and triggers a credential popup.
   - `gh pr create --base <base> --head <branch> --title "<title>" --body-file <preview-file>`
     (add `--draft` if the flag was passed).
   - Print the PR URL. If the sensitive-content fallback left a screenshot
     un-embedded, remind the dev to drag it into the PR box.

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

Upload via the contents API, no clone needed (one PowerShell call per image,
never chained):

```
$b64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes("<abs path>.png"))
gh api --method PUT /repos/SirBepy/pr-assets/contents/<repo-name>/<branch-slug>/<file>.png -f message="ASSET: <repo> <branch> screenshot" -f content=$b64 --jq .content.download_url
```

- Path convention: `<repo-name>/<branch-slug>/<descriptive-name>.png`. Unique
  filenames only - a PUT to an existing path fails without its blob sha; if
  re-shooting, suffix `-2`, `-3`.
- The command prints the final `https://raw.githubusercontent.com/...` URL;
  embed it as `![<what it shows>](<url>)` in the PR body.
- `gh` account: the global PreToolUse hook switches accounts by the CURRENT
  repo's origin, but pr-assets lives under SirBepy. From a non-SirBepy repo
  (zirtue/fibo/revaire cwd), the active account won't have push rights - run
  `gh auth switch --user SirBepy` first, upload, then switch back (or just
  re-run any repo-scoped gh command and let the hook restore it).
- Remember the sensitive-content guard (Visual scan rules above): public URL, public repo.

## Anti-bloat rules (the actual point)

- **Hard budget**: tiny ≤ ~60 words; small/medium ≤ ~150 in the visible body
  (a `<details>` block doesn't count).
- **No bullet that just names a file.** If the bullet is "Updated `foo.ts`", delete it.
- **No restating the diff.** "Changed X from A to B" is what the diff is for.
- **"Why" before "what", always.**
- **No empty sections.** No blank `## Testing` / `## Screenshots` headers. If
  there's nothing to say, the section doesn't exist.
- **Banned phrases / tells**: "this PR introduces/aims to", "comprehensive",
  "robust", "seamlessly", "in order to", "various", emoji-as-headers, a lone
  `## Summary` header over a single paragraph.
- **No AI-attribution footer.** Deliberately drop the `🤖 Generated with Claude
  Code` line - it matches the dev's no-attribution commit rule and the human-light
  goal. (This overrides the harness default for PR bodies.)

## Rules

- One PR = one logical change. If the branch holds two unrelated things, say so
  and suggest splitting rather than papering over it with a long description.
- Never chain shell commands. One per call. Use `git -C <path>` / quote paths
  with spaces.
- Never create or push without the explicit approval gate in step 5.
- Edit mode (existing PR) regenerates the body the same way (subagent drafts,
  main agent gates); it never silently overwrites - it shows the new body and
  asks before `gh pr edit --body-file`.
- The drafting subagent never runs `git push` or `gh pr create`/`gh pr edit`
  itself - those are outward-facing, credential-triggering, and gated on live
  approval, so they stay with the main agent per the global rule that
  subagents don't take irreversible/outward-facing actions unsupervised.
