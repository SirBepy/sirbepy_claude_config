# Sound sources

Curated list for `/character-creator`. Try each in order. Search per slot using natural-language queries that map to the slot's intent.

## Slot intent map

| Slot | Search terms |
| --- | --- |
| `work_finished` | "victory", "done", "completed", "task complete", "yay", "finished" |
| `question_asked` | "yes", "what", "huh", "ready", "select", "waiting" |
| `ready` | "ready", "let's go", "begin", "spawn" |
| `select` | "select", "yes", "click", "ack", "acknowledged" |
| `annoyed` | "stop", "annoyed", "leave me alone", "pissed", "stop poking" |
| `death` | "death", "defeated", "fall", "noooo", "scream" |

## Sources (try in order)

1. **MyInstants** — https://myinstants.com  
   Search box at the top. Each result has an MP3 download link. Quick 2-5 second clips, perfect length for notification sounds. Best for popular game / TV / meme characters.

2. **The Sounds Resource** — https://www.sounds-resource.com  
   Game character voice packs as zip files. Higher fidelity, larger downloads. Best when you need every line a character says (e.g. for a Warcraft peon).

3. **101soundboards** — https://www.101soundboards.com  
   Searchable per-character soundboards. Useful when MyInstants is sparse.

## What to skip

- YouTube rip jobs (slow, low quality, licensing).
- TTS synthesis (only the bundled `default` character uses generic sounds).
- Stock sound libraries (won't match a specific character).

## Cleanup

- Each kept clip should be 0.5-3 seconds. Trim with `ffmpeg -i in.mp3 -t 3 -c:a copy out.mp3` if a clip is too long.
- Skip clips with intro music or background SFX that don't fit a notification chime.
- The loader accepts `.wav`, `.mp3`, `.ogg`, `.flac`. No need to convert formats.
- Filename should be `<slug>-<slot>-<n>.<ext>` (e.g. `sonic-work_finished-1.mp3`). Stable names make it obvious which file feeds which slot.
