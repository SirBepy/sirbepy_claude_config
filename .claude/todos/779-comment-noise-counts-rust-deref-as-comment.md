<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=87269acc -->
<!-- duplicate-checked -->
<!-- 778 is about the em-dash marker at commit time, 774/775 are code-check/stash scope. Searched
     backlog + done/ for "comment-noise", "awk", "prefilter", "false positive" - nothing covers the
     comment regex itself misclassifying a code line. -->
# comment-noise.sh counts a Rust deref-assignment line as a comment, inflating the block run

**Type:** bug
**Origin:** ai

## Goal

Stop `skills/commit/comment-noise.sh` from classifying a line whose first non-space character is
`*` as a comment when the file is not a C-style block-comment context, so a compliant 4-line comment
block above a Rust deref-assignment does not get reported as a 5-line one.

## Context

Hit for real on 2026-08-25 committing `src-tauri/src/ipc/window/mod.rs` in the
`claude_usage_in_taskbar` repo. The added block was:

```
+                        // Reset the paint-liveness baseline per window: otherwise
+                        // `last_frontend_raf` still holds its boot-time default and the
+                        // first `frontend_ping` reports `raf_tick: 0`, equal to it, so
+                        // the "tick changed" check skips and the watchdog misfires.
+                        *state.last_frontend_raf.lock().unwrap() = (0, std::time::Instant::now());
```

4 comment lines, exactly at the hard cap, and one line of code. The script reported
`src-tauri/src/ipc/window/mod.rs 5/5 (100%) longest 5` and the gate exited 1.

Cause is the awk classifier at `comment-noise.sh:19`:

```
if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; ... } else run=0
```

The bare `\*` alternative exists for continuation lines inside a `/* ... */` block. In Rust it also
matches every `*deref = value;` statement, and in C/C++ it would match `*ptr = x;` the same way.
Because the deref line directly follows the comment, `run` never resets, so `max` reaches 5 and
trips the `max[k]>=5` condition.

This is the bad kind of false positive: it fires exactly when a block is already AT the cap, and the
documented treatment ("if it prints anything, TRIM") pushes the committer to shorten a compliant
comment to satisfy a miscount. That is the failure mode
`~/.claude/memory` records as "subagents degrade the product to pass tooling", except here the
tooling induces it directly. In the incident above the comment was cut from 4 lines to 3 purely to
get a green gate, losing a real sentence for no reason.

## Second instance: `--` matches CSS custom properties

Hit 2026-08-26 committing the new `countoff` project. `src/styles.css` was reported as
`27/847 (3%) longest 18`, while the file has 7 real comments (`grep -c '/\*'`) and no comment block
over 3 lines. The run of 18 is lines 2-19 of `:root`:

```css
:root {
  --bg: #0d0f14;
  --bg-1: #141821;
  --bg-2: #1c2130;
```

The `--` alternative in the same alternation exists for SQL and Lua comments. A CSS custom property
declaration starts with exactly `--` after leading whitespace, so any design-token block of 5+
variables trips the `max[k]>=5` arm. Every themed stylesheet Joe writes has one.

Same shape as the Rust case, same line of the script, so both want fixing in one pass: the
alternation classifies by leading token with no notion of what language the file is.

## Approach

Options, cheapest first:

1. Require the `*` alternative to be followed by whitespace or end-of-line (`\*([[:space:]]|$)`).
   `* continuation text` still matches; `*state.foo = x;` and `*ptr = x;` no longer do. This is a
   one-character-class change and handles the common case.
2. Additionally track whether an unterminated `/*` is open and only honour the bare `*` form while
   inside one. More correct, more awk state.

Option 1 is probably enough - a leading `*` immediately followed by an identifier is essentially
never a comment continuation in practice.

3. For the `--` case, gate that alternative on file extension the way `#` is already gated for
   markdown: skip it when `f` ends in `.css`, `.scss`, `.less` or `.sass`. `--` is never a comment
   leader in any of them.

Worth a look at whether the remaining alternatives have the same blind spot now that `#`, `*` and
`--` all have.

## Acceptance

- The exact 5-line block quoted above (4 `//` lines + the `*state...` line) is NOT reported.
- A `:root` block of 18 CSS custom properties is NOT reported.
- A genuine 5-line `/* ... * ... */` block still IS reported.
- Add a regression case to whatever self-test covers this script; if none exists, note that in the
  commit so `ci/run_all.py` coverage can follow.

## Notes

Surfaced from a project session (`claude_usage_in_taskbar`), filed here because the target is the
global `~/.claude` tree. Not executed there, per global CLAUDE.md's rule about doing global work
from a project session.
