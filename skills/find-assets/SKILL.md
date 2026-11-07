---
name: find-assets
description: Use when a game or app needs art or sounds. Finds free, license-checked ones, never draws them.
argument-hint: "<what is needed, e.g. cute pixel office characters with sit/typing animation> [--use public-repo|app-store|local-only]"
---

# /find-assets

> Search for existing free assets. Never make them.

Joe (2026-10-28): "i dont want you making the assets at all... it costs too many tokens and it can
sometimes not be worth it... theres tons of free great assets out there, i wanna make you good at
searching for assets". A standing preference in every project, not only the one that raised it.

## The rule

**Claude does not create art or sound assets** (sprites, tiles, characters, backgrounds, SFX, music,
logos) by hand, SVG, CSS pixel art, canvas code or an image model, unless Joe explicitly asks for
that asset in the current session. Joe typing `/generate` or asking for an image-model asset by
name is that explicit ask; Claude reaching for `/generate` on its own to fill a gap is not. A
missing asset is a search task, then a placeholder (a flat
colour block or the engine's default) while the search runs. Asking for "a character" in a
brainstorm is not asking Claude to draw one.

Two things this does not cover: UI icons (use Phosphor, per the global UI rules, which is a
library, not drawn art) and a free deterministic pipeline Joe names (an LPC generator export, a
palette swap script): running those is fine, hand-drawing is not.

## Steps

1. **Pin the ask.** From the request and the project, fix: asset kind (sprite sheet, tileset, UI
   pack, icon, SFX, music), art style and size (e.g. 16x16 or 32x32 pixel, side view), the
   animations needed (idle, walk, sit, type), the engine/format, and **where it will ship**:
   `public-repo`, `app-store`, or `local-only`. Shipping target decides which licenses are allowed
   (table below). If it is not stated and not inferable (a public GitHub repo is `public-repo`),
   use the strictest likely one and say so in the report.
2. **Read `sources.md`** in this skill's folder: the source list per asset kind, with what each
   source's licensing usually looks like. It is a starting map, not proof.
3. **Dispatch the search to a subagent.** Multi-query web research never runs inline: raw search
   results stay out of the main context. Use a `sonnet` Agent, `READ-ONLY DISPATCH`, with the full
   preamble from `refs/builder-preamble.md` (staging line, `run_in_background` FORBIDDEN line).
   The prompt carries step 1's brief, the shipping target, the source map from `sources.md`, and
   these requirements for what it returns, per candidate:
   - name, URL of the asset page, creator
   - **the license quoted verbatim from that page** (not "CC0, I think"), plus the page URL it came from
   - art size, palette/style, file format, how many frames and which animations exist
   - what is missing against the brief
   - a fit verdict (strong / usable / weak) with one line of why
   It returns 3-6 candidates, ranked, and also lists sources it checked that had nothing good.
   Any candidate whose license it could not read on the page is marked `license unverified` and
   ranked last whatever it looks like.
4. **Triage licenses** with the table below against the shipping target. Drop what the target forbids.
5. **Report ranked candidates** as a table: rank, name + link, license (verbatim quote), allowed for
   the target (yes / yes with credit / no), size, animations covered, gaps, verdict. Then one
   recommendation. Do not download, unpack or commit anything until Joe picks, except to look at a
   preview image.
6. **Update `sources.md`** when the search found a good source not already listed: one row, with the
   date, the license seen on the page, and what it is good for. A source that burned a search
   (paywalled, ripped, dead, license unclear) gets a row too, marked avoid, so the next search
   skips it. Only a session working in `~/.claude` edits the file (in place, line by line). From
   any other project, do not edit it: file the proposed row as a todo in
   `C:\Users\tecno\.claude\.claude\todos\` and mention it in the report.
7. **When Joe picks one,** record its credit in the project (a `CREDITS.md` or the engine's
   equivalent) with name, creator, URL, license and the date seen. CC-BY and CC-BY-SA need that
   credit; CC0 does not, but the row is still worth keeping.

## License triage

Rough guide, not legal advice. The license on the asset's own page wins over this table, and a
pack with mixed per-file licenses (LPC, OpenGameArt) is checked per file actually used.

| License | public repo | app store | local only | Notes |
|---|---|---|---|---|
| CC0 / public domain | yes | yes | yes | No credit needed |
| CC-BY | yes, with credit | yes, with credit | yes | Credit creator, link license |
| CC-BY-SA | yes, with credit | avoid: share-alike on adapted art, effect on the game is unsettled | yes | Ask Joe before shipping it |
| GPL (on art) | yes, with the license text | avoid: copyleft may reach the game | yes | Rare; treat like CC-BY-SA but stricter |
| CC-BY-NC | only while the repo stays non-commercial and nothing downstream is licensed for commercial reuse | no | yes | Fails any commercial or ad-supported release |
| "No redistribution" (paid itch.io packs, e.g. LimeZu) | **no**: a public repo redistributes it | no | yes | Keep out of git entirely (gitignore it) |
| Unlicensed rip (Spriters Resource, game rips) | no | no (Google Play's IP policy is reported to ban game artwork; the policy page itself was not read) | yes, private use only | Never in a public repo or a store build |
| No license stated | no | no | yes, private use only | "Free to download" is not a license |

## Pitfalls

- A "free" pack page that links a license file you cannot open is `license unverified`, not CC0.
- "Free for non-commercial" on an itch.io page is NC even when the page header says free.
- Modified assets keep the original license: a recoloured CC-BY-SA sprite is still CC-BY-SA.
- Prior art projects (open-source games and demos) credit their asset sources; their credits file is
  a fast lead to good packs, but the license is re-read at the source, not copied from the project.
- Kenney-style "logo reserved" or "do not claim as your own" clauses are credit courtesies, not a
  license restriction; still quote them.
