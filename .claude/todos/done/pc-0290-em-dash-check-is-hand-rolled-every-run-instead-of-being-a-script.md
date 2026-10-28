<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The em-dash check gets hand-rolled per run instead of being a script next to comment-noise.sh

**Type:** skill-improvement
**Origin:** ai

## Goal

Ship an em-dash-on-added-lines checker as a real script beside `skills/commit/comment-noise.sh`, and
wire it into `/commit` step 5a so the check runs mechanically instead of being improvised each time.

## Context

Surfaced by the `/close` retrospective of the 2026-08-12 `/auto-do-todos` run.

The "never use the em dash character anywhere" rule is stated in CLAUDE.md and every builder dispatch
prompt in that run repeated it verbatim. Agents still introduced em dashes three separate times, and
each time the main agent detected and fixed them with a DIFFERENT ad-hoc invention:

1. Wave 2, `skills/shortcut-done-audit/SKILL.md`: five hand-written `Edit` calls, one per line.
2. Wave 3, `skills/shortcut-create-ticket/SKILL.md` and `skills/shortcut-priorities/SKILL.md`: an
   inline PowerShell script written on the spot that diffed added lines against `HEAD` and replaced
   the character only on lines the diff actually added.
3. Wave 4, `skills/shortcut-update-ticket/SKILL.md` (a new file): a whole-file replace.

Same check, three implementations, one session. The wave-3 version is the correct one and the only
one worth keeping: replacing every em dash in a touched file is a drive-by edit of lines the change
never intended to touch, which is why added-lines-only is the right scope.

There are four archived todos about em-dash enforcement (`done/31`, `done/59`, `done/213`,
`done/269`), so a hook may already exist. It did not fire here. Establish whether that is because the
hook only inspects the dev-facing message text and not file writes, before building anything new.

## Approach

1. First determine what already exists. Check `hooks/` and `settings.json` /
   `settings.local.json` for an em-dash hook and read what surface it actually inspects. If it only
   covers outbound messages, say so in the fix, that is the reason file writes slip through.
2. Add `skills/commit/em-dash.sh` (mirroring `comment-noise.sh`'s shape: working-tree mode taking
   file paths, plus a `--range <base>` mode) that reports em dashes on ADDED lines only, printing
   `<file>:<line>` per hit and exiting 0 with no output when clean. Added-lines-only is the whole
   point: a file can legitimately carry pre-existing em dashes that are not this change's business.
3. Reference it from `/commit` step 5a next to the comment-noise prefilter, same "flagged means fix
   it now, do not ask" treatment.
4. Reference it from `refs/delegation-doctrine.md`'s builder-prompt requirements, alongside the
   comment-noise prefilter line that todo 272 added, so builders self-check before reporting.

## Acceptance

- `bash skills/commit/em-dash.sh <files>` prints nothing and exits 0 on a clean diff.
- On a diff that adds an em dash it prints the file and line, and exits 0 (report, do not fail the
  shell, matching `comment-noise.sh`'s contract).
- A pre-existing em dash on an UNCHANGED line is not reported.
- `--range <base>` mode works over a multi-commit range.
- `/commit` step 5a and `refs/delegation-doctrine.md` both point at it.

## Notes

- Do not "fix" this by adding more emphatic wording to the rule. The rule was already stated in
  CLAUDE.md and repeated verbatim in every dispatch prompt of the run where it was broken three
  times. This todo exists because wording alone demonstrably failed.
- Done 2026-08-13. New skills/commit/em-dash.sh mirrors comment-noise.sh's shape, working-tree plus --range modes, added lines only, exit 0 always, and folds in the untracked-file handling so it cannot repeat the pipefail bug fixed in 5e259da. Builds the em dash from raw UTF-8 bytes so the script never trips its own check. Wired into /commit step 5a alongside comment-noise, and into delegation-doctrine's builder-dispatch prefilter list. Verified against a real seeded diff: reported file:line correctly, exit 0.
