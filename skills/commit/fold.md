# /commit fold <sha>

Read on demand from `skills/commit/SKILL.md` when the dev types `/commit fold <sha>`.

Folds newly-staged-or-named fixes into an existing commit `<sha>` that is not yet pushed, preserving every other commit's original message, author, and timestamp. This is the explicit, dev-named counterpart to `~/.claude/snippets/auto-commit.md`'s "Folding a correction into the last commit" section, not a replacement for it - if `<sha>` is HEAD and nothing has landed on top of it since, that snippet's own atomic `update-ref` recipe (its Case A) is simpler and applies directly, use it instead. This mode exists for the case that snippet marks unsafe for silent/automatic action (its Case B, other commits sitting on top of the target) but which is fine once a dev explicitly names the sha and no file overlap blocks a clean split.

**Preconditions, checked in this order, before anything is written:**

1. Resolve `<sha>` to a full hash (`git rev-parse <sha>`). Unresolvable: stop, tell the dev.
2. **Pushed check, unmissable, and it must query the live remote, never local refs.** A pushed commit is never folded, and the dev is not asked to choose: refuse, name the sha, and tell them to make a normal follow-up commit instead (same fix-forward wording as auto-commit.md's "Fixes: `<short-sha>`" body line). Stop, do not touch history.

   `@{u}` and `origin/*` are **not** evidence. A branch can be pushed with an explicit refspec and never get an upstream, and `origin/*` goes stale the moment a fetch fails (Revaire repos fetch as the wrong account and 404 silently), so both routinely report "unpushed" for a commit that is live on the remote and under review. Prove it against the remote itself:

   - `git remote` empty: nothing to push to, genuinely safe, continue.
   - Otherwise `git ls-remote <remote> 'refs/heads/*'` for the live tip shas. For each tip the local object store already has, `git merge-base --is-ancestor <sha> <tip>`; any success means pushed - refuse.
   - A tip whose object is missing locally cannot be tested, so it cannot clear `<sha>` either. If any tip is untestable and none of the testable ones matched, **refuse anyway** and say the check was inconclusive. This mode rewrites published history when it is wrong, so an unprovable answer is treated as pushed.
3. **Overlap check.** `git log --format=%H <sha>..HEAD` lists every commit on top of the target. For each, `git show --name-only --format= <commit>` and intersect with the file list this fold is about to touch. Any overlap: a clean pathspec split can't separate the hunks - **refuse this mode**, point the dev at "Splitting one file across commits" in `skills/commit/edge-cases.md` instead.
4. Step 5a's `prefilter-gate.sh` runs against the fold's own file set, same as any other commit.
5. Branch guard: record `git rev-parse --abbrev-ref HEAD` now, and re-check it immediately before the reset below - same rule as step 8's, stop if it moved. Same peer check (7a) too, but here the announcement stays a broadcast: the daemon commit lock covers only `git commit`, not a reset, so when `list_peers` shows another session, `post_message` the pathspec about to be rewritten before touching history.

**Recipe, once every precondition passes:**

1. Record the ordered commit list from `<sha>` to `HEAD`, oldest first, with each full hash, author date, committer date, and message: `git log --format='%H|%aI|%cI|%s' --reverse <sha>~1..HEAD`.
2. `git reset --soft <sha>~1` - moves HEAD to the target's parent; the index now holds everything from `<sha>..HEAD` plus this fold's own fix, together. Same deliberate, surfaced exception to the "never reset what you didn't stage" rule as step 8's own unpushed-overlap check - this is the dev's own prior work, named explicitly.
3. Recommit oldest first by pathspec, never `git add -A`:
   - First commit = the original target's own file list plus the fold's fix files, using the **original** message from step 1, with `--date` and `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` set to the original timestamps.
   - **Shared-file hazard:** a pathspec commit takes the file's CURRENT working-tree state, not that commit's own diff. Before recommitting, intersect every riding commit's `git show --name-only` list against every other's; any file in more than one means each earlier recommit will silently absorb later commits' hunks to that file unless restored first - a silent pass here is worse than an aborted fold. Before each intermediate recommit, `git checkout <original-sha> -- <shared-file>` to put the file back to that commit's own blob; before the final commit, restore the pre-fold tip's state the same way.
   - Each remaining original commit, in original order, recommitted with its own unchanged file list (restored per the hazard above if shared), original message, original timestamps.
   - **Client repo, inside the 23:00-10:59 window:** `hooks/commit-window-guard.py` refuses every `--date` / `GIT_*_DATE` there, allow marker or not, so a fold that replays original timestamps has no path until 11:00. Wait for 11:00 (the replayed night dates then pass once Joe's allow marker exists) or defer the fold; never drop the dates to squeeze it through, since that rewrites the commits' times.
4. **Verify via patch-diff, not full-tree-diff**, every commit except the folded one: `git show <original-sha>` must diff empty against `git show <new-sha>` for its replacement. A full-tree comparison would not catch a hunk silently landing in the wrong commit.
5. Report the old-sha to new-sha remapping to the dev.
