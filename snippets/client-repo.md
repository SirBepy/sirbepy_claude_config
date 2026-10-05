# Client-repo policy

The testing floor and the push gate apply to every repo (`CLAUDE.md` "Testing & verification floor", sequence in `/commit`'s "Push pipeline"). Client repos keep two extras on top, because a regression there lands on someone else's product and on Joe's reputation with them.

## Which repos this covers

A repo is a **client repo** when its `origin` slug (`owner/repo`) is listed in `~/.claude/refs/client-repos.txt`. Keyed by origin rather than folder, so a second checkout or linked worktree of a listed repo counts too. Nothing is ever added to a client repo's own files. Check any repo with `python C:/Users/tecno/.claude/hooks/_client_repo.py is-client <path>`; a repo not on the list is personal, whoever owns it.

## What changes in a client repo

1. **No e2e suite still means an e2e check.** Where `/e2e` finds no scripted path (its "anything else" row: bare Node without Playwright, Rust/Tauri, a backend API), a personal repo's Pre-push gate notes "no suite" and moves on; a client repo's drives the real system by hand instead (curl the endpoints, click through the app). The step itself lives in `/commit`'s "Pre-push gate".
2. **Fold correction rounds.** A tweak to Claude's own just-made, unpushed commit that belongs to the same logical change is folded into it, small tweaks included, rather than stacked as a new commit. The mechanics and the safe/unsafe checks are in `snippets/auto-commit.md`'s client-repo fold rule.
