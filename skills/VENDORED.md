# Vendored skills manifest

What this file is: a record of which skills under `skills/` were copied in from a
third-party source (vendored) rather than authored by Joe, so a reinstall/update
doesn't silently clobber a local patch without anyone noticing.

How to regenerate: `git show --stat --name-only <vendoring-commit> | grep '^skills/'`
against the commit(s) that added a vendored pack, cross-checked with
`plugins/installed_plugins.json` and `plugins/known_marketplaces.json` for any
skill that DID come in through the live Claude Code plugin manager (none do, as
of this writing, see "How this repo actually got them" below). Patch status is
derived by diffing the current tree against the vendoring commit for each skill's
files: `git diff <vendoring-commit> HEAD -- skills/<name>`.

## How this repo actually got them

Every skill listed below was added by hand in a single commit,
`4cc2977 CHORE: vendor the Cloudflare, impeccable and web-perf skill packs`
(2026-08-12), not through `/plugin install`. `plugins/installed_plugins.json`
only lists `caveman`, `superpowers`, and `rust-analyzer-lsp` as live-installed
plugins, none of which map to any directory under `skills/`. So there is no
plugin lockfile or install-date field for these skills beyond "the date of
commit 4cc2977", and no upstream commit/version pin except where a skill's own
frontmatter carries one (`impeccable` does; the Cloudflare skills don't).

## Vendored skills

| Skill | Source | Version / commit | Vendored | Local patch |
|---|---|---|---|---|
| agents-sdk | github.com/cloudflare/skills | unknown (no version field, not plugin-installed) | 2026-08-12 (commit 4cc2977) | No |
| cloudflare | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| cloudflare-email-service | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| cloudflare-one | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| cloudflare-one-migrations | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| durable-objects | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| sandbox-sdk | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| turnstile-spin | github.com/cloudflare/skills (explicitly "Mirrors developers.cloudflare.com/turnstile/spin") | unknown | 2026-08-12 (commit 4cc2977) | No |
| web-perf | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| workers-best-practices | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| wrangler | github.com/cloudflare/skills | unknown | 2026-08-12 (commit 4cc2977) | No |
| impeccable | github.com/pbakaus/impeccable (npm package `impeccable`, author Paul Bakaus) | 4.0.4 (from the skill's own frontmatter, not independently verified against current upstream) | 2026-08-12 (commit 4cc2977) | **Yes** - `reference/new-work.md`, commit `540c946 FIX: scope code-check by language, unbloat impeccable's contract, pin SRI hashes (94, 106, 248, 282)` |

Evidence for the Cloudflare-family source: every one of these `SKILL.md`
descriptions carries the phrase "Biases towards retrieval from Cloudflare docs"
(or, for `turnstile-spin`, an explicit `developers.cloudflare.com` URL), and a
web search confirms `github.com/cloudflare/skills` publishes exactly this set
(agents-sdk, wrangler, durable-objects, sandbox-sdk, turnstile-spin, web-perf,
workers-best-practices, cloudflare, cloudflare-email-service, cloudflare-one,
cloudflare-one-migrations) as an installable Claude Code skill pack.

Evidence for `impeccable`: its frontmatter carries `version: 4.0.4` and
`license: Apache 2.0`, its `allowed-tools` invoke `npx impeccable *`, and a web
search confirms `impeccable` is a published npm package from
`github.com/pbakaus/impeccable`.

## Patch detection method and confidence

**Authoritative, not heuristic.** Because all 12 vendored skills entered the
repo in one identifiable commit (`4cc2977`), `git diff 4cc2977 HEAD --
skills/<name>` gives an exact, file-level answer for every one of them: only
`impeccable/reference/new-work.md` has changed since vendoring. This is a
stronger signal than mtime comparison and does not depend on having a separate
pristine copy on disk - the pristine copy is `git show 4cc2977:<path>`.

This method only covers skills vendored through this repo's own git history.
If a skill is ever vendored again by copy-pasting files without a commit
boundary (or by editing files in the same commit that adds them), this
technique cannot separate "upstream content" from "local edit" for that skill,
and would need a real pristine copy or plugin lockfile to fall back on.

## Non-vendored (hand-authored) skills

Every other directory under `skills/` (roughly 65 of them: `commit`, `close`,
`brainstorm`, `autopilot`, `clockify-reconciliator`, `android-drive`,
`screenshot`, and the rest) shows no vendor signature: no retrieval-bias
description text, no external frontmatter fields (`version`, `license`), no
match against `plugins/installed_plugins.json`, and each has its own
individual `FEAT`/`FIX` commit history in this repo rather than one bulk
vendoring commit. These are Joe's own and are out of scope for this manifest.
