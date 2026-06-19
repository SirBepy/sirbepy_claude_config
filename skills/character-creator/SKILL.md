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

### Canonical game dir - NEVER create a duplicate game group

Before writing ANY game dir, LIST the existing `<app-data>/characters/` dirs (and read each one's `game.json` `label`). If a dir already exists for the SAME game - even under a different slug - REUSE that exact existing dir + slug and write the new characters into it. Never create a second dir for a game that's already present.

Match by game IDENTITY, not exact slug string: normalize both sides (lowercase, strip punctuation, drop edition/article words like `the`, `iii`, `frozen-throne`, `rehydrated`) and compare against existing dir names AND their `game.json` labels before choosing a slug. If a normalized match exists, the existing slug wins; do not invent a new one.

Past incident (2026-06-06): a run created `warcraft3` (3 chars, 6 clips) alongside the existing `warcraft-3-frozen-throne` (4 chars, full kits) -> two duplicate "Warcraft III" groups in the UI. This had also happened on 2026-06-04. Root cause: no existing-dir check before picking a game-slug. Always do the check above.

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

Then per character: crop / resize to 64x64 with Python Pillow (ImageMagick is NOT installed on this machine), then **flatten onto an opaque background** (see sprite-sources.md "ALWAYS flatten transparency" — never ship an alpha icon; cutouts like HotS hexagons must become opaque rectangles). Save as `<char-dir>/icon.png`.

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

**Clip length rules (HARD) - NEVER guillotine a clip:**
- NEVER truncate a clip to a fixed length. The old "cut every clip to 2s" rule was WRONG: it chopped lines off mid-word (1136 clips ruined in the first batch). Do not reintroduce a fixed-length cut under any circumstance.
- **> 10 seconds:** discard the clip entirely. Too long for a notification chime. Find a shorter line instead - never chop a long clip down to fit.
- **<= 5 seconds:** keep the WHOLE clip. The only editing allowed is stripping leading/trailing PURE silence (never speech).
- **5 to 10 seconds:** keep the whole clip, but it needs the user's ear before shipping. Do NOT auto-assign a 5-10s clip to a slot. Add it to a per-run "5-10s clips pending approval" list so the user can listen once and approve or reject. Under `/autopilot` (no human present): fill slots from <=5s clips, and park every 5-10s candidate in `COMMENTS_FOR_BEPY.md` under a `## 5-10s clips pending approval` heading with its full path. Never block the run waiting on approval.
- **Silence-trim only** (WAV, stdlib `wave` - strip leading AND trailing silence below an amplitude floor, keep a ~150ms head/tail so the onset/final consonant isn't clipped). Do NOT use `audioop` (removed in Python 3.13+; read samples with `int.from_bytes`):
  ```python
  import wave  # stdlib only - do NOT use audioop (removed in Python 3.13+)
  with wave.open(in_path, 'rb') as w:
      sr, sw, ch, n = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()
      if n / sr > 10.0: skip()              # >10s -> discard, never cut
      frames = w.readframes(n)
  fr = sw * ch                              # bytes per frame
  full = 1 << (8 * sw - 1)                  # full-scale amp (128 for 8-bit, 32768 for 16-bit)
  floor = full // 90                        # ~1% of full scale counts as silence
  def amp(i):                               # |amplitude| of channel 0 at frame i
      v = int.from_bytes(frames[i*fr:i*fr+sw], 'little', signed=(sw > 1))
      return abs(v - 128) if sw == 1 else abs(v)   # 8-bit PCM is unsigned, centered at 128
  first = 0
  while first < n and amp(first) <= floor: first += 1          # strip leading silence
  last = n
  while last > first and amp(last - 1) <= floor: last -= 1     # strip trailing silence
  first = max(0, first - int(sr * 0.15))    # keep ~150ms head/tail so onset/consonant isn't clipped
  last  = min(n, last + int(sr * 0.15))
  frames = frames[first*fr:last*fr]
  with wave.open(out_path, 'wb') as ow:
      ow.setnchannels(ch); ow.setsampwidth(sw); ow.setframerate(sr); ow.writeframes(frames)
  ```
- MP3/OGG: do NOT re-encode to shorten. Keep whole if <=10s (subject to the 5-10s approval rule above); discard if longer.

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
- Audio format is load-bearing. The app decodes natively via `rodio` built with ONLY `wav`, `symphonia-mp3`, and `vorbis` features, so the **only playable formats are WAV (PCM), MP3, and Ogg *Vorbis***. NOT flac, NOT opus (incl. opus-in-ogg), NOT m4a/aac/webm - those decode to silence with no error. When a source clip is `.ogg`, confirm it is Vorbis not Opus (`ffprobe -show_entries stream=codec_name`); when it's any unsupported codec, transcode to WAV or Ogg Vorbis before saving. Past incident: a whole HotS batch shipped as valid files that played silently because rodio lacked the vorbis feature - never assume an extension implies playability.
- Don't write outside `<app-data>/characters/<char-slug>/` (and the temp scratch dir).
- Don't run the app, the dev server, or the test suite. Just produce files.
- Don't re-search per character what you can search once per game. Icons + sounds are bulk ops.
- Don't auto-trigger on natural phrases. The user must invoke `/character-creator` explicitly.
