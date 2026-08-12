<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=0e7ebd60 -->
# Fix /create-pr's image-hosting instructions for this repo

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/create-pr`'s "Image hosting" section describe what actually works in fibo, so the next
session doesn't rediscover the assets-branch flow by trial and error.

## Context

Found while embedding a GIF + two stills in PR #188 (2026-07-29).

Skill file: `C:\Users\tecno\.claude\skills\create-pr\SKILL.md`, the "Image hosting" section.

Two things it gets wrong:

1. It says private repos use "the repo's own orphan `assets` branch, **if its
   `.claude/pr-style.md` documents one (fibo does)**". Fibo has no `.claude/pr-style.md` - not in
   the main checkout, not in a worktree. Following the skill literally routes to the manual
   drag-and-drop fallback, even though the `assets` branch DOES exist
   (`git ls-remote --heads origin assets` -> `c1825a2`) and is already organised one folder per
   branch slug (`feature-frontend2-item-cards/`, `fix-pageheader-inline-toolbar/`, ...).
2. Its upload recipe passes base64 on the command line (`-f content=$b64`). That works for a small
   PNG and fails for anything real: a 129KB GIF is ~172KB of base64, well past PowerShell's
   per-argument limit. The working form is a JSON payload file plus
   `gh api --method PUT "repos/Fibo-Studio/fibo/contents/<slug>/<file>" --input payload.json`, with
   the file written BOM-less (`[System.IO.File]::WriteAllText` + `UTF8Encoding($false)`) or gh
   rejects it. Same gotcha the `gh-api-windows-gotchas` memory already records for other endpoints.

Embed URL form that renders in a private repo's PR body is the one the skill already documents and
that part is correct: `https://github.com/<owner>/<repo>/blob/assets/<path>?raw=true` (camo can't
authenticate `raw.githubusercontent.com`).

## Approach

Either write the missing `frontend2/.claude/pr-style.md`... actually repo-root `.claude/pr-style.md`
documenting the assets-branch convention (folder-per-branch-slug, the blob?raw=true embed form, the
`--input` payload requirement), OR drop the "(fibo does)" claim from the skill and describe the
detection step instead: `git ls-remote --heads origin assets`, and use it if present. Prefer the
pr-style.md route - the skill already defers to that file, so one file makes the skill correct for
this repo without editing the skill at all.

Then fix the base64 recipe in the skill itself, since that bug is not repo-specific.

## Acceptance

- A fresh session asked to embed a screenshot in a fibo PR finds the assets branch by reading docs,
  not by probing.
- The documented upload command works for a 100KB+ file on the first try.

## Notes

Folded in from todo 134 (archived 2026-07-31, same bug): `-f`/`--raw-field` does NOT support the
`@<path>` read-from-file syntax at all - it silently sends the literal string and GitHub replies
"content is not valid Base64". Only `-F`/`--field` (or `--input <json-payload-file>`) reads from a
file. Payload file must be BOM-less. When invoked via the Bash tool (not PowerShell), also use
`repos/...` with no leading slash or MSYS rewrites it to a filesystem path. Full detail in
auto-memory `gh-api-windows-gotchas.md`. 2026-07-31 update: uploads worked first-try today using a
temp payload file, and `.claude/pr-style.md` still does not exist at repo root (only a copy inside
the unmerged slack-announce worktree) - the "write pr-style.md" half of this todo is still open.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 177; renumbered to 33 per the max+1 id rule. Confirmed by dev 2026-08-07.

- 2026-08-08, /auto-do-todos: the skill half is DONE and committed (`eecad49`). The 2026-07-31 note
  above saying the base64 bug was fixed was wrong - `drafting-rules.md` still passed `-f content=$b64`
  on the command line. It now builds a JSON payload, writes it BOM-less, and uploads via
  `gh api --input`. Only the fibo-side file remains.
- Duplicate of 235 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.

## Open questions

Written by /auto-do-todos on 2026-08-08. The dev authorized the cross-repo write, and
`.claude/pr-style.md` IS now written to disk at `C:\Users\tecno\Desktop\Projects\fibo\`. It cannot be
committed: fibo's `.gitignore` line 117 ignores `.claude/*` and allowlists only `.claude/skills/` and
`.claude/commands/opsx/`, a deliberate team convention per its inline comment. This also explains the
note above about the file existing only inside an unmerged worktree - same gitignore, force-added
there and never merged.

- [ ] [TOOLING] How should `.claude/pr-style.md` get tracked in fibo? Options: (a) `git add -f` it as
      a deliberate one-off exception; (b) add a narrow `!.claude/pr-style.md` allowlist line to
      fibo's `.gitignore` next to the existing exceptions. Recommended: (b), because (a) leaves the
      file invisible to `git status` forever, so the next person to edit it will not notice it drifted.
      Either way it edits a team-owned file, which is why this is the dev's call and not Claude's.

- Re-verified 2026-08-08: premise still holds.
