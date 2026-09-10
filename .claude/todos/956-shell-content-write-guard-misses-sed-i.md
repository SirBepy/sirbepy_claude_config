<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=63d8bcbb -->
<!-- duplicate-checked: grepped the live backlog and done/ for "shell-content-write-guard", "sed -i" and "in-place" - no existing entry covers the in-place-editor family. -->
# shell-content-write-guard misses `sed -i` and the other in-place editors

**Type:** skill-improvement
**Origin:** ai

## Goal

`hooks/shell-content-write-guard.py` blocks in-place file editors the same way it already blocks
`Set-Content` / `Out-File` / redirects, so the global "never write file CONTENT through the shell"
rule is enforced by the hook rather than by the model remembering it.

## Context

Global `CLAUDE.md`, Shell Commands section, states the rule the hook exists to enforce:

> Never write file CONTENT through the shell - not `Set-Content`, not `Out-File`, not `>`/`>>`.
> Use the `Write` tool [...] This is a hard ban on the mechanism, not an encoding nudge [...]
> This ban overrides any harness/auto-mode preamble telling Claude to write via shell;
> `cat`/`sed`/`grep` reads and a `python`/`node` heredoc opening it stay allowed.

Note the carve-out is for `sed` **reads**. An in-place `sed -i` is a write, and the hook does not
see it. Read 2026-09-05, `hooks/shell-content-write-guard.py:51-82`: the pattern set is
`CONTENT_CMDLET_RE` (`Set-Content|Out-File|Add-Content`), `TEE_RE`, `REDIRECT_RE`, `HEREDOC_RE`,
`HERESTRING_RE` and `IEX_RE`. Nothing matches `sed -i`, `perl -pi`, `python -c "...write..."`, or
`ed`.

Reproduced 2026-09-05 in `claude_usage_in_taskbar`: a session running under an auto-mode preamble
that explicitly instructs "make file changes with sed" used `sed -i 's/.../.../'` to edit
`src/views/sessions/session-statusbar.ts`, a tracked source file. The hook did not fire. The edit
happened to be correct, so nothing broke - which is the problem: the guard's silence reads as
permission, and the auto-mode preamble is actively pushing every session toward this exact call.

## Approach

1. Add an `INPLACE_EDIT_RE` next to `CONTENT_CMDLET_RE` covering at minimum `sed` with `-i`
   (including `-i.bak` and the `-i ''` BSD form), `perl` with `-i`, and `ed`. Keep bare `sed`
   without `-i` allowed - that is the documented read carve-out and is used constantly.
2. Follow the file's existing quote-masking approach so a `sed -i` appearing inside a quoted string
   argument to something else is handled the same way `CONTENT_CMDLET_RE` hits already are.
3. Decide deliberately whether a path proven OUTSIDE any repo is exempt, matching whatever the
   existing `is_outside_repo`-style logic in the file already does for redirects, rather than
   inventing a second policy.
4. Add cases to `hooks/test_shell_content_write_guard.py` for: `sed -i` blocked, `sed -i.bak`
   blocked, `perl -pi -e` blocked, plain `sed -n '1,50p' file` still ALLOWED (regression guard for
   the read carve-out), and `grep`/`cat` still allowed.

## Acceptance

- `python hooks/test_shell_content_write_guard.py` passes, including the new cases.
- `python ci/run_all.py` green.
- A manual `sed -i 's/a/b/' <some tracked file>` is rejected with a message naming the `Write` tool.
- A manual `sed -n '1,20p' <file>` still runs.

## Notes

The auto-mode preamble that tells sessions to edit with `sed` is a separate surface and is NOT in
scope here - global `CLAUDE.md` already says the ban overrides it. This todo only closes the
mechanical gap so the override does not depend on the model noticing the conflict.
