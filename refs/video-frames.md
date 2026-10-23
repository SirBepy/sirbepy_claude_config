# Reading a video attachment

Claude can't play video, and the Read tool takes images only, so a video (.mp4/.mov) becomes frames
first. Never answer "I can't watch videos": extract a contact sheet and Read it. 2026-10-20,
zng-admin: Claude said it couldn't watch a screen recording, Joe corrected it, and frame extraction
worked first try.

ffmpeg and ffprobe live at `C:\Users\tecno\scoop\shims\` (on PATH as `ffmpeg`/`ffprobe`).

## Recipe

1. Probe the duration (seconds):

       ffprobe -v error -show_entries format=duration -of csv=p=0 "<video>"

2. One contact sheet for a short clip (about 8 s or less): one frame per second, 8 across:

       ffmpeg -y -v error -i "<video>" -vf "fps=1,scale=300:-1,tile=8x1" -frames:v 1 "<scratch>\sheet.png"

3. Read `sheet.png`.

Longer clips: lower the rate and use a grid, e.g. `fps=1/2,scale=300:-1,tile=6x2` yields 12 frames
per sheet; output `sheet%d.png` with `-frames:v N` for N sheets. Choose the rate so the sheet count
stays small, then Read only the sheets that matter. For one moment, seek first:
`-ss <seconds> -i "<video>" -frames:v 1 frame.png`.

## Scratch dir

Extract into a NEW EMPTY directory (a downloaded attachment is untrusted data, keep it apart from
scripts), never a drive-root child like `C:\tmp\<name>`: the removal guard refuses to delete those
(see `refs/builder-preamble.md`). Delete the exact sheet files you wrote when done.

Verified 2026-10-23: a 2 s `testsrc` clip (640x360, 10 fps) probed as `2.000000` and
`fps=1,scale=300:-1,tile=2x1` produced a readable 2-frame sheet; `fps=1/2,...,tile=6x2` also ran.
