<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=bcc64eeb -->
# Pin the exact weekly-screenshot URL and framing in clockify-reconciliator

**Type:** skill-improvement

## Goal

Make step 12 of `/clockify-reconciliator` produce the screenshot Joe actually wants on the first try, without a correction round.

## Context

On 2026-07-26 the close-out screenshot was taken twice and corrected once.

1. Joe asked for a shot showing "not just duration but also the actual time slots". The skill's step 12 URL (the weekly view) shows durations only, so I substituted the Calendar view. Joe rejected it: "you shouldve taken the screenshot from this url" and supplied
   `https://app.hubstaff.com/organizations/410414/time_entries/weekly?date=2026-07-20&date_end=2026-07-26&filters%5Buser%5D=4023312&filters%5BshowWeeklycopy%5D=`
   The `&filters%5BshowWeeklycopy%5D=` param is not in the skill file at all.
2. At the skill's prescribed ~1600x1000 viewport the grid's rightmost **Total** column is clipped behind a horizontal scrollbar, so the week total is unreadable in the image.

Related standing lesson: [[feedback-follow-skill-specified-artifacts]].

## Approach

Edit `~/.claude/skills/clockify-reconciliator/SKILL.md` step 12 (note: hardlinked to `~/.claude-personal/skills/...`, editing one edits both - verify with an inode/size check after saving):

- Replace the URL template with the `showWeeklycopy` variant above, parameterised on org/user/date.
- Replace "Resize viewport to ~1600x1000" with: viewport width >= 2300, collapse the left nav first (click the leaf element whose text is `left_panel_close`), then clip the screenshot to the grid region rather than `fullPage`, so there is no large empty area below the two rows.
- Keep the existing >50 KB size sanity check.
- Add one line noting the Calendar view (`/time_entries/calendar?...`) as the place to READ per-slot boundaries when verifying alignment, explicitly not as the screenshot source.

## Acceptance

- A fresh `/clockify-reconciliator zirtue` run writes `hubstaff-weekly-<mon>_to_<sun>.png` to the Desktop showing all seven day columns AND the Total column, with no correction needed.
- File size > 50 KB.
- Both hardlinked copies of SKILL.md reflect the change.

## Notes

Working reference implementation from this session: `c:/tmp/hs_weekly_copy2.cjs` (may be cleared by tmp cleanup; the approach above is sufficient to rebuild it).
- completed, commit 22b597a
