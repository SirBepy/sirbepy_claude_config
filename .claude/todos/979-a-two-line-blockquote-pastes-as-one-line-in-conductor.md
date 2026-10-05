<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# A two-line blockquote pastes as one line in Conductor

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `refs/copy-paste-format.md`'s "Sequential commands" advice from producing a broken paste:
two commands on two lines inside one blockquote reach Joe's shell as ONE line.

## Context

2026-09-10, countoff session. Claude gave Joe this, exactly as the ref recommends for commands
meant to run together:

```
> gcloud auth login
> gsutil cors set cors.json gs://generic-sirbepy-project.firebasestorage.app
```

What he pasted into PowerShell (his own transcript, verbatim):

```
gcloud auth login gsutil cors set cors.json gs://generic-sirbepy-project.firebasestorage.app
ERROR: (gcloud.auth.login) unrecognized arguments: cors set cors.json gs://...
```

This is standard markdown, not a Conductor bug: a single newline inside a blockquote paragraph is
a soft line break and renders as a space, so the two lines are one paragraph and copy as one line.
The ref's `flutter clean && flutter pub get && flutter run` example works only because it is
already one line joined with `&&`.

`refs/copy-paste-format.md` "Sequential commands" currently reads: "Multiple commands meant to run
together can be batched in one blockquote" and shows the `&&` form. It never says that separate
LINES will collapse, and the "Placeholders" and "Language matching" sections give no hint either.

## Approach

- In `refs/copy-paste-format.md` "Sequential commands": state that a blockquote is ONE paragraph
  and lines inside it collapse to spaces. Batching in one blockquote is fine only when the
  commands are joined on a single line (`&&`, `;`). Two commands that must stay separate lines
  (an interactive login followed by a second command, anything that cannot be chained) go in a
  fenced code block instead, one command per line, the same escape the Windows-path gotcha
  already uses.
- Mirror the one-line rule into root `CLAUDE.md`'s "Copy-paste for Joe" bullet, since that bullet
  is what loads every session and the ref is only read once.
- Optional: extend `hooks/` if there is an existing outbound-format guard that could flag a
  blockquote containing more than one line without `&&`/`;`. Only if such a hook already exists;
  do not add a new hook for this alone.

## Acceptance

- The ref and the root bullet both say lines inside a blockquote collapse, and name the fenced
  code block as the multi-line escape.
- `python ci/run_all.py` still passes (token budget included).
