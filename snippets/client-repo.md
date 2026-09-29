# Client-repo policy

Client work is tested harder than personal work, because a regression there lands on someone else's product and on Joe's reputation with them.

## Which repos this covers

A repo is a **client repo** when it has a remote and `origin` is NOT under `github.com/SirBepy/`. That is the same owner check `/commit` step 8 and `hooks/gh-account-switch.sh` already use, so client repos need nothing added to their own files: detection is mechanical, never a guess about who owns the code, and no marker ever goes into a client repo's `CLAUDE.md`.

No remote, or `origin` under `SirBepy`: personal, this file does not apply.

## What changes in a client repo

1. **Every behaviour change ships with a test that fails without it.** Write the test alongside the change, not after. A change that cannot be tested by Claude (native UI, hardware, visual judgement) says so explicitly in the commit report instead of shipping silently untested.
2. **Before every commit:** `/commit` step 6b runs `/test` (the full fast floor: unit, typecheck, lint, build) and `/code-check` on the commit's own diff. A `/code-check` finding about the change itself gets fixed before the commit lands; a finding about older, untouched code goes to the backlog as usual.
3. **Before every push:** `/commit`'s pre-push step runs `/e2e`. A red run blocks the push. It sits at push rather than commit because auto-commit fires nearly every turn and e2e is slow.
4. **Fold correction rounds.** A tweak to Claude's own just-made, unpushed commit that belongs to the same logical change is folded into it, small tweaks included, rather than stacked as a new commit. The mechanics and the safe/unsafe checks are in `snippets/auto-commit.md`'s client-repo fold rule.
