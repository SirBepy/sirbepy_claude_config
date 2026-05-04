---
name: character-creator
description: Triggers on /character-creator <game-or-char> only. Game-centric by default - builds multiple characters from one game in a single batch (one icon source pass + one sound source pass shared across chars). For one-off single chars use `/character-creator <char> from <game>`. Outputs to <app-data>/characters/<char-id>/. Aborts cleanly when nothing usable is found. Never auto-triggers.
---

# /character-creator

> Scaffold character bundles (icon + per-event sound slots) for the user's claude_usage_in_taskbar Tauri app. Game-centric by default: one game = many characters built in one batch.

## Usage

Two invocation forms:

| Form | Meaning |
| --- | --- |
| `/character-creator <game-slug>` | Game mode (default). Build multiple characters from this game in one run. e.g. `/character-creator army-men-rts` |
| `/character-creator <char-slug> from <game-slug>` | Single-char mode. Build one character but tag it under the named game. e.g. `/character-creator vikki from army-men-rts` |

The skill never auto-triggers on natural phrasing.

## Char id naming

**Do NOT include the game name in the char-slug.** The UI groups chars by their `game` field, so prefixing every char with the game name is redundant and ugly.

Right: `sarge`, `peon`, `vikki`, `peasant`, `arthas`
Wrong: `army-men-sarge`, `wc3-peon`, `army-men-vikki`

Exception: only when the SAME char-slug would collide across games or variants of the same character. e.g. `sonic-classic` vs a future `sonic-modern` both belong to game `sonic`. The slug disambiguates the variant, not the game.

## Output

Characters are GROUPED BY GAME. Layout:

```
<app-data>/characters/
  <game-slug>/
    game.json                  # game metadata
    _shared/                   # shared/global sounds for this game
      character.json           # has "shared": true
      icon.png
      sounds/
    <char-slug>/               # per-character bundle
      character.json
      icon.png                 # 64x64
      sounds/
        *.wav | *.mp3 | *.ogg
    <other-char>/
      ...
```

Resolve `<app-data>` per platform:
- Windows: `%APPDATA%\claude-usage-tauri`
- macOS: `~/Library/Application Support/claude-usage-tauri`
- Linux: `~/.config/claude-usage-tauri`

### `game.json` schema

```json
{
  "id": "army-men-rts",
  "label": "Army Men RTS",
  "year": 2002,
  "publisher": "3DO",
  "platform": "PC",
  "genre": "Real-time strategy"
}
```

Add fields as the app grows. Always write at minimum `id` + `label`.

## Workflow

### Step 1: Parse args + pick characters

Parse the invocation:
- `<char> from <game>` -> single-char mode. `chars = [<char>]`, `game = <game>`. Skip Step 2.
- `<game-slug>` alone -> game mode. Continue.
- Bare `<char-slug>` with no game -> ask the user which game it belongs to via AskUserQuestion (free-form). Set `game` accordingly.

### Step 2: Ask which chars to build (game mode only)

Use AskUserQuestion (multiSelect: true) to pick which characters from the named game to build. Source the candidate list from prior knowledge of the game. Cap at 4 options per AskUserQuestion call; if the game has more, run a second question or ask the user to specify additionally.

If the user picks "Other", they specify slugs free-form (comma-separated).

Each selected character gets its own slug. Output dir uses the char-slug, NOT the game-slug.

### Step 3: Create dirs

