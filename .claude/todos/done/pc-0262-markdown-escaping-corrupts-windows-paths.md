<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=9, reconfirm-count=2, content-hash=8a1aa0c5 -->
# Blockquote copy-paste rule silently corrupts every Windows path with a dot-directory

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop Claude from sending Joe broken Windows paths. Amend
`~/.claude/refs/copy-paste-format.md` (and the `CLAUDE.md` Communication bullet
that points at it) so that anything containing a backslash goes in a **code
block**, never a bare blockquote.

## Context

Reported by Joe on 2026-08-12, in a revaire-mobile session, with the words
*"this is an issue that happens quite often actually... i hate this and it
happens so often."* He has been receiving paths like:

```
C:\Users\tecno\Desktop\Projects\revaire-mobile.for_bepy\aab\...
```

when the intended path was:

```
C:\Users\tecno\Desktop\Projects\revaire-mobile\.for_bepy\aab\...
```

### Root cause â€” confirmed, not a guess

Markdown (CommonMark/GFM) treats a backslash before any **ASCII punctuation**
character as an escape and consumes the backslash. Everything else is left
alone. So in a raw-markdown context:

| Sequence | Next char | Renders as | Result |
|---|---|---|---|
| `\U`, `\t`, `\D`, `\a` | letter | `\U`, `\t`, â€¦ | separator survives |
| `\.` | punctuation | `.` | **separator eaten** |
| `\_`, `\-`, `\(`, `\#` | punctuation | `_`, `-`, â€¦ | **separator eaten** |
| `\\` | punctuation | `\` | UNC `\\server` â†’ `\server` |

That is why exactly one backslash vanishes and it is always the one before a
dot-directory. It is not intermittent and it is not the app misbehaving.

### Why it recurs constantly

Joe's environment is saturated with dot-directories: `.for_bepy`, `.claude`,
`.cursor`, `.git`, `.env`, `.vscode`, `.portfolio-data`, `.claims`. Every path
naming one is corrupted on render.

### Why the current rules cause it rather than prevent it

`~/.claude/refs/copy-paste-format.md` mandates that copy-paste content go in a
**blockquote**, justified by the claim that inline backticks and fenced code
blocks "don't render distinctly in the app." A blockquote is raw markdown, so it
escapes. The rule that exists to make copy-paste reliable is precisely what
breaks it.

Meanwhile the Conductor system prompt separately requires **full absolute paths**
in all user-visible text, so the collision is guaranteed, not incidental.

## Approach

1. Edit `~/.claude/refs/copy-paste-format.md`. Add a rule that **overrides** the
   blockquote default whenever the content contains a backslash:
   - Copy-paste content with a backslash â†’ **fenced code block**.
   - A path named in prose â†’ **inline code**.
   - Blockquotes remain the default only for backslash-free copy content.
   State the reason inline (markdown escapes `\` + punctuation) so a future
   session does not "simplify" the rule back to blockquotes-always.
2. Update the `CLAUDE.md` Communication bullet that summarises the copy-paste
   ruleset so the exception is visible without opening the ref file.
3. Consider whether the "backticks don't render distinctly" premise is still
   true in Conductor. Joe confirmed the chosen convention on 2026-08-12, so
   correctness already won this tradeoff, but if code blocks do render
   distinctly the ref file's justification is simply stale and should be
   rewritten rather than patched.
4. Optional, only if it proves cheap: a `Stop`-hook style check that flags a
   user-visible message containing `\` followed by punctuation outside a code
   span. Do not build this speculatively; the rule change is the fix.

## Acceptance

- `copy-paste-format.md` states the backslash â†’ code-block exception explicitly,
  with the escaping reason.
- The `CLAUDE.md` Communication bullet reflects it.
- A path like `C:\Users\tecno\.claude\todos\PLAN.md` sent under the new rule
  arrives with every separator intact.
- Must not regress: backslash-free copy-paste content (commands, prose, Croatian
  message drafts) still uses blockquotes, which is the whole point of the
  existing rule and remains correct.

## Notes

### Decision already made â€” do not re-litigate

Joe was offered four conventions on 2026-08-12 and chose **"code blocks for
anything with backslashes"** over forward slashes, doubled backslashes, and a
nested blockquote+code hybrid. Rejected and why:

- **Forward slashes** (`C:/Users/...`) â€” renders fine anywhere and Windows,
  PowerShell and Explorer accept it, but `cmd.exe` and some CLIs choke, so it
  fails when pasted somewhere unexpected.
- **Doubled backslashes** (`C:\\Users\\...`) â€” renders correctly but the raw
  message text is wrong, so anything reading the source rather than the render
  gets a corrupt path.
- **Blockquote wrapping a code block** â€” correct and most distinct, but verbose,
  and nested rendering is not guaranteed in this app.

### Scope note

This is a global-tooling fix. It was surfaced from a revaire-mobile session and
filed here per the rule that `~/.claude` findings belong in the `~/.claude`
backlog. Joe authorised filing the todo, **not** editing the global rules from
that session, so the edit itself is still pending and belongs to a `~/.claude`
session.
- completed, commit 39029b7
