<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/commit`'s documented inline here-string form broke on a message containing double quotes

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit`'s multiline-message recipe survive a commit message that contains double quotes,
instead of silently word-splitting it into pathspecs.

## Context

Happened 2026-08-18 while committing the `/ticket` merge.

The Bash tool description and `/commit`'s own usage both show the inline form:

```powershell
git commit -m @'
Commit message here.
'@
```

A message whose body contained the phrase `"file a ticket for this"` (with literal double quotes)
was passed that way, together with a `-- <pathspec>` list. It failed with git reporting the message
words as pathspecs:

```
error: pathspec 'a' did not match any file(s) known to git
error: pathspec 'ticket' did not match any file(s) known to git
error: pathspec 'for' did not match any file(s) known to git
```

so the here-string was not held together as one argument. A single-quoted here-string is supposed to
be literal, which is exactly why this is worth pinning down rather than working around by feel.

**What is NOT established, and must not be written up as if it were:** the retry changed *two*
things at once - it assigned the here-string to `$msg` first AND removed the double quotes from the
message. It succeeded, but that does not isolate which change fixed it. Do not claim "assign to a
variable first" as the fix until it has been tested on its own.

## Approach

1. Reproduce deliberately in a scratch repo, changing one variable at a time:
   - inline `-m @'...'@` with embedded double quotes,
   - inline `-m @'...'@` without them,
   - `$msg = @'...'@` then `-m $msg` **with** them.
   That third case is the one that decides whether the variable or the quotes mattered.
2. Fix whichever recipe is actually wrong. If the variable assignment is what saves it, change the
   documented form in `skills/commit/SKILL.md` and say why in one line, since the inline form reads
   more naturally and will otherwise be re-adopted.
3. Check whether the Bash tool's own guidance ("for multi-line strings use a heredoc") needs the
   same caveat noted somewhere Claude will actually read it.

## Acceptance

- The documented form survives a commit message containing double quotes, proven by a real commit.
- The writeup records which single change fixed it, with the failing and passing commands.

## Notes

- Filed 2026-08-18 by `/close`. Cost two failed commit attempts in one session.
- A second, unrelated failure in the same command was `README.md` being gitignored in this repo
  (`.gitignore:2` is a blanket `*`), so naming it in a pathspec is always an error here. Not part of
  this todo, just noted so the transcript is not misread as one bug.
