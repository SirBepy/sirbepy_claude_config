---
name: create-pr
description: Drafts a human-light PR for the current branch, scales the body to the diff, suggests visuals, previews locally, and creates it on approval.
disable-model-invocation: true
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
   (edit vs. create framing), and an instruction to read
   `C:\Users\tecno\.claude\skills\create-pr\drafting-rules.md` in full for the
   detailed rules (auto-tier thresholds, comment-noise check, visual scan,
   Slack-block format, image-hosting conventions) rather than re-explaining
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
     nothing and no linter can do it): see "Comment-noise check" in
     `drafting-rules.md`. Report the offenders as `file:line` + the block's
     first line + line count, or `clean`. Never rewrite them itself - the main
     agent gates it.
   - **Auto-tier** (see the auto-tier rubric in `drafting-rules.md`) and
     **title** (conventional prefix, one line).
   - **Visual scan** - inspect the changed-files list and decide what to
     *recommend*, per the "Visual scan rules" in `drafting-rules.md`, but do
     NOT capture or upload anything itself:
     - Frontend/UI files touched → recommend `screenshot`, name the route to
       capture.
     - Schema/pipeline/data-flow files touched → draft the mermaid block
       inline in the body now (cheap, no upload needed) and recommend
       `mermaid` so the main agent can ask whether to keep it.
     - Neither → recommend `none`.
     If recommending `screenshot`, leave a literal placeholder line
     `<!-- IMAGE_HERE -->` exactly where the image markdown should go once
     captured.
   - **Draft the body** per the tiering rubric (`drafting-rules.md`) +
     anti-bloat rules below, and the Slack announcement block
     (`drafting-rules.md`) if `.github/workflows/slack-announce.yml` exists.
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
     self-verify, run the sensitive-content guard (`drafting-rules.md`), then
     upload it per the "Image hosting" rules in `drafting-rules.md` and return
     ONLY the final embeddable image URL
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

See `skills/create-pr/drafting-rules.md` for the auto-tier rubric, the
comment-noise check, the visual-scan rules, and the Slack-announcement-block
format the drafting subagent applies in step 2.

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

See `skills/create-pr/drafting-rules.md` for the image-hosting conventions
(public vs. private repo, upload command, account caveats) the drafting
subagent applies when a screenshot needs embedding.

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
