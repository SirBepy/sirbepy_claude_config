---
name: local-gpu-runs-gentle-limits
description: Joe wants long local AI runs on his PC gentle on CPU, GPU and RAM, even if slower
promoted: 2026-11-08
verified: 2026-11-08
sources:
  - C:\Users\tecno\.claude-personal\projects\C--Users-tecno-Desktop-Projects-dashboard-a\memory\local-gpu-runs-gentle-limits.md
  - C:\Users\tecno\.claude-personal\projects\C--Users-tecno-Desktop-Projects-rodge\memory\local-gpu-runs-gentle-limits.md
metadata:
  type: feedback
  scope: global
---
Joe (2026-10-22): "please lets make sure that we dont stress out my CPU GPU or RAM, lets go slower if needed".

**Why:** the bake-off ran models that spill off the 12 GB card at **99% CPU on all 20 threads**; Joe noticed.

**How to apply** (any long local model run in this project, measured 2026-10-22):
- Cap Ollama CPU threads at 8 (`num_thread`): CPU dropped to 17-32%.
- 2 s rest between calls; GPU pause at 70 C, resume at 60 C.
- RAM floor 4 GB free, not higher: a spilled 24-27B model alone keeps free RAM at 5-6 GB, and a 6 GB floor paused a
  night run for about 2.4 h waiting for RAM the loaded model itself held.
- Do not change process priorities yourself; Jarvis keeps llama-server at BelowNormal on Joe's request.
- Joe said the PC is free all day for runs when he is away, but schedule checks of long runs within about 1-2 h: a
  6 h gap left a stalled run idle for most of a day (2026-10-22).
- Daytime with Joe at the PC (2026-10-27, Mistral Small 3.2 24B spilled, Brave ~4-5 GB): free RAM sat at 1.7-3.9 GB,
  under the floor, so the run ran ~7 min, paused, unloaded, reloaded. Closing Steam and Discord was not enough.
  Conductor's speech-to-text helper (`claude_usage_in_taskbar\stt-sidecar` python, ~3.2 GB) respawns within seconds
  when killed, so it cannot be freed. Joe chose "let it crawl" over lowering the floor; big spilled models are night work.
  A detached watcher script that sleeps the PC when a run ends worked (`C:\Users\tecno\eval-data\sleep-watch.ps1`).
- Overnight 2026-10-30 (Qwen 3.8 27B spilled, 400 mails, personal-v1 check, eval run 559): free RAM sat at 2-4.5 GB even
  with Joe away, the runner's guard (pause under the floor, resume at 5 GB free, log line "paused until 60C and 5 GB
  free") let through only 12-60 mails per 30 min, so 400 mails took 7 h 05 min wall for 2 h of model time. GPU peaked
  at 58 C, so heat was never the limit; RAM was. A 400-mail 27B run is an all-night job. A Claude background command
  dies at its 2 h cap, but `pnpm eval run` resumes from the stored calls, so a detached looping script that reruns it
  until the call count reaches 400 finished it (script kept in `.for_bepy/personal-check/loop.ps1`).

Related: [[gemma4-26b-unstable-on-ollama]].
