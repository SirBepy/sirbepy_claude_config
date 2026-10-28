<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# comment-noise.sh counts CSS custom properties as comment lines

**Type:** bug
**Origin:** ai

## Goal

`skills/commit/comment-noise.sh` flags any new CSS file that declares more than four custom
properties, because its comment pattern treats a leading `--` as a comment marker.

## Context

Found 2026-08-31 while committing a stylesheet split in the `countoff` project.

The awk rule at `skills/commit/comment-noise.sh:22` is:

```
if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; ... }
```

The `--` alternative is there for SQL, Lua and Haskell line comments. In CSS it also matches every
custom-property declaration, since those are spelled `--name: value`.

Measured on `countoff`'s `src/styles/base.css`: the script reported `30/237 (12%) longest 18`. The
file actually contains **5** comment lines. The other 25 hits are the `:root` token block, and the
"18-line comment block" that trips the hard cap is `--bg` through `--rail`, 18 consecutive colour and
sizing tokens.

This is not a rare shape. Any design-token file, any `:root` block, any theme file with more than
four variables trips the `max>=5` hard cap, so the gate exits 1 on a file with no comments in it at
all. `/commit` step 8 tells the caller to chain the gate with `&&` before `git commit`, so a
false positive here structurally blocks the commit and pushes the caller into either gutting real
comments or documenting an override by hand.

## Approach

Gate the `--` alternative on file extension, the same way `.md`/`.mdx` are already excluded a few
lines above and generated suffixes are excluded below it. Something like: only treat `--` as a
comment marker when `f` is not `.css`, `.scss`, `.less` or `.sass`.

A narrower alternative, if `--` should keep working inside CSS-in-JS: require the `--` to be followed
by a space or end of line, since a CSS custom property is always `--name:` with no space. That fixes
the CSS case without an extension list, but it would stop matching `--`-with-no-space comments in the
languages the rule was written for, so check those first.

## Acceptance

- A CSS file consisting of a `:root` block with 20+ custom properties and no comments reports nothing.
- SQL, Lua and Haskell comment blocks are still caught, verified with a fixture of each.
- `bash ci/run_all.py` (or the repo's own check runner) still passes.

## Notes

The same pattern is read by `/create-pr`'s comment-noise check, so fixing the script fixes both
callers at once. Nothing else needs to change.
- Duplicate of 779 - resolved by 779's fix in commit aa4b27c during /mega-todos batch 3, 2026-08-31. Both describe the same comment-noise.sh classifier defect: 779 covers the bare-* Rust deref case and the -- CSS custom-property case together, 848 covers the CSS half alone. 779's builder was given 848's acceptance block and satisfied both, including weighing 848's narrower space-requirement alternative and rejecting it because SQL, Lua and Haskell use no-space -- comments. Filed independently by a concurrent session that did not know 779 existed.
