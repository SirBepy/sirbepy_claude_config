# shortcut-done-audit — investigation dispatch prompt

Read this file at step 5 (dispatch investigation subagent(s)) before firing any Agent calls. Fill in the per-ticket facts computed in steps 1-5, then paste the resulting prompt to each subagent.

## Dispatch prompt shape

Fan out in parallel - single message, multiple `Agent` calls, `model: 'sonnet'`, `subagent_type: 'general-purpose'`. Never use the Workflow tool for this unless Joe explicitly asks for orchestration (per global CLAUDE.md gate). When batching (volume gate triggered), give one subagent 2-3 tickets with clearly separated sections in the prompt and ask it to return one verdict block per ticket, don't blur evidence across tickets. Paste the canonical preamble from `refs/builder-preamble.md` into every dispatch prompt (it's read-only per the "Explicit read-only instruction" below, so the `READ-ONLY DISPATCH` opt-out applies) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers.

Each dispatch prompt must include, per ticket:

- The ticket ID, its current workflow state name, and every matching commit SHA + subject found in step 3 (or, for a soft match, the branch name and its tip SHA).
- **Explicit read-only instruction**: no comments posted, no workflow-state changes, no code edits, no commits, no `git checkout`/`pull` (repo is already fetched).
- Shortcut story-fetch command (same token pattern as step 2) — the story JSON includes `description`, `comments`, `pull_requests`, `branches`, `commits`, `labels`, `blocked`/`blocker`, `moved_at`. There is no separate history endpoint; infer state-lag from these fields plus git.
- Pre-computed mechanical facts so the subagent doesn't waste its own turns re-deriving them: whether each SHA is already an ancestor of `develop`/`main` (`git merge-base --is-ancestor <sha> develop`), and the branches it's contained in (`git branch -a --contains <sha>`) — hand these down as facts, don't make question 4 below re-run them per-agent.
- The five core questions, in this order, with "answer with evidence" (quote comment text, cite SHAs, cite file/line):
  1. **Was it returned?** Reviewer/QA pushback in comments, closed-unmerged or reopened PRs, rework-signaling labels.
  2. **Any new comments** — especially unanswered ones raising concerns.
  3. **Can you reproduce the described issue/behavior right now?** Case-by-case depth: read the current code and reason it through by default; only reach for `/run` or browser automation if code-reading is genuinely inconclusive (e.g. behavior depends on live API responses or timing) — don't default to booting the app for every ticket, it's slow and fragile across a batch.
  4. **Was it just done and never moved?** Use the pre-computed ancestor/branch facts above, plus whether the workflow state realistically lags the code.
  5. **MOST IMPORTANT — does the ticket's described scope match what was actually implemented?** Read the full description/AC, then `git show` every matching commit (or diff the branch against `develop` for a soft match), and call out any gap, partial coverage, or drift — not just "does it compile."
- If a sibling ticket shares a rename commit, an event name, or clearly overlapping scope (grep other tickets' titles/commits for the same feature area first), tell the subagent explicitly to check whether the sibling **supersedes** part of this ticket's AC — this was the single most valuable catch in the first run (54521 vs 54680).
- Ask for an overall verdict in a fixed vocabulary so the report step can group cleanly: `DONE`, `PARTIALLY DONE` (list gaps), `SUPERSEDED` (name the other ticket), `MISMATCH` (commits with the right ID prefix implement something else / real fix is unmerged), or `UNCLEAR`.

## Edge cases learned from the first run

- **Commit-prefix misattribution.** A ticket ID prefix on a commit message doesn't guarantee the commit implements that ticket — someone can typo/reuse an ID. Always cross-check the commit's actual diff against the ticket description, never trust the prefix alone. (Caught on 54263: two "54263:" commits on develop were unrelated work; the real fix sat unmerged on an abandoned branch.)
- **Sibling supersession.** Two FE tickets on the same feature area, worked back-to-back, can leave the older one's AC stale without either being "wrong" — the newer ticket intentionally replaced part of the older scope. Always check sibling tickets sharing a rename commit or the same feature folder before calling something a gap. (Caught on 54521 vs 54680.)
- **Stale-deploy false alarms.** A QA/PM comment reporting a bug "still happening" can predate the actual deploy of a fix that's already merged to `develop` — check commit timestamps vs comment timestamps before treating a comment as a real return. Still flag it as unanswered/unresolved even if likely stale; don't silently dismiss it.
- **Cross-codebase companion tickets.** Two tickets with near-identical titles/event names can be legitimately separate work in different repos (e.g. Framer/zirtue.com marketing site vs Flutter zng-app) rather than duplicates — check the description for explicit cross-references before flagging as a dupe.
- **Backlog with commits isn't automatically "board hygiene."** Don't assume a low-state ticket with matching commits must be understated — verify the commits are actually merged and actually match scope before recommending a forward move.
