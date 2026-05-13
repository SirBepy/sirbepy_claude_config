# Auto-commit policy

Projects that `@import` this snippet opt into auto-commit-on-every-logic-change. Joe uses this for personal projects only.

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

## When the user says the commit was wrong

### What counts as "the commit was wrong"

Only these trigger an undo attempt:

- User says the last commit was a mistake (wrong approach, wrong scope, shouldn't have been committed at all).
- User says the change itself was wrong and the commit should be redone with the fix.

Do **not** trigger an undo for:

- Small tweaks ("rename this var", "tighten the wording", "also add X"). Make a new commit on top.
- Style nits on the commit message alone. Make a new commit on top; never amend.
- The user reading the diff and asking questions. Wait, don't undo anything.

Never `git commit --amend` or `git rebase` interactively. Always new commit on top OR soft-reset, nothing else.

### Identify the bad commit

First, figure out which commit the user means:

- If the user is talking about the **last commit you made this session** (no other commits since), it's HEAD. Go to "Case A".
- If the user names an older `<sha>` or describes an older change, treat it as an older commit. Go to "Case B".

When unsure, ask the user to confirm the sha before doing anything.

`<short-sha>` below means `git rev-parse --short <ref>` output (7 chars).

### Case A: the bad commit is HEAD

Run these checks in order. ALL must pass for "safe":

1. `git log -1 --pretty=oneline` — confirm the subject matches what was just committed.
2. `git fetch --quiet` — refresh remote tracking so the next check isn't stale. If there is no network or the remote is unreachable, treat the commit as unsafe to undo.
3. `git rev-parse --abbrev-ref --symbolic-full-name @{u}` — check upstream.
   - If this errors with "no upstream configured", the branch can't be pushed yet. Treat as **safe on the push axis** (push-not-possible = no remote impact).
   - If it returns an upstream name, run `git branch -r --contains HEAD`. Empty output = not pushed = safe. Non-empty = pushed = unsafe.

If safe:

1. Tell the user you're rolling back commit `<short-sha>`, fixing, recommitting.
2. `git reset --soft HEAD~1` (keeps changes staged).
3. Fix the issue.
4. Run `/commit` for a fresh message.

If unsafe (any check failed): go to "Fix forward" below.

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
