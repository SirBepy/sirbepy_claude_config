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
   - **Base branch.** If a positional arg was passed, use it - done. Otherwise
     never hardcode `main`: detect the repo's real default branch via
     `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`
     (verified working in PowerShell for a simple, space-free `--jq`
     expression like this one; if a future edit grows the expression and hits
     PowerShell's word-splitting on quoted `--jq` args - `gh` dying with
     "accepts 1 arg(s)" - pipe to `ConvertFrom-Json` and read
     `.defaultBranchRef.name` off the object instead). Then check the remote
     for other long-lived candidates (`git branch -r` filtered to `main`,
     `master`, `develop`, `dev`, `trunk`, `release`, `staging`, excluding
     whichever one `gh` just returned). If more than one candidate branch
     exists, the right base is ambiguous - do not silently default to the
     detected branch either: ask the dev via `AskUserQuestion`, listing the
     detected default plus each other candidate as options. This check runs
     unconditionally, regardless of whether any doc file exists and regardless
     of which repo this is - it must never depend on a root `GIT_FLOW.md`
     being present and must never special-case a repo by name.
   - Require `gh` (`gh --version`) and a GitHub remote (`gh repo view`). If
     either is missing, say so and stop.
   - Check whether a PR already exists for this branch (`gh pr view`) - just
     note yes/no, don't fetch its body yet. Existing PR → the subagent will
     regenerate (edit mode) instead of drafting fresh.
   - **Title-convention probe** (one `gh` call, cheap):
     `gh pr list --state merged --limit 10 --json title --jq '.[].title'`.
     Pass the raw titles to the step 2 subagent - they outrank
     `drafting-rules.md`'s conventional-prefix table for this repo, which is
     the fallback for a repo with no discernible pattern (fewer than 3
     merged titles, or no shared structure among them), never the default.
   - **GIT_FLOW gate:** if `GIT_FLOW.md` exists at repo root, read it fully
     before asking anything, then batch every decision it implies for this PR
     (branch/base, reviewer, any deviation confirmation) into ONE
     `AskUserQuestion` call - never a first question now and a second
     "oh, also" round later for something already readable from the file.
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
   One call, **`run_in_background: false`** (foreground - its report is needed
   before anything else can happen). Paste the canonical preamble from
   `refs/builder-preamble.md` into the dispatch prompt (paste it, don't retype
   it) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its
   staging line, `run_in_background`/`FORBIDDEN` sentence, and screenshot-id
   marker.
   Give it: the branch name, the base branch, whether a PR already exists
   (edit vs. create framing), the step 1 title-convention probe's raw title
   list, and an instruction to read
   `C:\Users\tecno\.claude\skills\create-pr\drafting-rules.md` in full for the
   detailed rules (auto-tier thresholds, visual scan,
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
   - **Secret-scan check** (always, not skippable by `--no-checks`): see
     "Secret-scan check" in `drafting-rules.md`. Report any hit as `file:line`
     + the flagged text, or `clean`. This is not auto-fixable - do not draft
     the PR body if it hits, report the hit and stop so the main agent can
     surface it to the dev.
   - **Auto-tier** (see the auto-tier rubric in `drafting-rules.md`) and
     **title**, one line: match the shape of the step 1 probe's titles
     (case, punctuation, scope, and whether they carry a ticket id). If a
     probed title's ticket id sits in a slot the branch name also encodes
     (`rev-5312-...` -> `REV-5312`), reuse it. This overrides
     `drafting-rules.md`'s conventional-prefix table (`FEAT:`/`FIX:`/etc.) -
     that table applies only when the probe found fewer than 3 merged
     titles or no shared structure among them.
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
     (pass, or the exact failure to show the dev), the secret-scan verdict
     (`clean`, or the hit list), visual recommendation + reason, and
     confirmation of the file path written. Do NOT return the full diffs,
     commit log, or check output in the happy-path case - the file on disk is
     the artifact; the return value is just enough for the main agent to act
     on.

2b. **Secret-scan gate (main agent).** If the verdict was `clean`, continue.
   Otherwise STOP - do not write the preview file, do not open the PR. Show
   the dev the flagged `file:line` and tell them to remove the literal value,
   replace it with an env var or secret-store read, and commit the fix before
   `/create-pr` runs again. This is not auto-fixable.

3. **Visual approval (main agent - live gate, cannot delegate).** If the
   subagent recommended `none`, there's nothing to ask - continue to step 4.
   Otherwise ask the dev a short, dedicated y/n (separate from and before the
   step 5 approval gate - never fold the two together):
   - `mermaid` → "keep the mermaid diagram in the body?" On no: strip the
     block from the preview file (small `Edit`, main agent does this itself -
     it's a few lines, not worth a subagent round-trip). On yes: leave it.
   - `screenshot` → "embed a screenshot of `<route>`?" On yes: **dispatch a
     second, small subagent** (`general-purpose`, `model: 'sonnet'`,
     `run_in_background: false` - same live-gate dependency as step 2) to
     bring the app up (reuse a running `/supervised-run` instance if one already
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
   - **Step 4 must be the FINAL action of its turn - no tool call after it,**
     with one exemption below for Claude Conductor. Text emitted right before a
     tool call can be invisible to the dev, so the rendered preview and the
     markers have to land in a turn with nothing after them. Step 5's
     `AskUserQuestion` opens a NEW turn, never the same one.
   - **Claude Conductor specifically:** Conductor mandates `report_turn_status`
     as the literal last action of every turn (a Stop hook blocks the turn
     otherwise), so "no tool call after it" is unsatisfiable there as written.
     Which fix applies depends on an unverified fact - whether Conductor's
     card parser reads raw assistant text or only `send_message` payloads -
     that cannot be confirmed from outside a live Conductor session:
     - If the parser reads raw assistant text: the "no tool call after it"
       rule is exempt for `report_turn_status` only, since that call is
       harness-mandated and carries no user-visible text - emit the markers
       as plain text same as elsewhere, then call `report_turn_status`.
     - If the parser only reads `send_message` payloads: emit the three
       marker lines as the body of a `send_message` call instead of raw
       assistant text.
     Do not do both - the rendered inline preview from this step plus a
     rendered card is a duplicate wall of text for the dev.

See `skills/create-pr/drafting-rules.md` for the auto-tier rubric, the
secret-scan check, the visual-scan rules, and the Slack-announcement-block
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
   An earlier same-session "don't ask me things" instruction never suspends this
   gate either, even for a new push to an already-approved PR - it still asks,
   every time, for every preview.

   Ask the dev to approve the previewed body (AskUserQuestion).
   Only on approval:
   - **Mandatory pre-publish grep, before any `gh pr create --body-file` or
     `gh pr edit --body-file` call, no exceptions**: grep the preview file
     (body text and any embedded image caption) for the em dash character
     (U+2014). A hand-authored caption like `![Scope switcher open — searchable...]`
     is exactly the string most likely to carry a stray one, and this file
     never goes through a commit step where the usual grep habit would catch
     it. Fix any hit before publishing, not after - replace the em dash with a
     comma, colon, or hyphen (`Edit`, main agent, not a shell text write) and
     re-render the preview.
   - **PR-guard marker:** a global PreToolUse hook blocks raw `gh pr
     create`/`gh pr edit`. Immediately before that call, and no earlier,
     write a uniquely-suffixed marker:
     ```powershell
     Set-Content -Path "C:\Users\tecno\.claude\hooks\.pr-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"
     ```
     Each call writes its own fresh marker; the hook consumes the oldest
     fresh one and leaves the rest, so two concurrent sessions can't consume
     each other's. The hook needs a marker written within the last 2
     minutes, so redo this before every individual `gh pr create`/`gh pr
     edit` call, not once for the whole flow (this includes edit-mode
     regenerations of an already-created PR).
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
- Use `git -C <path>` / quote paths with spaces.
- Never create or push without the explicit approval gate in step 5.
- Edit mode (existing PR) regenerates the body the same way (subagent drafts,
  main agent gates); it never silently overwrites - it shows the new body and
  asks before `gh pr edit --body-file`.
- **Title-only rename** (e.g. fixing a title after the fact) skips that whole
  flow: run `gh pr edit <number> --title "<new title>"` directly.
  `hooks/pr-guard.py`'s ownership check already lets an edit to the dev's own
  PR through without a marker or `CLAUDE_PR_HOOK_BYPASS`, so a title fix
  never forces a full body regeneration.
- The drafting subagent never runs `git push` or `gh pr create`/`gh pr edit`
  itself - those are outward-facing, credential-triggering, and gated on live
  approval, so they stay with the main agent per the global rule that
  subagents don't take irreversible/outward-facing actions unsupervised.
