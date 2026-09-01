<!-- Claim before executing: .claude/todos/.claims/845.claim per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=1, content-hash=bc8ddee5 -->
<!-- duplicate-checked -->
# shell-content-write-guard missed a `>` redirect it blocked moments later

**Type:** skill-improvement
**Origin:** ai

## Goal
`hooks/shell-content-write-guard.py` should block a `>` file-content redirect
consistently, regardless of how quote characters are arranged earlier in the same
command. Right now a command can slip through, and the same redirect to the same
path is then blocked on the next attempt.

## Context
Observed 2026-08-31 in a `claude_usage_in_taskbar` session.

**Call 1 - NOT blocked, file was written.** Roughly (paths shortened):

```
sed -e 's|const AUQ_ANSWER_SENTINEL = "<auq-answer/>";|const AUQ_ANSWER_SENTINEL = "<auq-answer";|' \
    -e 's|foldText: A|foldText: B|' \
    e2e/view-harness/auq-extra-message-single-send.view.spec.ts \
    > e2e/view-harness/zz-scratch-diag.view.spec.ts \
  && sed -i 's|X|Y|' e2e/view-harness/zz-scratch-diag.view.spec.ts \
  && pnpm exec playwright test e2e/view-harness/zz-scratch-diag.view.spec.ts
```

It ran. Proof the file was created with content: playwright then reported
`SyntaxError: ... zz-scratch-diag.view.spec.ts: Unterminated regular expression. (97:93)`
and echoed lines 95-100 of it.

**Call 2 - blocked.** Same `>` operator, same destination path, differing mainly in
the quote characters in the preceding `sed` expressions:

```
rm -f e2e/view-harness/zz-scratch-diag.view.spec.ts \
  && sed -e 's|const AUQ_ANSWER_SENTINEL = "<auq-answer/>";|const AUQ_ANSWER_SENTINEL = "<auq-answer";|' \
       -e 's|foldText: A|foldText: B|' src.ts \
       > e2e/view-harness/zz-scratch-diag.view.spec.ts \
  && grep -n ... && pnpm exec playwright test ...
```

Denial text: ``  `>` redirect writes file content to
`e2e/view-harness/zz-scratch-diag.view.spec.ts` through the shell. ``

So the guard's protection is order/parity dependent, not content dependent. That is
the bad direction of inconsistency: it fails OPEN silently, on a normal successful
parse, with no error printed. The module docstring only promises "Fails open on
error" - this is not an error path.

## Suspected cause - NOT yet confirmed, verify before fixing
`mask_quoted()` (around line 76) masks in this order:

```python
masked = HERESTRING_RE.sub("QSTR", command)
masked = dquote_re.sub("QSTR", masked)   # double quotes FIRST
masked = SQUOTE_RE.sub("QSTR", masked)   # single quotes second
```

Double-quote masking running before single-quote masking means `"` characters that
live INSIDE single-quoted `sed` expressions get paired with each other across the
single-quote boundaries. A span that happens to include the real `>` operator can
then be masked away as if it were string content.

Supporting observation, not proof: while trying to test this, a command embedding the
call-1 string was itself blocked, and the denial named the target as
``QSTR<auq-answerQSTRQSTR`` - visibly a mangled mask, not a real path. So quote
pairing does cross single-quoted regions. Whether that is the exact reason call 1
passed is still unverified.

## Approach
1. Reproduce both command strings against `find_violation()` directly. **Note the
   testing trap:** an inline heredoc containing these strings gets intercepted by this
   very hook, so the test cannot be typed inline. Put the two strings in a `.py` file
   (written with the Write tool) that imports the hook via `importlib` and prints
   `find_violation(cmd)` and `mask_quoted(cmd, DQUOTE_RE)` for each.
2. Confirm or reject the ordering hypothesis by comparing the two masked strings.
   If confirmed, the likely fix is masking single-quoted regions BEFORE double-quoted
   ones, or doing a single left-to-right scan that respects whichever quote opens
   first, rather than two independent regex passes.
3. Add both command strings to whatever self-test file covers this hook
   (`hooks/test_*.py`) so the regression is pinned.
4. Re-run `python ci/run_all.py` - it composes the hook self-tests.

Do NOT "fix" this by broadening the redirect regex until the masking question is
settled; a guard that over-blocks legitimate `2>&1` style commands is its own problem,
and line 114 already special-cases fd duplication.

## Done when
- Both call-1 and call-2 strings return a violation from `find_violation()`.
- A self-test pins them.
- `python ci/run_all.py` passes.

## Notes
**Opposite direction from todo 476** (`shell-write-guard fires on a greater-than
inside a heredoc`), which is a false POSITIVE. This one is a false NEGATIVE. Same
hook, and both trace to how the raw command string is masked before operators are
matched, so whoever fixes either should read both - but a fix aimed only at
over-blocking will not touch this, and a fix aimed only at under-blocking risks
making 476 worse.

Filed from a project session per global CLAUDE.md ("spotting the problem, filing the
todo in the `~/.claude` backlog... are fine"); no global files were edited there.

Context on why it mattered: the two calls were an attempt to generate a throwaway
diagnostic spec via `sed`, which the global "never write file CONTENT through the
shell" rule forbids outright. The guard is the enforcement for that rule, so a silent
miss means the rule is only advisory in exactly the case where someone has already
drifted from it.
- Done via /mega-todos 2026-09-01 (0caf60f): mask_quoted now masks heredoc, double-quote and single-quote spans in one left-to-right pass, so an odd quote count can no longer swallow a real redirect. Also landed 476 shared-invariant items.
