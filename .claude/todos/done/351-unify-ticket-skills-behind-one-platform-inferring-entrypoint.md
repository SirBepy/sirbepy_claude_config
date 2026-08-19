<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Eight ticket skills each hand-roll their own API; unify them behind one platform-inferring `/ticket`

**Type:** skill-improvement
**Origin:** dev

## Goal

One ticket entrypoint that infers the tracker from the repo, with per-platform quirk files holding
only what genuinely differs, replacing eight skills that each carry their own copy of the same
create/update/search plumbing.

## Context

Joe's ask, 2026-08-16, raised while deciding todo 338's fate: *"what if we had one skill that
creates all tickets, and then it just infers from the project is it linear/shortcut/whatever, this
kind of knowledge gets saved in memory or in obsidian, for now memory, but myb later in obsidian
too, and then we can have new subfiles for quirks with each platform, like how we do apply some
extra fields in shortcut as opposed to linear or smth"*.

Current surface, counted 2026-08-16 in `~/.claude/skills/`:

- `shortcut-create-ticket`, `shortcut-update-ticket`, `shortcut-pickup-ticket`,
  `shortcut-done-audit`, `shortcut-priorities`
- `linear`
- `obsidian-pickup-ticket`

Todo 343 already pulled the shared `search/stories` recipe out into `refs/shortcut-api.md`, so the
Shortcut half has a partial shared layer to build on. There is no equivalent for Linear.

## Approach

**Scope was settled 2026-08-18** (handoff todo 378, now archived). The shape below is decided; do not
re-litigate it:

- **Merge only create / update / pickup**, with the platform looked up from the repo. `priorities`
  and `done-audit` stay separate skills - they are cross-ticket sweeps, not per-ticket operations.
  This is narrower than this todo's original all-eight framing, and it is Joe's call.
- **The reason is consistency of enforcement, NOT DRY.** The tree-wide "fold everything into routers"
  idea scored **3/10** across two rating panels (9 subagents) and its DRY premise was falsified by
  measurement: the actual duplication left across the ticket skills is about a 3-line warning
  repeated three times. **Do not revive the router idea.** The narrow create/update/pickup merge
  scored 5/10 and is worth doing on enforcement grounds alone.
- **Platform inference means a deterministic repo-to-tracker lookup, not a model guess.** Joe pushed
  back correctly on requiring an explicit platform argument. `hooks/gh-account-switch.sh` already
  proves the deterministic-lookup pattern in this tree.
- **Obsidian is out of scope.** Joe, 2026-08-18: *"obsidian isnt important at all... later when i
  need obsidian, i can ask an ai to add obsidian."* So `obsidian-pickup-ticket` is not part of the
  merge.
- **`/test` (shipped 2026-08-18) is the proof-of-shape** this todo builds on: one verb, stack
  inferred from marker files, delegating to specialists rather than absorbing them. Copy that
  structure rather than inventing a second one.

Remaining sketch, still open:

- Repo-to-tracker mapping is the load-bearing piece. Joe's stated preference is native per-project
  memory first, Obsidian later. `hooks/gh-account-switch.sh` already holds a repo-owner mapping in
  bash and `refs/shortcut-api.md` holds the Shortcut side, so check what can be reused before
  inventing a third registry.
- Per-platform quirk files (extra fields Shortcut requires that Linear does not, and vice versa)
  sit beside a shared core, the same shape `refs/` files already use.
- `shortcut-create-ticket`'s ground-check gate plus `hooks/shortcut-create-guard.py` are the
  strongest part of the current surface and must survive the merge platform-agnostically, not get
  dropped as Shortcut-specific. `shortcut-update-ticket` has no equivalent gate today, which is the
  one real gap todo 338 left behind when it was archived as superseded.

## Acceptance

- One entrypoint files a ticket into the right tracker without being told which one.
- **The outbound gate that shipped 2026-08-18 survives the merge intact**: creates on both platforms
  and claim-bearing updates (name, description, comments) still hard-block without a fresh ground
  check, via `refs/outbound-ground-check.md` plus `hooks/linear-create-guard.py`,
  `hooks/linear-update-guard.py` and `hooks/shortcut-mutation-guard.py`. State moves and self-assign
  stay frictionless - do not widen that without asking Joe.
- The merged skill must not be able to disarm its own guard. `shortcut-mutation-guard.py` was
  deliberately moved OUT of `skills/shortcut-create-ticket/hooks/` for exactly this reason.
- No skill still carries a private copy of plumbing the shared layer provides.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` when Joe answered the question round. Dev-origin: this is his
  idea, not a Claude finding, so it does not get archived without his word.
- **Sized as its own session.** Eight skills is not a side quest inside another run.
- **Todo 58 is DONE and no longer blocks this** (2026-08-18). It deleted, merged and rewrote
  **nothing** - all 83 skills were verified live and none were dead - so the eight ticket skills all
  survived and this job did not shrink. What 58 changed is context budget, not the surface. Record:
  `skills/AUDIT-2026-08-18.md`. Do not re-audit.
- **This is the next concrete build**, per handoff 378, which shipped `/test` first as the smaller
  proof of the same verb-first pattern.
- Supersedes the leftover half of [[338-shortcut-create-ticket-needs-a-source-verification-gate]],
  archived 2026-08-16.
- Related: [[343-shortcut-call-sites-still-hand-roll-search]] built the shared Shortcut search recipe.
- Done 2026-08-18. /ticket shipped at skills/ticket/ - SKILL.md (model-invocable, tracker resolved from the git remote via a 2-row table), shortcut.md and linear.md quirks files, plus the 51-entry log.md moved out of the deleted skill (it was gitignored, so deleting the directory would have destroyed it). shortcut-create-ticket, shortcut-update-ticket and shortcut-pickup-ticket deleted, per Joe's call. Fibo and personal repos are explicitly out of scope: /ticket names the remote and stops. All references repointed (CLAUDE.md, README.md, refs/shortcut-api.md, refs/outbound-ground-check.md, hooks/shortcut-create-guard.py, .gitignore, todo 353). The one acceptance item not landed is /linear's reverse pointer, blocked a fourth time by orphaned uncommitted changes in that file - filed as todo 387.