For each char-slug in the build list:
- `mkdir -p <app-data>/characters/<char-slug>/sounds`
- If the dir already exists with a `character.json`, ask once whether to overwrite or skip THIS character (don't abort the whole batch).

### Step 4: Find icon source (one pass per game)

Read `sprite-sources.md`. Find ONE source that covers the whole game's roster (sprite sheet, portrait grid, screenshot, or per-char Wikipedia images). Download it/them once.

**Bulk-zip strategy applies here too.** If the game is dumped on archive.org or available as a modding asset pack, downloading once and pulling per-character textures + portrait files out is faster than per-char web hunts. Same trust rule as sounds: archive.org / ModDB / NexusMods / official = safe. Unknown hosts = flag for Joe before downloading.

Then per character: crop / resize to 64x64 with Python Pillow (ImageMagick is NOT installed on this machine). Save as `<char-dir>/icon.png`.

If no source covers a character, leave that char's icon missing and surface in the final summary as:

> Could not find an icon for `<char-slug>`. Drop a 64x64 PNG at `<full-path>/icon.png` manually.

Never synthesize art with an image model. The user explicitly chose sourced over generated.

### Step 5: Find sound source (one pass per game)

Read `sound-sources.md`. The cheap moves:
1. Search archive.org for a voice/SFX rip of the game (e.g. item like `armymen-rts-voicepack`). Download once.
2. **Bulk-zip strategy preferred.** A single big zip (full game build, modding asset pack, voice rip archive) is almost always faster than chasing per-character clips. Suggest it whenever one exists. Joe explicitly favors this path. Caveat: only from trustworthy hosts. archive.org / official mirrors / GOG / Steam Workshop / well-known modding sites (ModDB, NexusMods) are safe. Random forum attachments and unknown filehosts are NOT - flag the source before downloading and let Joe decide.
3. Search soundfxcenter.com for the game's per-character pages.
4. Per-char fallback: Wikipedia / wiki transcripts to know what each character's iconic lines are, then look those exact phrases up on archive.org.

Aim to download a single bulk source (zip / multi-file archive) that covers most characters. Stage to `$env:TEMP\<game-slug>-sounds\`.

### Step 5b: Build a shared `<game>` bundle for global sounds

Some sounds are global to the entire game roster - death screams, generic "yes"/"job done" lines, building completion chimes. Don't duplicate them into every char. Instead, write a SHARED bundle:

- Slug: the game-slug itself (e.g. `army-men-rts`, `warcraft-3`)
- `character.json` has `"shared": true` to mark it as a fallback bundle
- Slots filled with the truly-shared clips (death, work_finished defaults, etc.)
- Icon: a faction logo / generic emblem for the game

Per-char bundles only fill slots they have UNIQUE content for. Slots they lack fall back to the shared bundle (resolver concern - app handles).

This keeps each char focused on their distinctive lines and avoids 7x duplication of the same death scream.

### Step 6: Distribute sounds per char per slot

For each character, for each of these slots:

| Slot | Intent |
| --- | --- |
| `work_finished` | "job done", "complete", "all done", "yes sir" |
| `question_asked` | "yes?", "what?", "huh", "you called?" |
| `ready` | "ready", "let's go", spawn / select-on-spawn |
| `select` | acknowledge / click / "on it" |
| `annoyed` | "stop that", "quit it", complaint, poke-line |
| `death` | death scream, "I'm hit", final cry |

**Keep ALL candidate sounds you find.** The user has a UI to swap slot mappings later, so the per-char `sounds/` dir is a POOL — every clip we extract goes in, even if it doesn't fit a slot. Delete only failures (corrupt, wrong format, > 5s).

Filename convention: `<char-slug>-<original-action>-<n>.<ext>` (NOT `<slot>-<n>` — preserve the original action info so the user knows what's what when picking from the pool).
- e.g. `sarge-select-0.wav`, `sarge-attack-0.wav`, `sarge-spotted-0.wav`, `sarge-mandown-0.wav`
- N is a 0-based index per (action, char) pair — multiple lines for same action get distinct N.

Don't reuse the same clip across `select` and `question_asked` slots for the same char unless unavoidable. But the FILES exist in the pool regardless — slots just point to a subset.

**Clip length rules (HARD):**
- Discard ANY candidate clip > 5 seconds. Don't even keep it staged. Joe doesn't want long clips and they make poor notification chimes.
- Trim accepted clips to <= 2 seconds when writing the final WAV. Ideal is <1 second.
- For WAVs use Python's stdlib `wave` module to truncate frames (no ffmpeg needed):
  ```python
  import wave, io
  with wave.open(in_path, 'rb') as w:
      sr = w.getframerate(); n = w.getnframes()
      if n / sr > 5: skip()
      keep = min(n, int(sr * 2))
      frames = w.readframes(keep)
  with wave.open(out_path, 'wb') as ow:
      ow.setnchannels(...); ow.setsampwidth(...); ow.setframerate(sr)
      ow.writeframes(frames)
  ```
- For MP3 trimming, use ffmpeg: `ffmpeg -i in.mp3 -t 2 -c:a copy out.mp3`. Install via scoop if missing.

### Step 7: User picks per slot per char

For each char, for each slot, use AskUserQuestion (multiSelect: true) to let the user pick which staged clips to keep. 4 options max per call (AskUserQuestion limit); if more candidates, surface the best 4 and mention extras.

Copy chosen files into `<char-dir>/sounds/`. Discard the rest.

If a slot returned zero candidates, leave it empty in `character.json`. v1 events (`work_finished`, `question_asked`) tolerate empty - the resolver falls back to the global default sound.

If both `work_finished` and `question_asked` end up empty for a char, ask once whether to retry with different terms, supply files manually, or accept silent fallback.

### Step 8: Write `character.json` per char

```json
{
  "id": "<char-slug>",
  "label": "<Pretty Name>",
  "game": "<game-slug>",
  "version": 1,
  "icon": "icon.png",
  "slots": {
    "work_finished":  ["sounds/<char-slug>-work_finished-1.wav"],
    "question_asked": ["sounds/<char-slug>-question_asked-1.wav"],
    "ready":          ["sounds/<char-slug>-ready-1.wav"],
    "select":         ["sounds/<char-slug>-select-1.wav"],
    "annoyed":        ["sounds/<char-slug>-annoyed-1.wav"],
    "death":          []
  }
}
```

`label` is the title-cased pretty version of the slug.
`game` is the game-slug from Step 1. Always present, even in single-char mode.

### Step 9: Final summary

Print one block per char:

> Character `<char-slug>` ready at `<full-path>`.
> Slots filled: work_finished (N), question_asked (N), ready (N), select (N), annoyed (N), death (N).

Then once at the bottom:

> Refresh the Characters view in the Claude Usage app to see them (sidemenu > Characters > Refresh button).

If any slot was left empty for any char, list explicitly so the user knows.

## Don't

- Don't ship an icon you couldn't actually fetch. No synthesized art.
- Don't normalize / convert audio formats unless required (loader accepts wav/mp3/ogg/flac).
- Don't write outside `<app-data>/characters/<char-slug>/` (and the temp scratch dir).
- Don't run the app, the dev server, or the test suite. Just produce files.
- Don't re-search per character what you can search once per game. Icons + sounds are bulk ops.
- Don't auto-trigger on natural phrases. The user must invoke `/character-creator` explicitly.
