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

1. **Preconditions.**
   - Refuse if on `main`/`master` - PRs come off a feature branch.
   - Base = first positional arg, else `main`.
   - Require `gh` (`gh --version`) and a GitHub remote (`gh repo view`). If
     either is missing, say so and stop.
   - If a PR already exists for this branch (`gh pr view`), switch to **edit**
     mode: regenerate the body and offer to update it instead of creating a new one.

2. **Gather (read-only).** One command each, no chaining:
   - `git log --oneline <base>..HEAD` - the commits.
   - `git diff --stat <base>..HEAD` - size + file list.
   - `git diff --name-only <base>..HEAD` - for the visual scan.
   - Read the actual commit messages - they already encode the "what + why".
     The PR body is a *synthesis* of them, not a concatenation.

3. **Fast checks** (skip if `--no-checks`). Run only the checks the project HAS
   (typecheck / lint / build - not slow e2e). If one fails, **abort**, print the
   failing output, and explain why. Do not draft a PR for a red branch.

4. **Auto-tier - by judgment, biased small.** Raw line count is a weak signal (a
   700-line deletion is still *tiny* to explain). Tier on **how many distinct
   things a reviewer must understand**:
   - **Tiny** - one concern (docs, config, a single fix). Body = a TL;DR only:
     2-4 sentences, what + why. No headers, no bullets, no sections.
   - **Small/medium** - a few related changes. One-sentence "why" on top, then
     2-5 "what" bullets (only when there's genuinely more than one thing), then
     a `**Verify:**` line if there's something to check.
   - **Large** - multiple concerns / a new subsystem. Same light top, then a
     collapsed `<details><summary>Detail</summary>…</details>` block for
     context / approach / risk. The surface stays short; depth hides until clicked.

5. **Title.** Conventional prefix reused from `/commit` (`FEAT FIX REFACTOR CHORE
   DOCS TEST STYLE DATA`). Derive from the commits; if they span prefixes, pick
   the one that names the dominant change. One line, no trailing period, says
   what changed - not how.

6. **Visual scan → suggest → you approve (never auto-embed).** Inspect the
   changed-files list and propose at most what fits:
   - **Frontend / UI files** (`frontend/src/**`, `*.tsx`, `*.css`) → before
     installing any browser harness, probe once for the `SendUserFile` tool
     (`ToolSearch` or check the tool list). **If present:** offer a
     **screenshot**. On yes: bring the app up via `/supervised-run`, capture with
     the `/screenshot` helper, `SendUserFile` the image to the dev, and add a line to
     the preview: *"Screenshot saved at `<path>` - drag it into the PR box after
     create (GitHub needs a manual image upload)."* Do **not** try to embed a
     local path in the body; it won't render. **If absent:** still capture the
     screenshot - it remains the verification step - `Read` it to self-verify the
     change, then give the dev (a) the live `/supervised-run` URL + the exact
     route to the changed view, and (b) the absolute PNG path to drag into the
     PR box himself. Say plainly that no image-to-chat channel exists this
     session; do not silently substitute an existing/repurposed screenshot.
   - **Schema / pipeline / data-flow files** (`domain/models/**`,
     `backend/**/pipelines/**`, `schema_manager.py`, `migrations/**`) → offer a
     **mermaid diagram** of the changed flow. On yes: embed a fenced ` ```mermaid `
     block directly in the body - GitHub renders it natively, so it stays text and
     stays a light read. Keep it to the nodes that changed, not the whole system.
   - Nothing matches → no visual. Silence is correct; never pad with a diagram
     for its own sake.
   - **Ask per item, as its OWN short y/n question, separate from and before**
     the step 8 approval gate. Never fold the visual y/n into the final
     approval `AskUserQuestion` alongside other questions - that's the exact
     violation this note exists to prevent. Embed nothing the user didn't approve.

7. **Preview locally (before any create).**
   - Write the final body to `.for_bepy/pr_preview/<branch-slug>.md` (gitignored
     personal space - never staged; create the folder if missing).
   - Render it **inline in the chat** so the dev reads it exactly as a reviewer will
     (the terminal renders GitHub-flavored markdown; mermaid shows as a code block
     here but renders on GitHub).
   - State the tier picked, the base branch, and any visual follow-up.
   - **Emit the Claude Conductor in-app preview markers** so the modal card appears.
     Run these PowerShell commands (one per call, no chaining) to encode the data:
     ```
     $body = [System.IO.File]::ReadAllText("<absolute path to .for_bepy\pr_preview\<slug>.md>", [System.Text.Encoding]::UTF8)
     [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($body))
     ```
     (Always `ReadAllText` with explicit UTF8, never `Get-Content -Raw`: PS 5.1
     reads BOM-less UTF-8 files with the ANSI codepage and mangles non-ASCII
     characters like `→` into mojibake inside the base64 marker.)
     Build the commits JSON string from the git log output gathered in step 2
     (array of `{"sha":"<7chars>","msg":"<headline>"}` objects), then encode it:
     ```
     $commitsJson = '[{"sha":"abc1234","msg":"headline"},...]'
     [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($commitsJson))
     ```
     Then emit these three lines as PLAIN TEXT in your response (not in a code block,
     not in a blockquote - raw text so the app parser strips them from the chat display
     and shows the PR card instead):
     ```
     <cc-pr-title:TITLE_GOES_HERE>
     <cc-pr-body:BASE64_BODY>
     <cc-pr-commits:BASE64_COMMITS_JSON>
     ```
     The title must not contain `>` characters. The base64 values must be single
     lines with no spaces or line breaks.

8. **Confirm, then create.** Pre-flight: have you already asked step 6's visual
   y/n as its OWN question? If not, STOP and do it first - do not fold it into
   this step's question. This gate is **not skippable even when `/create-pr` is
   invoked as the tail of a bundled instruction** (e.g. "commit X onto its own
   branch and /create-pr") - bundled phrasing is not pre-approval. Always show
   the preview and wait for an explicit `AskUserQuestion` answer for THIS
   preview before calling `gh pr create`, every single time, no exceptions for
   how the invocation was phrased.

   Ask the dev to approve the previewed body (AskUserQuestion).
   Only on approval:
   - Push the branch if it isn't on the remote yet (`git push -u origin <branch>`).
     This is implied by the dev invoking `/create-pr`; still announce it, since it's
     an outward-facing action and triggers a credential popup.
   - `gh pr create --base <base> --head <branch> --title "<title>" --body-file <preview-file>`
     (add `--draft` if the flag was passed).
   - Print the PR URL. If a screenshot is pending, remind the dev to drag it in.

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
- Never create or push without the explicit approval gate in step 8.
- Edit mode (existing PR) regenerates the body the same way; it never silently
  overwrites - it shows the new body and asks before `gh pr edit --body-file`.
