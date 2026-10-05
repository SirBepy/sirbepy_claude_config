# Client-repo policy

Client work is tested harder than personal work, because a regression there lands on someone else's product and on Joe's reputation with them.

## Which repos this covers

A repo is a **client repo** when its `origin` slug (`owner/repo`) is listed in `~/.claude/refs/client-repos.txt`. Keyed by origin rather than folder, so a second checkout or linked worktree of a listed repo counts too. Nothing is ever added to a client repo's own files. Check any repo with `python C:/Users/tecno/.claude/hooks/_client_repo.py is-client <path>`; a repo not on the list is personal, whoever owns it.

## What changes in a client repo

1. **Every behaviour change ships with a test that fails without it.** Write the test alongside the change, not after. A change that cannot be tested by Claude (native UI, hardware, visual judgement) says so explicitly in the commit report instead of shipping silently untested.
2. **Commit and push run extra gates.** The full ordered list, client-only steps marked, lives only in `/commit`'s "Push pipeline" section (`skills/commit/SKILL.md`); read it there, never restate it here, since every restated copy drifted when a step was added. The client-only review and e2e sit at push rather than commit because auto-commit fires nearly every turn, and a review per commit mostly re-reviews work that gets folded anyway.
3. **The push is hook-enforced.** `hooks/client-push-gate.py` blocks any `git push` in a client repo until HEAD is cleared with `python C:/Users/tecno/.claude/hooks/_client_repo.py mark <repo> --reason "<why>"`. Clear it only after both checks pass. When a check cannot pass (flaky spec, backend down, no e2e path), ask Joe through `ask_user_question` whether to push anyway, and mark with a reason naming the failure only on his yes. Pushes Joe runs in his own terminal are outside the hook.
4. **Fold correction rounds.** A tweak to Claude's own just-made, unpushed commit that belongs to the same logical change is folded into it, small tweaks included, rather than stacked as a new commit. The mechanics and the safe/unsafe checks are in `snippets/auto-commit.md`'s client-repo fold rule.
