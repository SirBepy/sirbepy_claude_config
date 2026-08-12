<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=918c522b -->
# inject-widgets: add SRI integrity hashes alongside the commit-pinned CDN script tags

**Type:** skill-improvement

## Goal

`skills/inject-widgets/SKILL.md` injects two third-party JS `<script>` tags (settings
widget, animated background) into every project's `index.html`, pinned to a specific
commit hash on jsdelivr's CDN. The commit pin already protects against the SCRIPT
CONTENT changing unexpectedly (a moving `@latest`-style tag could be silently altered
upstream), but does not protect the BROWSER from serving corrupted/tampered content if
jsdelivr itself is compromised or MITM'd - that's what Subresource Integrity (`integrity`
+ `crossorigin` attributes) is for. Add SRI hashes to both script tags, since this script
runs on every single page of every public bepy project.

## Context

`skills/inject-widgets/SKILL.md` (as of 2026-08-01), the two injected tags:

- Step 2, line 24:
  ```html
  <script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@cb6aebd1b672d69bae3aff91581a0a6c6ab2e695/widget/settings.js"></script>
  ```
- Step 3, line 37:
  ```html
  <script src="https://cdn.jsdelivr.net/gh/sirbepy/bepy-project-init@cb6aebd1b672d69bae3aff91581a0a6c6ab2e695/widget/background.js"></script>
  ```

Both are already pinned to the exact commit `cb6aebd1b672d69bae3aff91581a0a6c6ab2e695` of
`sirbepy/bepy-project-init` (good - this already prevents the script CONTENT from
silently changing on the source repo). Neither tag has an `integrity` attribute, so if
jsdelivr's CDN infrastructure itself were compromised (cache poisoning, BGP hijack, CDN
account compromise) the browser would still execute whatever bytes it received with no
verification against the known-good hash. Since this script is injected into "every
third-party JS on every public page" (per this todo's own filing context) across all of
Joe's public bepy projects, an SRI hash is a low-cost, high-leverage hardening step:
jsdelivr's own documentation explicitly supports and recommends SRI for exactly this pin-
to-commit use case.

## Approach

1. Read `skills/inject-widgets/SKILL.md` in full before editing.
2. Compute the SRI hash for each pinned file at the exact pinned commit. jsdelivr
   supports generating this directly - fetch
   `https://www.jsdelivr.com/package/gh/sirbepy/bepy-project-init` or use their documented
   SRI-hash API/URL pattern (jsdelivr publishes a per-file SRI hash lookup, e.g. appending
   specific query params or using their `data-jsdelivr-hash` tooling - check jsdelivr's
   current documentation for the exact mechanism at implementation time, since URL
   patterns for CDN tooling can change). Alternatively, download both files
   (`widget/settings.js`, `widget/background.js`) at the pinned commit directly from
   `sirbepy/bepy-project-init`'s GitHub repo and compute the hash locally:
   ```powershell
   $bytes = [System.IO.File]::ReadAllBytes("<downloaded-file>")
   $hash = [System.Security.Cryptography.SHA384]::Create().ComputeHash($bytes)
   "sha384-" + [Convert]::ToBase64String($hash)
   ```
   (SRI conventionally uses sha384; confirm jsdelivr's own recommendation matches before
   finalizing).
3. Add `integrity="sha384-<hash>"` and `crossorigin="anonymous"` attributes to both
   script tags in `skills/inject-widgets/SKILL.md` (both the settings-widget tag at line
   24 and the background tag at line 37). `crossorigin="anonymous"` is required for SRI
   to actually take effect on cross-origin script loads - without it browsers ignore the
   `integrity` attribute silently.
4. **Bump-pin coupling:** whenever `bepy-project-init`'s pinned commit hash changes in the
   future (a routine event per this file's existing convention of updating the commit
   pin), the SRI hash MUST be recomputed and updated in the SAME edit - a stale SRI hash
   paired with a new commit's bytes will make the browser REFUSE to load the script
   entirely (SRI mismatch = load blocked, not a silent fallback). Add an explicit note in
   `skills/inject-widgets/SKILL.md` next to the pinned commit stating this coupling, so a
   future commit-pin bump doesn't forget to recompute the hash and silently break every
   project's widget/background script.

## Acceptance

- Both injected `<script>` tags include correct `integrity` and `crossorigin` attributes
  matching the currently-pinned commit's actual file bytes.
- Load a project with the updated tags in a real browser and confirm the scripts still
  execute (no SRI mismatch error in the console) - this is the concrete proof the hash
  was computed correctly against the right file version.
- The file documents the "recompute SRI on every commit-pin bump" coupling explicitly,
  so it doesn't silently drift out of sync on the next pin update.

## Notes

- completed, commit 540c946. SRI hashes computed from the real fetched bytes and cross-checked GitHub raw against the jsdelivr CDN URL; the browser-load acceptance step has no live project in this repo to run against.
