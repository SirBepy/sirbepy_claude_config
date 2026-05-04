---
name: character-creator
description: Triggers on /character-creator <name> only. Scaffolds a new character bundle (icon + sound slots) for the claude_usage_in_taskbar Tauri app at <app-data>/characters/<id>/. Searches curated sprite + sound sources; aborts with a clear instruction if nothing usable is found. Never auto-triggers.
---

# /character-creator

> Scaffold a complete character bundle (icon + per-event sound slots) for the user's claude_usage_in_taskbar Tauri app.

## Usage

`/character-creator <name>` where `<name>` is the slug-form id of the character (e.g. `sonic`, `peon`, `mario-doctor`). The skill is invoked manually only; it never auto-triggers on natural phrasing.

## Output

A populated dir at `<app-data>/characters/<slug>/`:

```
<slug>/
  character.json
  icon.png         (64x64 PNG, source: spriters-resource or similar)
  sounds/
    *.wav | *.mp3 | *.ogg
```

Resolve `<app-data>` per platform:
- Windows: `%APPDATA%\claude-usage-tauri`
- macOS: `~/Library/Application Support/claude-usage-tauri`
- Linux: `~/.config/claude-usage-tauri`

## Workflow

### Step 1: Confirm the slug

Ask the user with AskUserQuestion if there's a more specific subject (e.g. for "Sonic" - Genesis Sonic, modern Sonic, Sonic 2, etc). One question, no body. Skip if the slug is already specific.

### Step 2: Create the dir

`mkdir -p <app-data>/characters/<slug>/sounds`

If the dir already exists with a `character.json`, ask the user whether to overwrite or abort.

### Step 3: Find an icon

Read `sprite-sources.md` (sibling file). For each source in order, attempt to fetch a 64x64-or-larger portrait of the character:

1. Try the source's search/listing for the slug.
2. If a usable image is found, download it.
3. Crop or resize to 64x64 with whatever tool is available (ImageMagick `magick`, Python Pillow, or `sips` on macOS).
4. Save as `icon.png` in the character dir.

If no source produces a usable image, abort with this exact message and exit:

> Could not find an icon for `<slug>`. Drop a 64x64 PNG at `<full-path>/icon.png` and re-run `/character-creator <slug>`.

Never synthesize art with an image model. The user explicitly chose sprite-sourced over generated art.

### Step 4: Find candidate sounds per slot

For each slot in this order:

| Slot | Intent |
| --- | --- |
| `work_finished` | victory / done / completed |
| `question_asked` | yes / what / huh / waiting for input |
| `ready` | "ready" / "let's go" / select-on-spawn |
| `select` | acknowledge / click |
| `annoyed` | "stop poking me" / pissed / leave-me-alone |
| `death` | death / defeated / fall / final cry |

Read `sound-sources.md`. For each slot, search the sources with the intent hints. Download 4-8 candidates per slot to a temp dir. Keep filenames descriptive (`<slug>-<slot>-<n>.<ext>`).

### Step 5: Present picks per slot

For each slot, use AskUserQuestion (multiSelect: true) to let the user choose which downloaded candidates to keep. Limit options to 4 per question (AskUserQuestion's max). If more candidates exist, surface the best 4 and mention more in the question text.

For chosen files: copy from temp into `<char-dir>/sounds/` with the keep-name. Discard the rest.

### Step 6: Handle empty slots

If a slot returned zero candidates across all sources, leave the slot empty in `character.json`. Warn the user with a one-line summary at the end. v1 events (`work_finished`, `question_asked`) tolerate empty slots: the resolver falls back to the global default sound.

If both `work_finished` and `question_asked` are empty after the search, ask the user once whether to retry with different search terms, supply files manually, or accept the silent fallback.

### Step 7: Write `character.json`

```json
{
  "id": "<slug>",
  "label": "<Pretty Name>",
  "version": 1,
  "icon": "icon.png",
  "slots": {
    "work_finished":  ["sounds/<slug>-work_finished-1.wav"],
    "question_asked": ["sounds/<slug>-question_asked-1.wav"],
    "ready":          ["sounds/<slug>-ready-1.wav"],
    "select":         ["sounds/<slug>-select-1.wav"],
    "annoyed":        ["sounds/<slug>-annoyed-1.wav"],
    "death":          []
  }
}
```

`label` is the Pretty Name version of the slug (title-cased, hyphens to spaces).

### Step 8: Confirm

Print:

> Character `<slug>` ready at `<full-path>`.
> 
> Slots filled: work_finished (N), question_asked (N), ready (N), select (N), annoyed (N), death (N).
> 
> Refresh the Characters view in the Claude Usage app to see it (sidemenu > Characters > Refresh button).

If any slot was left empty, list it explicitly so the user knows.

## Don't

- Don't ship an icon you couldn't actually fetch. No synthesized art for v1.
- Don't normalize / convert audio formats unless required (the loader accepts wav/mp3/ogg/flac).
- Don't write outside `<app-data>/characters/<slug>/` (and the temp scratch dir).
- Don't run the app, the dev server, or the test suite. Just produce files.
- Don't auto-trigger on natural phrases. The user must invoke `/character-creator <name>` explicitly.
