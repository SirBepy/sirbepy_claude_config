<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped .claude/todos/ and done/ for heredoc, backslash; 1203 is the write guard's pwsh quote mask and 1131 the guards' heredoc regex, a different mechanism each -->
# refs/shell-io-gotchas.md tells Claude a raw string in a heredoc keeps backslashes, but the Bash tool still loses one level

**Type:** skill-improvement
**Origin:** ai
**Summary:** The shell gotchas doc gives advice that holds in practice: never route literal-backslash file content through the Bash tool, even in a raw string.

## Why

Seen 2026-10-28: Python raw strings in a quoted heredoc still lost one backslash level, so the doc's raw-string advice failed.

## Goal

`refs/shell-io-gotchas.md` gives advice that holds in practice: do not route literal-backslash file content through the Bash tool at all, even with a quoted heredoc and a Python raw string.

## Context

Seen 2026-10-28 in claude_usage_in_taskbar (the "In-app file viewer" chat). Content went through the Bash tool as `python - <<'PYEOF'` with Python raw strings (`r'''...'''`):

- A raw string holding the JS regex `/\\/g` came out in the file as `/\/g`, checked with `python -c "print(ascii(...))"` on the written file.
- `[a-z]:[\\/]` came out as `[a-z]:[\/]`.
- `\uFEFF` inside the same raw string came out as a literal U+FEFF character.
- In a separate non-raw heredoc string, `"x\\n"` was meant to write the two characters `\n` but wrote a real newline.

So something before Python decoded one level of escapes, even though the heredoc delimiter was quoted and the strings were raw. The fix that worked was building backslashes with `chr(92)` in a `python -c` one-liner, or writing the content with the Write tool. Content written with the Write tool kept `\\` correctly, for example `/\\/g` in `src/shared/open-file.ts`.

Today, lines 61-64 of `refs/shell-io-gotchas.md` say "Write literal-backslash content with the Write or Edit tool, or with a raw string, never through a normal heredoc string." The raw-string half of that advice is what failed here.

## Approach

- Edit `C:\Users\tecno\.claude\refs\shell-io-gotchas.md` lines 61-64. Drop "or with a raw string" for content passed through the Bash tool. Say that the Bash tool can collapse `\\` to `\` and decode `\uXXXX` even inside a quoted heredoc. Keep the Write/Edit-tool advice, and add a `chr(92)` build or a patch script written with the Write tool and then run as the safe options.
- Before editing, reproduce once: from the Bash tool, run `python - <<'EOF'` with `open(p,'w').write(r'/\\/g')`, then inspect the file with `ascii()`. If it does not reproduce, record the conditions in Notes instead of changing the ref.

## Notes

None.
- Fixed in eab8c38.
