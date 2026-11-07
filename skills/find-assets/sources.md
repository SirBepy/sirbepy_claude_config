# Asset sources (living list)

A starting map for `/find-assets`, appended to by that skill when a search finds a good new source.
Free sources only: no paid signups, no accounts that cost money. Provenance column says how a row
was learned. **Nothing here replaces reading the license on the asset's own page at use time.**

Provenance codes: `R1028` = the 2026-10-28 claude_usage_in_taskbar "Game city view" research
(sonnet subagents, web), recorded in todo 1265. `bg` = Claude's background knowledge when the row was
added, NOT checked against the live site: treat as a lead only.

Row format when adding: `| source | kinds | typical license | notes | seen (date, how) |`.

## Art: sprites, tilesets, UI packs

| Source | Kinds | Typical license | Notes | Seen |
|---|---|---|---|---|
| Kenney (kenney.nl) | tilesets, UI, characters, icons, audio | CC0 for everything; logo reserved | Consistent style across packs, safest default | R1028 |
| OpenGameArt (opengameart.org) | everything | per file; filter by license | Many office/indoor packs are CC-BY-SA, not CC0: check each | R1028 |
| LPC / Universal LPC Spritesheet Generator | layered character sheets, walk/sit/etc. | per layer: CC0, CC-BY, CC-BY-SA, GPL | Exports a credits CSV; keep it with the project | R1028 |
| JIK-A-4 "Metro City" | characters | CC0 | Pixel characters | R1028 |
| itch.io (free, tagged assets) | everything | per pack; read each page | Free-but-NC and no-redistribution are common; filter by license and read it | bg |
| Quaternius (quaternius.com) | 3D models | CC0 | 3D only | bg |

## Art: icons and UI glyphs

| Source | Kinds | Typical license | Notes | Seen |
|---|---|---|---|---|
| Phosphor Icons | UI icons | MIT | The global default for frontend icons (see UI rules); a library, not an asset hunt | bg |
| game-icons.net | game item/ability icons | CC-BY 3.0 | Credit the artist per icon | bg |

## Sound

| Source | Kinds | Typical license | Notes | Seen |
|---|---|---|---|---|
| Kenney audio packs | SFX, UI sounds | CC0 | Same site as the art | R1028 |
| Freesound (freesound.org) | SFX, ambience, foley | per file: CC0, CC-BY, CC-BY-NC | Needs a free account to download; read each file's license | bg |
| OpenGameArt audio | SFX, music | per file | Same per-file license rule as the art | R1028 |

## Avoid, or local-only

| Source | Why | Seen |
|---|---|---|
| itch.io LimeZu Modern Interiors / Office | Cheap, not free, and forbids redistribution: local use only, keep out of git | R1028 |
| The Spriters Resource | Rips with no license; private local use only, never a public repo or a store build (Google Play's IP policy bans video-game artwork) | R1028 |
| Myinstants, 101soundboards, Sounds Resource | Game and meme rips, no license; also reject scrapers (HTTP 403 seen in character-creator work) | memory `reference_character_creator_sources` |

## Leads, not sources

Open-source projects that credit their art are a fast way to discover where good packs live: Pixel
Agents, a16z AI Town, Stanford Smallville (R1028). Read their credits file, then go to the original
source and read the license there.
