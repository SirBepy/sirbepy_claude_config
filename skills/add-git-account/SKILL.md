---
name: add-git-account
description: Onboards a GitHub account for a project and wires commit identity, push auth, and gh CLI to it, scoped by remote URL, without touching the global default.
disable-model-invocation: true
argument-hint: "[gh-username] [commit-email]  (run from inside the target repo)"
---

# /add-git-account

> Add a GitHub account and make one project use it (commits, push/pull, and the
> `gh` CLI) without changing the global default.

## The hard rule (why this skill exists)

**Never run `gh auth switch` manually or inside a skill - the global hook
(`~/.claude/hooks/gh-account-switch.sh`) owns the active account**, switching
it automatically to match the current repo's origin remote on every `gh`
call. This skill wires only the git-identity layer (commit author + push/pull
auth), which the hook does not touch. If you ever feel tempted to run `gh auth
switch`, stop - add a `case` line to the hook instead (see step 5 below).

The dev keeps several GitHub accounts. One is the GLOBAL default (personal);
specific projects map to other accounts by **git remote URL**. This skill
owns one concern:

| Concern | Mechanism | Scope |
|---|---|---|
| Commit identity + git push/pull auth | `~/.gitconfig-<slug>` (user + gh-backed credential helper) loaded via a remote-URL `includeIf` in `~/.gitconfig` | git only |

This layer never mutates the global active account.

## Inputs

- **gh-username** - the GitHub account login (e.g. `JosipMuzicFibo`).
- **commit-email** - the `user.email` for commits in this project. Never guess
  an email; front-load it before writing.
- **remote owner** - derived from the current repo's `git config --get
  remote.origin.url` (e.g. `https://github.com/Fibo-Studio/fibo.git` ->
  owner pattern `github.com/Fibo-Studio/`). Confirm before writing.
- **slug** - short context name for the gitconfig file (e.g. `fibo`). Derive from
  the owner; confirm.

## Procedure

1. **Detect + confirm.** From inside the repo: read `remote.origin.url`, derive
   the `github.com/<owner>/` pattern and a slug. Show the derived owner pattern,
   slug, gh-username, and email; confirm before any write.

2. **Onboard the account (one-time login).** Run `gh auth status`. If the target
   username is NOT listed, it is a brand-new account: stop and have the dev run
   once, in their own terminal (interactive browser flow, persists in the keyring):
   `gh auth login --hostname github.com --git-protocol https --web`
   Do NOT proceed, and do NOT switch to another account as a workaround. Resume
   once the account appears in `gh auth status`.

3. **Git layer - write `~/.gitconfig-<slug>`** (mirror `~/.gitconfig-sirbepy`):
   ```
   [user]
       name = <gh-username>
       email = <commit-email>
   [credential "https://github.com"]
       helper =
       helper = "!f() { gh auth token --user <gh-username> --hostname github.com | sed 's/^/password=/'; echo username=<gh-username>; }; f"
       username = <gh-username>
   ```
   The empty `helper =` resets the inherited helper list (drops system GCM) for
   matching repos only; the gh-backed helper then provides auth from the named
   account's token. Never store a raw token; it is pulled live from gh.

4. **Git layer - add the `includeIf`** to `~/.gitconfig` (prefer the remote-URL
   form, next to the other `hasconfig` entries; it works regardless of where the
   repo lives on disk):
   ```
   [includeIf "hasconfig:remote.*.url:https://github.com/<owner>/**"]
   	path = ~/.gitconfig-<slug>
   ```
   Idempotent: skip if an entry for this owner already exists.

5. **gh-CLI layer.** The global PreToolUse hook (`~/.claude/hooks/gh-account-switch.sh`)
   owns which `gh` account is active, keyed by the origin remote's owner. Add
   one `case` line for the new owner: `*<owner>/*) acct=<gh-username> ;;`
   (see the existing entries in that file for the pattern).

6. **Verify both layers** (do not claim done without this):
   - `git -C <repo> config user.email` -> the new email.
   - `gh.exe auth status` -> global active account is UNCHANGED.

7. **Report.** Tell the dev that the hook change takes effect on the next `gh`
   call (no new terminal needed), and that existing commits keep their old
   author (this only affects new commits); offer a rewrite only if asked.

## Notes

- Resolving by **remote URL** (not folder path) is the preferred form: it works
  for clones anywhere and matches the dev's existing `hasconfig` convention. The
  older `gitdir:` entries still work; migrate them to the remote form
  opportunistically, but do not break a working setup unasked.
- Shell scope: the git layer (`includeIf` + `~/.gitconfig-<slug>`) is
  shell-agnostic - works from any shell. The `gh` CLI layer is owned by the
  bash hook (`~/.claude/hooks/gh-account-switch.sh`), independent of the
  dev's interactive shell.
- Quote paths with spaces.
