<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# /create-pr's preview-file format leaks "## Title"/"## Body" scaffolding into the real PR body

**Type:** skill-improvement

## Goal

Stop `gh pr create --body-file <preview-file>` from shipping the preview file's own `## Title` /
`## Body` section headers as literal content in the actual GitHub PR body.

## Context

2026-08-03, PR #215 (`frontend2` PWA standalone-shell branch): the drafting subagent wrote
`.for_bepy/pr_preview/pwa-standalone-shell.md` per `drafting-rules.md`'s template, which
apparently renders the preview as:

```
## Title

FEAT: ...

## Body

<actual body prose>
```

That's a reasonable shape for a human-readable preview rendered inline in chat (title + body
sections, clearly separated), but the main agent's step 5 then passed that SAME file straight to
`gh pr create --body-file`. Since `--title` is already supplied separately via its own flag, the
resulting PR body literally contained the redundant `## Title` / `FEAT: ...` / `## Body` headers
above the real prose â€” caught and fixed post-hoc with a manual `gh pr edit --body`.

The skill file is `C:\Users\tecno\.claude\skills\create-pr\SKILL.md` (step 4 renders the file
inline via `Read`, step 5 feeds the same file to `--body-file`); the actual template lives in
`C:\Users\tecno\.claude\skills\create-pr\drafting-rules.md` (not fully read this session â€” worth
confirming the exact wrapper structure it instructs the subagent to write, since this description
is inferred from the one instance observed).

## Approach

Pick one:
- Have the drafting subagent write the preview file as body-only content (no `## Title`/`## Body`
  wrapper), and have the main agent print `**Title:** <title>` itself when rendering the preview
  inline in chat, rather than relying on the file to carry a title section.
- Or, if `drafting-rules.md` deliberately wants a title+body wrapper for the chat-preview
  rendering, have step 5 strip everything through and including the `## Body` line before passing
  the remainder to `--body-file` (or write a second, body-only file specifically for `--body-file`
  and keep the wrapped one only for the inline chat render).

## Acceptance

- A `/create-pr` run's actual GitHub PR body contains only the intended prose â€” no `## Title`,
  repeated title line, or `## Body` header â€” verified by reading the created PR's body via
  `gh pr view <n> --json body`.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 203; renumbered to 42 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Premise falsified, closed by /auto-do-todos 2026-08-08. create-pr/SKILL.md step 2 now has the drafting subagent write the FINAL BODY only to the preview file (line 98), and the title travels separately via the subagent's return value and the cc-pr-title marker (line 163) into gh pr create --title. drafting-rules.md contains no Title/Body wrapper template at all. The scaffolding leak observed on PR #215 is unreachable under the current skill.
