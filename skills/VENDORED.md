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
| agents-sdk | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only (see below) |
| cloudflare | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| cloudflare-email-service | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| cloudflare-one | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| cloudflare-one-migrations | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| durable-objects | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| sandbox-sdk | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| turnstile-spin | github.com/cloudflare/skills (explicitly "Mirrors developers.cloudflare.com/turnstile/spin") | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| web-perf | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| workers-best-practices | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| wrangler | github.com/cloudflare/skills | unknown upstream commit (frozen copy, see SOURCE notes) | 2026-08-12 (commit 4cc2977) | **Yes** - flag only |
| impeccable | github.com/pbakaus/impeccable (npm package `impeccable`, author Paul Bakaus) | 4.5.2 (SKILL.md frontmatter `version`; updated in place by `npx impeccable update`, re-vendored in commit 1a066d6) | 2026-10-08 (commit 80dd5a5), re-vendored 2026-11-07 | **None.** The 118-word upstream `description` is kept verbatim and exempted in `ci/check_skill_frontmatter.py` (`LEGACY_OVER_BUDGET_DEBT`, reason "vendored upstream description"), because `npx impeccable update` overwrites SKILL.md in place and would undo any trim. Earlier local patches (`540c946`, `1f9eb1d`, the trimmed description) are all gone with the re-vendor and none is needed |
| asd-ste100 | github.com/danyuchn/asd-ste100-skill | 0.4.0 (frontmatter `version`) | 2026-10-15 (commit 6813a5a) | **Only the trimmed `description`** - upstream's 67-word, 465-char description fails `ci/check_skill_frontmatter.py`'s 25w/120c budget for a model-invocable skill. The trim is recorded in `skills/VENDORED.overrides.json` and re-applied by `python ci/check_vendored_overrides.py --apply` |

## Re-applying local overrides after a vendor update

`skills/VENDORED.overrides.json` lists every local frontmatter line that differs from upstream
(the 11 Cloudflare `disable-model-invocation: true` flags and asd-ste100's trimmed description).
`python ci/check_vendored_overrides.py` fails CI when one has drifted; after ANY vendor update
(`npx impeccable update`, a fresh copy of the Cloudflare pack, a new asd-ste100 release) run
`python ci/check_vendored_overrides.py --apply`, then `python ci/run_all.py`. impeccable has no
override: its description is exempted in `ci/check_skill_frontmatter.py` instead.

## SOURCE notes

- **Cloudflare pack (11 skills):** a frozen copy of `github.com/cloudflare/skills`, vendored in one
  commit (`4cc2977`, 2026-08-12). The upstream commit it was copied from was never recorded, so
  there is no pin; to refresh, compare against upstream's current tree and re-run the overrides
  step above. Only `wrangler` also has content edits beyond the flag (see its own git history).
  Decision 2026-11-07 (todo 1282): keep all 11. `cloudflare`, `wrangler`,
  `durable-objects`, `workers-best-practices` and `cloudflare-email-service` match live work
  (hubbub is a Worker with Durable Objects and KV). The other six (`cloudflare-one`,
  `cloudflare-one-migrations`, `sandbox-sdk`, `agents-sdk`, `turnstile-spin`, `web-perf`) stay too:
  all are slash-only, so deleting them saves no listing tokens, and `agents-sdk` holds 19
  references the umbrella `cloudflare` skill does not. `web-perf` needs a chrome-devtools MCP that
  is not configured here, so expect it to be unusable until one is.
- **impeccable:** `github.com/pbakaus/impeccable`, npm package `impeccable`. Update with
  `npx impeccable update`; `~/.impeccable/update-check.json` announces newer versions.
- **asd-ste100:** `github.com/danyuchn/asd-ste100-skill`, copied by hand at 0.4.0.

## The "flag only" patch, 2026-08-18

All 11 Cloudflare-family skills gained one frontmatter line during the todo 58 audit:

```yaml
disable-model-invocation: true
```

Nothing else in them changed, so `git diff 4cc2977 HEAD -- skills/<name>` should show exactly
that one added line per skill. Why: their descriptions totalled 4,243 chars of always-on session
context, 41 percent of the whole model-invocable budget, against **2 invocations in the 31 days
to 2026-08-18**, while Joe ran 59 real `wrangler` commands in `Desktop\Projects\hubbub\apps\worker`
over the same window. So the domain is live but the auto-invoke was not earning its cost. They stay
fully usable as `/cloudflare`, `/wrangler` and so on.

**Re-vendoring will silently drop this line.** Upstream does not carry it. Anyone refreshing this
pack from `github.com/cloudflare/skills` must re-apply the flag to all 11 (`python ci/check_vendored_overrides.py --apply`; CI now fails if one is missing), or the always-on budget
quietly grows back by 4,243 chars.

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
