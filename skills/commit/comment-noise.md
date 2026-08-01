# Comment-noise check

Shared by `/commit` (step 5a) and `/create-pr` (drafting subagent, step 2).
Read on demand - not part of either skill's always-loaded body.

The cap: **2 lines typical, 4 lines hard, per comment block**, and added comment
lines under **~25%** of a file's added lines once that file adds 20+ lines (below
that the ratio is noise - a 5-line constants file with one 2-line why-comment is
fine, and the block cap already covers it). Matches the global CLAUDE.md Code
Style rule; if a number changes, change it in both. A block earns its place ONLY
by naming a constraint, a gotcha, or a measurement the code cannot show.
Restating the next line, narrating steps, labelling JSX sections, or parking
design rationale in code all fail; rationale goes in the PR body.

1. **Mechanical prefilter** (one command, no judgment, run it verbatim):

   ```
   git diff <base>..HEAD | awk '
   /^\+\+\+ b\// { f=substr($0,7); run=0; next }
   /^\+/ && !/^\+\+\+/ {
     l=substr($0,2); add[f]++
     if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#|--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
     next
   }
   { run=0 }
   END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }' | sort
   ```

   Swap `<base>..HEAD` for `HEAD -- <files>` when scoping to a not-yet-committed
   diff (`/commit`'s step 5a). No output = `clean`, and the check is done. Do
   not read a single comment.
2. **Judge only the flagged files.** Read those diffs and list the specific
   offending blocks (`file:line`, first line, line count). A 5+ line block that
   genuinely documents one hard constraint can survive - say so and why. Do not
   review comments in files the prefilter didn't flag; they are in budget.
