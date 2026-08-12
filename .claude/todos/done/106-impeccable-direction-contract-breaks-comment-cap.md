<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=76265954 -->
# impeccable's direction contract mandates a comment block the global cap forbids

**Type:** skill-improvement
**Origin:** ai

## Goal

Resolve the direct conflict between `impeccable`'s "record the decision" step and the global
comment cap, so a session does not have to pick which instruction to break.

## Context

Hit 2026-08-10 in hubbub-game-music-guesser.

`~/.claude/skills/impeccable/reference/new-work.md` section 5 requires the chosen direction to
be written into the artifact as a comment: five blocks (THESIS, OWN-WORLD, STORY, FIRST
VIEWPORT, FORM) plus a FINISH line, up to 150 words, "in a form that survives the production
build", explicitly as an HTML comment in emitted markup. It also says to grep the built output
for the seed key afterwards, so it is meant to be auditable in the build.

Global `CLAUDE.md` Code Style says: **2 lines typical, 4 lines HARD CAP per comment block**, and
that design rationale "belongs in the PR body, a PATTERNS/CLAUDE doc, or the commit message" -
backed by a named 2026-07-29 incident.

These cannot both be satisfied. The contract needs six labelled sections; four lines cannot hold
them. Written as specified it lands at ~15 lines, and `/commit`'s own comment-noise prefilter
flags it immediately (`longest 15`), which is how the conflict surfaced.

What I did in that session: wrote the full contract in `src/screen.tsx`, got flagged at commit
time, then moved it into `DESIGN.md` and left a 2-line pointer in the source. That satisfied both
rules and arguably reads better, but it was an ad-hoc call made under commit pressure, and the
next session will hit the same fork and may resolve it the other way.

## Approach

Pick one and write it down so it stops being a judgment call:

1. **Preferred:** amend `new-work.md` section 5 to say the contract lives in `DESIGN.md` (which
   that same section already requires at finish anyway), with a <=2-line pointer comment in the
   artifact carrying the seed key. Keeps the audit trail - the seed key is still greppable - and
   respects the global cap. Cost: the contract no longer rides inside the built markup.
2. Add an explicit carve-out to global `CLAUDE.md` Code Style naming the impeccable direction
   contract as the one exempt block. Cost: an exemption is a precedent, and the cap's value is
   that it has none.

Whichever wins, also update `~/.claude/skills/commit/comment-noise.md` so the prefilter's
expected behaviour matches.

## Acceptance

- A fresh session running `/impeccable` on a new visual world produces a commit that passes the
  comment-noise prefilter with no manual trimming.
- The seed key is still findable after the fact (grep of source or `DESIGN.md`).

## Notes

Separate false positive worth fixing while in that file: the prefilter's awk treats any line
starting with `--` as a comment, so a CSS file's `--custom-property` declarations are counted as
comment lines. `src/mixtape.css` was flagged at "8/31 (25%) longest 6" while containing exactly
two single-line comments. Suggest excluding `--` for `.css`/`.scss` files, where it can never
mean a comment.
- completed, commit 540c946
