<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "tokenize", "hooklib", "shlex". 873 and 874 are the two
     sibling hooklib-extraction todos; neither covers tokenize. done/813 is the same shape in bash. -->
# `tokenize` is defined four times across the shell guards, in two incompatible families

**Type:** task
**Origin:** ai

## Goal

Decide whether shell-command tokenization belongs in `hooks/_hooklib.py`, and if so which of the two
existing behaviours becomes the shared one, so a fifth guard does not invent a third variant.

## Context

Surfaced 2026-09-02 by `/code-check`'s independent reviewer over the batch-3 `/mega-todos` diff. The
reviewer found two copies and classified it mechanical; the orchestrator then grepped
`def tokenize` across `hooks/` and found **four**, in two families that do NOT behave the same. That
is what moves this from a collapse to a decision.

**Family A** - `hooks/dev-server-guard.py:39` and `hooks/package-manager-guard.py:51`. Byte-identical
bodies, only the comment wording differs:

```python
return [_lib_strip_quotes(t) for t in shlex.split(command, posix=False)]
except ValueError:
    return command.split()
```

**Family B** - `hooks/dev-backend-guard.py:110` and `hooks/flutter-workdir-guard.py:87`. Both use
`flatten_tokens` rather than `strip_quotes`, and their `ValueError` fallbacks disagree with each
other:

- `dev-backend-guard.py` falls back to `re.split(r"\s+", segment)`
- `flutter-workdir-guard.py` falls back to `[]`

So there are four definitions, two token-cleaning helpers, and **three different answers to "what
happens when `shlex` raises"**. All four take the same `posix=False` decision for the same stated
reason (Windows backslashes survive), which is the part that is genuinely shared.

**Why the fallback divergence is the real question, not a detail.** These are all PreToolUse guards.
A `ValueError` from `shlex` means the command has unbalanced quotes - which is exactly the shape a
caller would use to smuggle something past a token-based check. Returning `[]` makes the guard see
an empty command and pass; returning a whitespace split makes it see something. Whether that
difference is deliberate per guard or accidental drift has to be answered before anything is merged,
because merging the wrong way silently changes what each guard does on malformed input.

**Not urgent.** Nothing is broken; `python ci/run_all.py` is green at 24/24 hook suites. This is
drift that has now reached four copies, which is the same count that made `done/813` worth doing for
`git_c`.

## Approach

1. **Answer the fallback question first, per guard, before writing any shared code.** For each of the
   four, work out what its `ValueError` branch means for that guard's decision, and whether an
   unbalanced-quote command should be treated as "nothing to see" or "suspicious". Record the answer
   even if the conclusion is that all four should keep their own.
2. If a shared helper is right, it belongs in `hooks/_hooklib.py`, which all four already import from.
   **That file is imported by 21 guards** (`ci/run_all.py`'s hook-import smoke check counts them), so
   treat a change there as its own unit of work, not a drive-by inside another todo.
3. Decide whether `strip_quotes` and `flatten_tokens` should also converge, or whether the two
   families are genuinely different jobs. Do not assume convergence just because the `shlex` call
   matches.
4. Coordinate with `873` (turn-boundary helpers duplicated across two hooks) and `874` (git-root
   resolution reimplemented in two guards). All three are the same class of `_hooklib` extraction
   question, and doing them as three separate hub-file edits is worse than doing them as one
   considered pass. Check both before starting.

## Acceptance

- The `ValueError` fallback semantics are stated per guard, with the reasoning, in writing.
- If extracted: one definition, and each of the four guards behaves identically before and after on
  a well-formed command AND on an unbalanced-quote command. Prove the second case explicitly, it is
  the one that differs today.
- If NOT extracted: the decision and its reasoning live in `hooks/_hooklib.py` or a sibling doc so
  this stops being re-filed.
- `python ci/run_all.py` exits 0, including the hook-import smoke check over every `_hooklib`
  importer.

## Notes

- Worth roughly a 5. Real four-way duplication with a genuine behavioural fork buried in it, on
  security-adjacent guards, but nothing is broken today.
- Filed as class 3 (judgment) rather than the reviewer's class 2, specifically because the two
  families disagree on malformed input. A class-2 "collapse the duplicate" treatment would have
  picked one fallback and silently changed two guards.
