<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# reachability.mjs counts an indexed file as an orphan when its link text contains brackets

**Type:** bug
**Origin:** ai

## Goal

`skills/cleanup-memory/reachability.mjs` reports `orphan-file` for memory files that DO have a
direct link inside MEMORY.md's loaded window, when the link's TEXT contains square brackets. Fix
the link parser so a bracketed label does not produce a false orphan.

## Reproduction

Confirmed 2026-09-28 against
`C:\Users\tecno\.claude-personal\projects\c--Users-tecno-Desktop-Projects-claude-usage-in-taskbar\memory`.

After a full `/cleanup-memory` pass the script reported:

```
[authoritative] loaded-window, direct-link-only:
  orphan-file: 2
    ...memory\project_cargo_build_hides_test_code.md
    ...memory\project_hidden_attr_beaten_by_author_display_rule.md
  orphan-index-entry: 0
```

Both files are in fact linked from MEMORY.md, verified with a plain
`grep -q "<stem>.md" MEMORY.md` on each (both matched). Their index lines are:

```
- [cargo build hides #[cfg(test)]](project_cargo_build_hides_test_code.md) - use `--all-targets`
- ... [an author display: rule beats [hidden]](project_hidden_attr_beaten_by_author_display_rule.md) - gate it with :not([hidden]); check base classes
```

The common factor is a `[` inside the link LABEL (`#[cfg(test)]`, `[hidden]`), which a
non-greedy `\[([^\]]*)\]\(([^)]+)\)`-style match terminates early on, so the `](path)` pair is
never associated with a label and the link is not counted.

Note this is the reading the skill designates authoritative, and all three of the script's
readings agreed on the same 2 files, so a user cannot dismiss it by cross-checking the other two.

## Why it matters

The script exists specifically because hand-counting this produced five different numbers in one
session, so its output is trusted without re-verification. A false `orphan-file` invites the exact
wrong fix: `/cleanup-memory` Step 6 says "for each `orphan-file`: add a `MEMORY.md` line pointing
to it", which would create a DUPLICATE index line for an already-indexed file. In an index that
has just been trimmed to fit under a hard byte cap, duplicate lines also consume the headroom the
trim bought.

## Approach

In `reachability.mjs`, match markdown links with a label pattern that tolerates balanced nested
brackets, or parse right-to-left from `](` back to the matching `[`. Do not simply switch to a
greedy label match, which would swallow two adjacent links on the same bundled line into one (the
index is full of lines carrying 5-12 links).

## Acceptance

- A fixture line containing `- [cargo build hides #[cfg(test)]](x.md) - hook` counts `x.md` as
  reachable.
- A fixture line containing two links where the first label has brackets still counts BOTH.
- Re-running against the claude_usage_in_taskbar memory dir reports `orphan-file: 0` for these two
  files (subject to that corpus not changing).
