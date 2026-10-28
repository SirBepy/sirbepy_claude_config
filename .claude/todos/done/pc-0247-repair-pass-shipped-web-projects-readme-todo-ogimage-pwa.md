<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=4adb4886 -->
# One-time repair pass over 8 shipped public web projects: leaked README TODO line, broken relative og:image, root-absolute PWA service workers

**Type:** skill-improvement

## Goal

The `bepy-project-setup-web`/`readme`/`meta-tags`/`pwa` skills that generate/standardize
web projects have all had bugs fixed (per the broader skill-audit this todo was filed
from) that used to produce three specific defects. The FIX is already in the skills
themselves - this todo is the separate, one-time REPAIR PASS needed over the 8 already-
shipped public repos that were generated/updated BEFORE the fixes landed, since fixing
the skill does not retroactively fix output that already shipped. Three defects to
repair across those repos:

1. A leaked README TODO line (placeholder/reminder text that should have been removed
   before the README was considered finished, but shipped as-is).
2. A broken relative `og:image` meta tag (an Open Graph image path that resolves
   relative to the wrong base, so link previews/social shares show a broken image).
3. Root-absolute PWA service worker registration paths (a `serviceWorker.register('/sw.js')`-
   style absolute path that only works when the site is served from a domain root, not
   from a subpath - breaking install/offline behavior for any project actually deployed
   under a subpath, e.g. GitHub Pages project sites at `username.github.io/repo-name/`).

## Context

This todo was filed from a skill-audit session (2026-08-01) that reviewed
`skills/readme/SKILL.md`, `skills/meta-tags/SKILL.md`, and `skills/pwa/SKILL.md` (all
invoked by `skills/bepy-project-setup-web/SKILL.md`'s Step 2 pipeline) and found/fixed
the root causes producing these three defects in newly-generated projects. The audit
identified 8 already-live public repos still carrying the OLD, buggy output from before
those fixes. This todo's own source material (a set of audit reports under a `C:\tmp`
scratch path) is NOT available to whoever picks this up - it was explicitly disposable
per the task that filed this todo, so the exact list of 8 repo names, their exact
og:image paths, exact TODO line text, and exact service-worker paths must be
REDISCOVERED from the live repos themselves, not assumed from memory.

## Approach

1. **Rediscover the affected repos.** List Joe's public GitHub repos (`gh repo list
   SirBepy --visibility public --limit 100` or equivalent - confirm the right `gh`
   account is active per the global CLAUDE.md's account-switch hook, which switches by
   the CURRENT repo's origin remote; from outside any repo cwd it defaults to `SirBepy`
   per that hook's documented mapping) and identify which ones were built via
   `/bepy-project-setup-web` or its component skills (check for the tell-tale generated
   file shapes: a `manifest.json` + service worker from `/pwa`, standardized README
   sections from `/readme`, injected widget scripts from `/inject-widgets`, etc.).
2. **For each candidate repo, check for each of the three defects independently** (a
   repo may have zero, one, two, or all three):
   - README: grep for literal `TODO` markers or placeholder text that reads as
     unfinished/reminder content rather than real documentation (e.g. "TODO: add
     screenshot," "TODO: fill this in") - read the README in full to judge, since a grep
     hit alone doesn't prove it's a leaked placeholder vs an intentional roadmap item.
   - og:image: check `index.html`'s `<meta property="og:image" ...>` tag - if its `content`
     is a relative path (not starting with `https://` or a domain-qualified URL), it will
     break social-preview rendering for crawlers that don't resolve relative URLs against
     the page's own origin correctly (some do, many don't) - fix by making it an absolute
     URL pointing at the repo's actual deployed image path (GitHub Pages URL pattern:
     `https://<user>.github.io/<repo>/<image-path>`, confirm the actual deployed base URL
     per repo, do not assume a single URL prefix works for all 8).
   - PWA service worker: check `manifest.json`'s `start_url`/`scope` and the service-
     worker registration call (likely in `index.html` or a bundled JS file) for a
     root-absolute path (`/sw.js`, `/manifest.json`, `scope: '/'`) vs a repo-relative one
     appropriate for however each repo is actually deployed (GitHub Pages project site
     under `/repo-name/`, a custom domain at root, etc. - check each repo's actual deploy
     target before assuming they're all GitHub Pages project subpaths).
3. **Fix each confirmed defect per repo**, committing normally in that repo (this todo's
   fixes happen IN each affected repo, not in `~/.claude` - this backlog entry just
   tracks that the sweep needs to happen; the actual commits land in the 8 separate
   repos).
4. Keep a running list (in the PR/commit description of each fix, or a scratch note
   during the sweep) of which of the 8 repos had which of the 3 defects, so the final
   report to Joe is a clear per-repo checklist rather than a vague "fixed some stuff."

## Acceptance

- All public repos generated/updated via the bepy web-project skills have been checked
  for all three defects (not just the ones remembered/assumed - actually enumerate and
  check each candidate repo).
- Every confirmed defect is fixed and committed in its own repo.
- A final summary lists, per repo, which defects were found and fixed (or confirmed
  absent) - so there's a record this sweep was actually exhaustive, not partial.

## Notes

- Done 2026-08-13, all 15 repos, pushed direct to default branches on Joe's call. The remembered scope of 8 was wrong: rediscovery found 16 public Pages repos, 15 carrying at least one confirmed defect (only bepy_styleguide clean). Fixed: the leaked README TODO (byte-identical across 13 repos, so one template bug not 13 mistakes), relative og:image made absolute, and root-absolute PWA paths made subpath-relative in the 9 repos that had a PWA. Two things a pre-push verification pass caught that would otherwise have shipped broken: (1) mass_send_message was DEAD in production, its Vite base was /MassSendMessage/ while Pages serves /mass_send_message/, so the main bundle 404'd; that also meant its og:image absolute url pointed at a Vite-hashed path that did not exist, and sw.js was never in the build output at all. Fixed base, moved sw.js and the favicon into public/, proved each by running the build. (2) split_opinions's fixes had been edited but never staged, so its commit would have been empty. Shas: countdown_timer f0b9a01, flashcards aaafbde, mass_send_message 0adbd74, no_sleep cd81fb9, split_opinions 49d9ac6, codenames-generator d0b53ac, empires_guess_the_author bb6164b, mc_skin_to_roblox_clothing 421bbd0, vectorize_text_for_stroke_animation de19cbc, visualize_tycoon_balancing bb54ea7, a_cxnfusing_framework_docs 2677b57, portfolio_2021 e091ab3, sirbepy.github.io 4ad662c, sirbepy_blog b5ad817, wedding_invitation 71c7118. Known leftover, pre-existing and out of scope: mass_send_message's sw.js ASSETS cache list still names pre-hash paths that do not exist post-build; fixing it properly needs a build-time cache-manifest generator.

## Open questions

Written by /auto-do-todos on 2026-08-12. The next run opens with these.

- [ ] [TOOLING] Authorize a repair pass across 8 shipped public web repos (missing README, broken og:image, broken PWA install)? This is the only todo in the backlog that changes repos OUTSIDE ~/.claude and puts changes on live public sites, which is why the 2026-08-12 autopilot run did not start it on its own. Options: (a) one branch and PR per repo, nothing merged without your review; (b) push straight to each default branch, they are your own personal sites; (c) fix one repo first as a sample and decide after seeing the result. Recommended: (c).
- [ ] The todo's own source scratch data was explicitly disposable and is now gone, so the 8 repos and their specific defects have to be re-identified before any pass runs. Confirm the repo list is still what you expect.
