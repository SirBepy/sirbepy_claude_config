<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog for flagged-skill-mention / disable-model-invocation / UserPromptSubmit injection; nothing covers the line-position rule. -->
# 891 - flagged-skill-mention silently misses a flagged skill named mid-line

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-02

## Goal

Decide whether `hooks/flagged-skill-mention.py` should match a `/<skill>` mention anywhere in the
prompt, not only in the first line or at the start of a later line - and if so, widen it without
reintroducing the bare-word false positives the current anchoring exists to prevent.

## Context

`hooks/flagged-skill-mention.py:56-60` builds

```python
_name_pattern = r'(?<![\w/-])/' + re.escape(name) + r'(?![\w-])'
mentioned = re.search(_name_pattern, first_line, re.IGNORECASE) or any(
    re.match(_name_pattern, ls, re.IGNORECASE) for ls in line_starts
)
```

So a flagged skill fires when it appears **anywhere in the first line**, or **at the start of any
other line**. A mention part-way through a later line never fires.

Observed 2026-09-02 in zng-app. Joe's `/iterate-it` args were a multi-line autopilot chain ending:

```
/e2e
and then when youre done just /commit and then /close up
```

`/e2e` opened its own line and was injected correctly. `/close` sat mid-line on the last line and
was NOT injected, so `Skill({skill: "close"})` rejected with `disable-model-invocation` and the
close phases could not run in that turn - Joe had to send `/close` again as its own prompt. `/commit`
on the same line was unaffected only because it is model-invocable and does not need the hook.

The anchoring is deliberate, per the comment at `flagged-skill-mention.py:54-55`: bare-word names
(`close`, `review`, `pickup`) collided with plain English and fired on ambient text. Requiring the
leading slash already carries most of that protection; the extra line-position requirement may be
belt-and-braces that now costs more than it saves, given how often Joe writes multi-command
autopilot chains in prose.

The loop itself is fine - it appends every match, so several flagged skills CAN inject from one
prompt. Position is the only gate.

Related: the zng-app memory `reference_close_skill_needs_standalone_message` documents the
observed behaviour and now carries the corrected position rule, but a memory only helps a session
that already loaded it; the hook is where the fix belongs.

## Approach

Two candidate changes, pick after checking the false-positive risk against real transcripts:

1. Drop the line-position requirement entirely: `re.search(_name_pattern, prompt, re.IGNORECASE)`
   over the whole prompt. Simplest. Re-run whatever false-positive cases motivated the original
   anchoring before adopting - the commit that added the slash requirement should name them.
2. Keep the anchoring but also match a mention that follows a conjunction/imperative
   (`and then /close`, `then /close`, `just /close`). Narrower, more code, more to get wrong.

Option 1 first unless the false positives turn out to be real with the slash requirement in place.

Whichever lands, add a case to the hook's own test file if one exists (`hooks/test_*.py`), since
`python ci/run_all.py` runs those.

## Acceptance

- A prompt whose last line is `and then when youre done just /commit and then /close up` injects
  `close/SKILL.md`.
- Ambient prose mentioning `close`, `review` or `pickup` WITHOUT a leading slash still does not fire.
- `python ci/run_all.py` green.

## Notes

- Completed in /mega-todos wave 1, commit 6c293bb: flagged-skill-mention.py now searches the whole prompt instead of only the first line or a line start, with added false-positive cases for a skill name appearing in ordinary prose.
