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

Not settled, and deliberately so. Sketch only:

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
- Shortcut's ground check still hard-blocks a create without a fresh marker, and update gets the
  same treatment.
- No skill still carries a private copy of plumbing the shared layer provides.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` when Joe answered the question round. Dev-origin: this is his
  idea, not a Claude finding, so it does not get archived without his word.
- **Sized as its own session.** Eight skills is not a side quest inside another run.
- **Overlaps todo 58** (the whole-skills audit), which is precisely the pass that decides which of
  the eight survive at all. Doing 58 first would likely shrink this job. Joe reconfirmed 58's park
  on 2026-08-16, so neither is scheduled yet.
- Supersedes the leftover half of [[338-shortcut-create-ticket-needs-a-source-verification-gate]],
  archived 2026-08-16.
- Related: [[343-shortcut-call-sites-still-hand-roll-search]] built the shared Shortcut search recipe.
