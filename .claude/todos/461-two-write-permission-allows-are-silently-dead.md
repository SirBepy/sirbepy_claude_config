<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=3, reconfirm-count=3, content-hash=386688a6 -->
<!-- duplicate-checked -->
# Two `Write(...)` entries in settings.json are dead, and the harness says so out loud

**Type:** task
**Origin:** ai

## Goal

Delete the two dead `Write(...)` permission allows in `settings.json`, and decide whether the
harness's own warning about them is worth surfacing anywhere it would actually be read.

## Context

Found 2026-08-20 while validating the nested-`claude -p` hook-verification harness for phase 2 of
the harvest plan. The nested session printed this on startup, before doing any work, twice:

```
Permission allow rule (C:\Users\tecno\.claude-fibo\settings.json):
Write(C:/Users/tecno/Desktop/Projects/Web/video-script-assistant/**) is not matched by file
permission checks - only Edit(path) rules are. Use
Edit(C:/Users/tecno/Desktop/Projects/Web/video-script-assistant/**) instead (Edit rules cover all
file-editing tools).

Permission allow rule (C:\Users\tecno\.claude-fibo\settings.json):
Write(C:/Users/tecno/.claude/skills/**) is not matched by file permission checks - only Edit(path)
rules are. Use Edit(C:/Users/tecno/.claude/skills/**) instead (Edit rules cover all file-editing
tools).
```

So `Write(<path>)` is not a thing: `Edit(<path>)` is the rule form that covers every file-editing
tool, `Write` included. Both offending entries are in `settings.json`'s `permissions.allow`:

- `Write(C:/Users/tecno/Desktop/Projects/Web/video-script-assistant/**)`
- `Write(C:/Users/tecno/.claude/skills/**)`

**Both are pure dead weight, not a missing grant.** The `Edit(...)` equivalent for each path is
already present in the same list, immediately above it in both cases, so deleting the `Write(...)`
line changes no effective permission. That is what makes this a cleanup rather than a fix.

Two things make it worth a todo instead of a shrug:

1. **The warning is only visible on a fresh session start.** It scrolled past in a nested headless
   run and would be equally easy to miss in a normal launch, which is how two dead entries survived
   long enough to be found by accident.
2. **Same silent-pass family as todos 412 and 460.** A permission entry that matches nothing looks
   identical to one that grants something. Anyone auditing this list by reading it would count both
   `Write(...)` lines as live grants and conclude the skills tree is writable by explicit policy,
   when the actual grant comes from the `Edit(...)` line next to it.

## Approach

1. Confirm the warning still fires before changing anything: run `claude -p` from a scratch cwd and
   look for the two `Permission allow rule` lines. Do not fix on the strength of this file alone.
2. Delete both `Write(...)` entries from `settings.json`'s `permissions.allow`. Verify the paired
   `Edit(...)` entry for each path is present first, in the same read, so the delete cannot remove
   the only grant for a path.
3. Re-run the nested `claude -p` and confirm both warning lines are gone and nothing else appeared.
4. Sweep the rest of the list for the same shape while there: any other `Write(...)` entry, and any
   entry whose tool name is not one the harness matches. `settings.local.json` needs the same pass;
   Claude Code appends "always allow" grants there automatically, so it can grow a dead entry
   without anyone typing one.

## Acceptance

- Both `Write(...)` entries are gone from `settings.json`.
- A nested `claude -p` from a scratch cwd prints neither warning, proven by pasted output.
- No effective permission changed: the `Edit(...)` grant for each of the two paths is still present.
- `python ci/run_all.py` still exits 0.

## Notes

Do not "fix" this by converting `Write(...)` to `Edit(...)`. That would create a duplicate of an
entry that already exists. The correct edit is a deletion.

Worth considering as a follow-up rather than folding in here: nothing mechanically checks this list
for entries the harness will ignore. `ci/run_all.py` validates skill frontmatter and gates
`CLAUDE.md`'s token weight, so a `settings.json` permission-entry linter would fit the same slot.
That is a bigger idea than this cleanup and should be judged on its own, not smuggled in.
