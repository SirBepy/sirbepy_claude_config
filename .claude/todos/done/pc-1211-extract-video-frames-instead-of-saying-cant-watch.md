<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep for ffmpeg/video/.mp4 hit only 1174 (preview pairs), done/847 (android record motion), done/459 (get-id), none about reading video attachments -->
# Extract frames from video attachments instead of saying Claude can't watch them

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-20

## Goal
When Joe attaches a video (.mp4/.mov) in chat, Claude pulls frames with ffmpeg and reads them, instead of telling him it can't watch videos.

## Context
2026-10-20, zng-admin session (SVB Slack thread triage): Joe attached a screen recording. Claude said "I couldn't watch the video" and moved on. Joe corrected it: "bro what do you mean, you usually are able to watch videos". Later in the same session Claude extracted frames and it worked first try:
ffmpeg is installed at `C:\Users\tecno\scoop\shims\ffmpeg.exe` (and ffprobe). The Read tool accepts images only, not video, so the frames step is required.

Recipe that worked (8-second clip, one contact sheet):
```
ffprobe -v error -show_entries format=duration -of csv=p=0 "<video>"
ffmpeg -y -v error -i "<video>" -vf "fps=1,scale=300:-1,tile=8x1" -frames:v 1 sheet.png
```
Then Read `sheet.png`. For longer clips, lower fps (e.g. `fps=1/2`) and use a grid tile (`tile=6x2`) with `-frames:v N` for N sheets. Scratch dir must be a new empty dir (untrusted download rule), not a drive-root child (`C:\tmp\...` can't be cleaned by the removal guard, see refs/builder-preamble.md).

## Approach
Add a short rule to global `CLAUDE.md` or a ref it points to (token budget permitting, `ci/check_instruction_budget.py`): "Video attachment: probe duration, extract a frame contact sheet with ffmpeg, Read it. Never say Claude can't watch it." Alternatively a tiny `refs/video-frames.md` with the recipe, referenced from CLAUDE.md's Communication or UI section.

## Acceptance
- The rule exists in a file every session loads, or in one CLAUDE.md points to.
- Instruction budget check passes.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): refs/video-frames.md recipe verified on a 2 s testsrc clip (ffprobe 2.000000, contact sheet rendered); one-line CLAUDE.md pointer in the Shell Commands section.
