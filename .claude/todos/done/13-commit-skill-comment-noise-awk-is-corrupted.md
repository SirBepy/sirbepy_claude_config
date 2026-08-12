<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=08cfc85e -->
# /commit's comment-noise prefilter command is corrupted and cannot run as written

**Type:** skill-fix

## Goal

Repair the step 5a shell command in `~/.claude-personal/skills/commit/SKILL.md` so it executes as
written, instead of every session having to notice it is broken and hand-rewrite it.

## Context

Step 5a of `/commit` is a mandatory, no-skip comment-noise check. The command it tells you to run
contains at least two placeholder-substitution artifacts that make it invalid:

```
| awk 'the=="??"{print substr(Fold,4)}' | while IFS= read -r f; do ...
/^\+\+\+ b\// { f=substr(Fold,7); run=0; next }
/^\+/ && !/^\+\+\+/ {
  l=substr(Fold,2); add[f]++
```

`the=="??"` should be `$1=="??"`, and every `Fold` should be `$0`. It reads as though `$1` and `$0`
were mangled by a find-and-replace at some point (`$0` -> `Fold`, `$1` -> `the`).

Consequence: the awk either errors or silently matches nothing, so the check reports clean on every
diff regardless of how many comment lines were added. A skill step that always passes is worse than
no step, because it looks like enforcement. Hit on 2026-08-07 in `zng-app`, where the command had to
be rewritten by hand before it produced any output at all.

`comment-noise.md` in the same folder is described as the single source of truth for the cap number
and for `/create-pr`'s range-mode variant, so check whether the same corruption exists there and in
`/create-pr` step 2b before assuming this is one isolated copy.

## Approach

1. Read `~/.claude-personal/skills/commit/SKILL.md` step 5a, `~/.claude-personal/skills/commit/comment-noise.md`,
   and `/create-pr` step 2b. Identify every corrupted copy.
2. Restore `$0` and `$1`. A working equivalent, verified 2026-08-07:

   ```
   git diff HEAD -- <files> | awk '
   /^\+\+\+ b\// { f=substr($0,7); run=0; next }
   /^\+/ && !/^\+\+\+/ {
     l=substr($0,2); add[f]++
     if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
     next
   }
   { run=0 }
   END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }'
   ```

   Note the untracked-file half of the original (the `git status --porcelain` + `git diff --no-index`
   loop) also needs its `$1`/`$0` restored; do not drop it, it is what makes new files visible.
3. **Prove it bites before believing it.** Run it against a diff with a deliberately long comment
   block and confirm it flags; then against a clean diff and confirm silence. A prefilter nobody has
   watched fire is exactly the failure this todo is about.
4. Consider moving the command into a script file the skill calls, so quoting/substitution cannot
   corrupt it again.

## Acceptance

- The command in `SKILL.md` runs verbatim, copy-pasted, with no hand-editing.
- It flags a diff containing a 6-line comment block, and stays silent on a clean one, both observed.
- Any other corrupted copies (`comment-noise.md`, `/create-pr`) are fixed in the same pass.

## Notes

Found during a `/commit` run in `zng-app` on 2026-08-07. Filed here rather than in the project backlog
because it changes the global `~/.claude-personal/skills/` tree.
- Skipped by /auto-do-todos 2026-08-08: already fixed upstream. commit/SKILL.md step 5a and commit/comment-noise.md both carry the correct awk (substr(\,7), \==??), not the Fold/the corruption this todo described. Note todo 45 covers a distinct, still-open mechanism (harness arg-substitution clobbering \ at invocation time) and is NOT closed by this.
