# Auto-commit policy

Universal default: unconditionally imported from global CLAUDE.md's Git Commits section, applies to every project, personal and client alike. **Never ask "should I commit this?" or "want me to commit?" before running `/commit`** - the answer is already yes whenever the criteria below are met. Asking defeats the entire point of this policy; if you notice yourself about to ask, that's the signal to just run `/commit` instead.

## When to commit

After finishing a turn, run `/commit` (always via the skill, never raw `git commit`) if **all** of these are true:

- You wrote or edited at least one file this turn that is **not** gitignored (any file type: code, docs, config, etc).
- Tests, type checks, or whatever verification is reasonable for the change have already been run and pass. If verification was skipped (e.g. no test suite, doc-only change, UI-only change you couldn't drive), say so out loud before committing.
- The turn ended cleanly. No half-broken state. No "I'll fix the rest later" loose ends in the diff.
- The user did not say "don't commit yet" or "wait, I want to look first" this turn.

Skip the auto-commit if:

- Every file you touched is gitignored (nothing to stage).
- The turn was a pure Q&A with no file changes.
- The change is a tiny part of a clearly-in-progress larger task and the user is steering step by step.

Commit is **the last action** of the turn. Test first, commit last. Do not commit and then keep editing.

Mixed turns (some gitignored, some not): commit the non-ignored files normally. Don't mention the ignored ones in the message.

## Folding a correction into the last commit

One commit per logical change still holds, but a correction round on a change you *just* committed is not a new logical change - it's finishing the same one. Client repos especially must not accumulate a commit per correction round: fold the fix into the commit you just made whenever that's safe, instead of stacking a new one on top.

### What counts as "fold this in"

Fold when the user says the just-committed change is categorically wrong - wrong approach, wrong scope, should be redone entirely:

- User says the last commit was a mistake (wrong approach, wrong scope, shouldn't have been committed at all).
- User says the change itself was wrong and should be redone with the fix.

Do **not** fold (make a new commit on top instead) when:

- The request is additive - a genuinely new ask layered on top of already-good work ("also add X", "now do Y too"). That's its own logical change, not a correction.
- The feedback is an ordinary small tweak or nit on otherwise-correct work ("no, fix X", "rename this", "you missed Y") - Fix-forward, not a fold. Folding is for redoing the commit, not patching it.
- Style nits on the commit message alone. Make a new commit on top; never amend.
- The user is reading the diff and asking questions. Wait, don't touch anything.

When it's genuinely unclear whether feedback is categorically-wrong-redo-it or an ordinary small tweak, ask.

Never `git commit --amend` or `git rebase` interactively. Always new commit on top OR the atomic `update-ref` fold below, nothing else.

### Identify the bad commit

First, figure out which commit the user means:

- If the user is talking about the **last commit you made this session** (no other commits since), it's HEAD. Go to "Case A".
- If the user names an older `<sha>` or describes an older change, treat it as an older commit. Go to "Case B".

When unsure, ask the user to confirm the sha before doing anything.

`<short-sha>` below means `git rev-parse --short <ref>` output (7 chars).

**Captured-sha requirement for Case A:** immediately after `/commit` creates a commit, note its full sha (`git rev-parse HEAD`, or read it off the commit output) and hold it in context for the rest of the session as `<captured-sha>` - no file, no persistent storage, just something you remember for this conversation. Case A's fold path below depends on having this value. If the bad commit is HEAD but there is no `<captured-sha>` in context for it (e.g. it was committed in a prior session, or context was compacted/cleared since), there is nothing to compare against - treat it exactly like Case B and go straight to "Fix forward".

### Case A: the bad commit is HEAD

Requires `<captured-sha>` in context (see above). Run these checks in order. ALL must pass for "safe":

1. `git fetch --quiet` — refresh remote tracking so the next check isn't stale. If there is no network or the remote is unreachable, treat the commit as unsafe to undo.
2. `git rev-parse --abbrev-ref --symbolic-full-name @{u}` — check upstream.
   - If this errors with "no upstream configured", the branch can't be pushed yet. Treat as **safe on the push axis** (push-not-possible = no remote impact).
   - If it returns an upstream name, run `git branch -r --contains HEAD`. Empty output = not pushed = safe. Non-empty = pushed = unsafe.

If safe:

1. Tell the user you're rolling back commit `<short-sha>`, fixing, recommitting.
2. Run the fold as one atomic compare-and-swap: `git update-ref -m "fold correction" HEAD <captured-sha>~1 <captured-sha>`. The trailing `<captured-sha>` is update-ref's old-value guard - git refuses the update (fatal error, nothing changes) if HEAD no longer equals `<captured-sha>`, e.g. a concurrent session committed on top. This replaces a separate verify-then-reset with a single atomic step, closing the race by construction.
   - On success: HEAD now points at `<captured-sha>~1`; the index and working tree still hold the bad commit's changes staged, same as `reset --soft` would leave them.
   - On failure (non-zero exit, "but expected ..." error): HEAD moved under us. Do not retry or force. Go to "Fix forward" below instead.
3. Fix the issue.
4. Run `/commit` for a fresh message.

If unsafe (fetch/push check failed): go to "Fix forward" below.

### Case B: the bad commit is older than HEAD

Run:

1. `git rev-list <sha>..HEAD --count` — if > 0, there are commits on top. Always unsafe regardless of push state.
2. (Skip even checking push state; commits on top make soft-reset wrong here.)

Go straight to "Fix forward".

### Fix forward (the unsafe path)

1. Tell the user: can't cleanly undo commit `<short-sha>` (give the specific reason: pushed, N commits on top, or no upstream-info available). Fixing forward as a new commit.
2. Make the fix as a new commit.
3. Commit message:
   - Subject: `FIX: <what>` (project's normal commit style, no special prefix).
   - One-line body: `Fixes: <short-sha>` — gives traceability without claiming git autosquash semantics. Do NOT use `fixup!` as a subject prefix unless the project explicitly uses `git rebase --autosquash` (this one doesn't).

Example:

```
FIX: correct loop bound in watchdog

Fixes: 1b67860
```

When in doubt, treat as unsafe.
