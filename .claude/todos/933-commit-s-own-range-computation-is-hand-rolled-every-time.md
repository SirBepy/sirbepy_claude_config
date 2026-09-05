<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: searched the backlog for foreign-hunk-check / --own; no existing entry. -->
# /commit's `--own` range computation is hand-rolled on every single commit

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop making the caller compute `foreign-hunk-check.sh`'s `--own` line ranges by hand, so the
working-tree check is cheap enough that nobody is tempted to skip it on a multi-commit sweep.

## Context

Surfaced 2026-09-05 during a Phase G session in `hubbub` that made **17 commits across 5 repos**.
`skills/commit/SKILL.md` step 8 requires, before every `git commit`:

```
bash skills/commit/foreign-hunk-check.sh -C <repo> --own <file>:<a>-<b>[,<a>-<b>...] <files>
```

Producing that argument means running `git diff -U0 -- <files>`, reading each `@@` header, and
converting `+<start>,<len>` into `<start>-<end>` per file - by hand, per commit. Two concrete costs
observed in that one session:

1. **It goes stale.** Ranges were computed, then a comment-noise trim shifted the lines, and the
   next check reported `foreign-hunks-inside-your-hunk 14-33` on a file with no peer edits at all.
   The ranges had to be re-derived from a fresh diff. A false positive on a security-shaped check
   is the failure mode that teaches people to stop running it.
2. **The caller wrote a wrapper anyway.** Rather than repeat the ceremony 17 times, the session
   wrote a throwaway `grp.sh` that computed `1-<wc -l>` per file and ran gate + check + commit as
   one call. That wrapper is the missing feature, written badly and thrown away.

Note the `1-<wc -l>` shortcut is only honest when the caller genuinely authored every uncommitted
line in those files. A real helper should derive the ranges rather than assume that.

## Approach

Add a `--own-from-diff` mode to `skills/commit/foreign-hunk-check.sh`: with no explicit `--own`,
it runs `git diff -U0` itself for the named pathspec, parses the `@@` headers, and treats every
hunk as own-unless-told-otherwise is WRONG - so instead invert it. The useful shape is the reverse
of today's: let the caller name the ranges it did NOT write (rare), or better, have the script
diff the working tree against the session's own last-known state.

Since that state does not exist, the pragmatic version is a `--own-files <file>...` flag meaning
"every uncommitted hunk in these files is mine", which is the assertion the caller is making today
anyway, just without the arithmetic. Keep explicit `--own` ranges for the genuinely mixed file.

Then update `skills/commit/SKILL.md` step 8 to show the new flag as the default form, with the
per-range form kept for the shared-file case.

## Acceptance

- A multi-file commit needs no `git diff -U0` reading and no manual range arithmetic.
- A file containing a hunk the caller did not write is still reported.
- The existing `--own <file>:<a>-<b>` form keeps working unchanged.

## Notes

- Do not solve this by dropping the check. It exists because a pathspec commit takes a file's whole
  working-tree state, and `git status`'s single `M` cannot say whose lines are in it.
- Related surface: `/commit` step 8 also asks for the unpushed-overlap check per commit; that one
  already takes a plain file list and needs no arithmetic, which is the ergonomic target here.
