# Sound sources

Curated list for `/character-creator`. Try in order. Skip dead ones.

## Sites that WORK

1. **archive.org direct downloads** (best for full voice packs / music)
   Pattern:
   - Search archive.org for `<game> voice pack` or `<game> sound effects`.
   - Get filenames from `https://archive.org/metadata/<item-id>/files`.
   - Download via `https://archive.org/download/<item-id>/<URL-encoded-filename>.mp3`.
   - `Invoke-WebRequest -UseBasicParsing` works.

2. **soundfxcenter.com** (best for individual SFX clips)
   Pattern:
   - Search the game on soundfxcenter.
   - Fetch the per-character download page to extract the direct MP3 URL.
   - URL pattern: `soundfxcenter.com/video-games/<game>/<hash>_<Name>.mp3`.
   - `Invoke-WebRequest` to download.

3. **Game-specific fan wikis (audio sections)**
   Some Fandom wikis host quote audio inline. WebFetch to find the audio URL, then download from the wiki CDN.

4. **YouTube via yt-dlp (last resort)**
   Only if nothing else covers the character. Use sparingly - slow, lossy.

## Sites that BLOCK with 403 - skip immediately

- `sounds-resource.com`
- `sounds.spriters-resource.com`
- `myinstants.com`
- `101soundboards.com`
- `zapsplat.com`
- `curseforge.com` (WebFetch blocked; may work via direct Invoke-WebRequest)
- `hiveworkshop.com` (WebFetch blocked)
- Fandom wikis (`*.fandom.com`)

## Game-specific extraction notes

**Warcraft 3 (Reign of Chaos / Frozen Throne)** - audio lives in `War3.mpq` / `War3x.mpq` MPQ archives in the install dir. WC3 MPQs are encrypted, so `mpyq` (Python) fails. Working pipeline:

1. Joe has WC3 installed at `C:\Users\tecno\Desktop\Warcraft III Reign of Chaos & The Frozen Throne\`. Use that.
2. Copy `War3.mpq` + `War3x.mpq` to a path WITHOUT `&` (the ampersand breaks CLI args). Use `$env:TEMP\War3.mpq`.
3. Use Ladik's MPQ Editor (download from `http://www.zezula.net/download/mpqeditor_en.zip`, extract, run `x64\MPQEditor.exe`).
4. MPQEditor.exe is GUI-first BUT has a MoPaq script mode via `/console <script.txt>`. Script syntax:
   ```
   open "<absolute path to mpq>" "<absolute path to listfile>"
   extract "<archive>" "<file pattern>" "<dest>" -fp
   close
   exit
   ```
5. Get the listfile from `http://www.zezula.net/download/listfiles.zip` (24MB). `Warcraft III.txt` inside has all WC3 file paths.
6. Unit voice paths are `Units\<Race>\<Unit>\<Unit><Action><N>.wav` (NO `Sound\` prefix in WC3). Most units live in `War3.mpq`, hero updates / TFT additions in `War3x.mpq`.
7. Action suffixes: `Ready`, `What1-N`, `Yes1-N`, `YesAttack1-N`, `Warcry1-N`, `Pissed1-N`, `Death`. Map to slots: ready->ready, what->question_asked, yes->select, yesattack->work_finished, warcry/pissed->annoyed, death->death.
8. Skip `MPQExtractor.exe` (no Windows binaries) and `mpqtool` (ceres-wc3, requires internal listfile). Skip `mpyq` (no encryption support). Only Ladik's MPQEditor /console works.

**Don't try Setup.mpq from the install ISO** - it's an installer container, no listfile, returns None on read_file.

## Slot intent map

| Slot | Search terms |
| --- | --- |
| `work_finished` | "job done", "complete", "all done", "task finished", "victory", "yes sir" |
| `question_asked` | "yes?", "what?", "huh", "you called?", "sir?" |
| `ready` | "ready", "let's go", "begin", "spawn", select-on-spawn |
| `select` | "select", "yes", "click", "ack", "on it", "understood" |
| `annoyed` | "stop", "quit it", "leave me alone", "stop poking", complaining |
| `death` | "death", "I'm hit", "no!", final cry, scream |

## Bulk-vs-per-char strategy

Game mode: pull ONE bulk source per game (a voice pack zip / archive.org item with many clips). Distribute clips across all chars from the same staging dir. Saves 90% of the search effort.

Per-character fallback: only when the bulk source missed a slot. Then go to soundfxcenter or wiki audio for that one clip.

## Cleanup

- Each kept clip should be 0.5-3 seconds. Trim long ones with `ffmpeg -i in.mp3 -t 3 -c:a copy out.mp3` if available.
- Skip clips with intro music or background SFX that don't fit a notification chime.
- Loader accepts `.wav`, `.mp3`, `.ogg`, `.flac`. No conversion needed.
- Filename: `<char-slug>-<slot>-<n>.<ext>` (e.g. `sarge-work_finished-1.mp3`). Stable names.

## PowerShell shell tips

- `Invoke-WebRequest -UseBasicParsing -Uri <url> -OutFile <path>` for downloads.
- Never chain commands with `&&` or `;` - one command per call.
- Temp staging: `$env:TEMP\<game-slug>-sounds\`.
- Final dest: `$env:APPDATA\claude-usage-tauri\characters\<char-slug>\`.
