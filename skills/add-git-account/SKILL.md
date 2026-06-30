---
name: add-git-account
description: Triggers on /add-git-account only. Onboards a GitHub account for a project AND wires that project's commit identity + push auth + gh CLI to it, scoped by remote URL, without touching the global default.
argument-hint: "[gh-username] [commit-email]  (run from inside the target repo)"
---

# /add-git-account

> Add a GitHub account and make one project use it (commits, push/pull, and the
> `gh` CLI) without changing the global default.

## The hard rule (why this skill exists)

**NEVER run `gh auth switch` (or any global account change) to satisfy a
per-project need.** gh's active account is global; switching it breaks every
other repo. Per-project account selection is done with the three-part mechanism
below. If you ever feel tempted to "just switch the account," stop and use this.

The dev keeps several GitHub accounts. One is the GLOBAL default (personal);
specific projects map to other accounts by **git remote URL**. Two concerns,
two layers - keep them straight:

| Concern | Mechanism | Scope |
|---|---|---|
| Commit identity + git push/pull auth | `~/.gitconfig-<slug>` (user + gh-backed credential helper) loaded via a remote-URL `includeIf` in `~/.gitconfig` | git only |
| `gh` CLI account (`gh pr create`, etc.) | a `gh` shadow function in the PS profile that sets `GH_TOKEN` per-call from a remote->account table | gh CLI only |

Neither layer mutates the global active account.

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

5. **gh-CLI layer - the PS profile resolver.** Profile lives at `$PROFILE`
   (today: `…\OneDrive\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`).
   - If the `gh` shadow function + `$GhAccountByRemote` table are ABSENT, install
     the whole block (see "Resolver block" below).
   - If present, add one line to `$GhAccountByRemote`:
     `'github.com/<owner>/' = '<gh-username>'` (skip if already there).

6. **Verify both layers** (do not claim done without this):
   - `git -C <repo> config user.email` -> the new email.
   - Token routing: in PowerShell, `$env:GH_TOKEN = (gh.exe auth token --user
     <gh-username> --hostname github.com); gh.exe repo view <owner>/<repo>
     --json name; Remove-Item Env:GH_TOKEN` -> resolves the repo.
   - `gh.exe auth status` -> global active account is UNCHANGED.

7. **Report.** Tell the dev to open a new terminal (or `. $PROFILE`) for the `gh`
   function to take effect, and that existing commits keep their old author (this
   only affects new commits); offer a rewrite only if asked.

## Resolver block (install once into the PS profile)

```powershell
# --- Per-project GitHub account routing for the gh CLI ----------------------
# Maps a substring of a repo's origin URL to the gh account `gh` should use.
# Git push/pull + commit identity are handled separately by the ~/.gitconfig-*
# credential helpers (includeIf). This only affects the gh CLI, and only for the
# duration of each call - the GLOBAL default account stays whatever it is.
# Add a project: one line in the table below.
$global:GhAccountByRemote = [ordered]@{
    'github.com/Fibo-Studio/' = 'JosipMuzicFibo'
}
function gh {
    $real = Get-Command gh.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $real) { Write-Error 'gh.exe not found on PATH'; return }
    $acct = $null
    $url = (& git config --get remote.origin.url 2>$null)
    if ($url) {
        foreach ($k in $global:GhAccountByRemote.Keys) {
            if ($url -like "*$k*") { $acct = $global:GhAccountByRemote[$k]; break }
        }
    }
    if (-not $acct) { & $real.Source @args; return }
    $token = (& $real.Source auth token --user $acct --hostname github.com 2>$null)
    if (-not $token) { & $real.Source @args; return }
    $had = Test-Path Env:GH_TOKEN
    $old = $env:GH_TOKEN
    $env:GH_TOKEN = $token
    try { & $real.Source @args }
    finally {
        if ($had) { $env:GH_TOKEN = $old } else { Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue }
    }
}
```

## Notes

- Resolving by **remote URL** (not folder path) is the preferred form: it works
  for clones anywhere and matches the dev's existing `hasconfig` convention. The
  older `gitdir:` entries still work; migrate them to the remote form
  opportunistically, but do not break a working setup unasked.
- Shell scope: the resolver is Windows PowerShell 5.1 (the dev's only interactive
  shell). If a Git Bash / pwsh setup appears later, add an equivalent resolver to
  that profile; the git layer is shell-agnostic and needs no change.
- One command per call, quote paths with spaces, never chain.
