---
name: delete
description: Use when deleting files or directories. Picks the right tool per platform - PowerShell on Windows, Bash rm on Unix/Mac.
---

# /delete

> Delete files or directories using the correct tool for the current platform.

## Rules

**Windows:** Use the `PowerShell` tool with `Remove-Item`.
- `Remove-Item` is a PowerShell cmdlet, not a bash command - calling it via the `Bash` tool exits 127.
- Git Bash's `rm` does actually work on Windows, but prefer PowerShell for deletion here anyway, for consistency.

**Mac / Linux:** Use the `Bash` tool with `rm`.

## Quick Reference

| Platform | Tool | Command |
|----------|------|---------|
| Windows | PowerShell | `Remove-Item "C:\path\to\file"` |
| Windows (recursive) | PowerShell | `Remove-Item "C:\path\to\dir" -Recurse -Force` |
| Mac / Linux | Bash | `rm /path/to/file` |
| Mac / Linux (recursive) | Bash | `rm -rf /path/to/dir` |

## Common Mistakes

- Using `Bash(Remove-Item ...)` on Windows - will always fail with exit 127.
- Using `PowerShell(rm ...)` on Mac - unnecessary; `rm` belongs in Bash there.
