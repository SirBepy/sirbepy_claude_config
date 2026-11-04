<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard's hits, done pc-0935 (stale test pointer) and done pc-1000 (attributing a red test), only share vocabulary. A search of the backlog for narration, recordVideo and text to speech found no existing todo. -->
# Recorded test report: every longer browser test produces a narrated deck, switchable per project

**Type:** skill-improvement
**Origin:** dev
**Summary:** Turn the Biller Groups demo's scripts into a reusable tool that records a longer test and builds a watchable report, with local text-to-speech narration, on by default per project.

## Goal

A longer browser test run ends with a self-contained report Joe can watch in the Conductor preview panel, without Claude spending much to make it. The first real run measures the added cost against the estimate below.

## Context

2026-11-04, zng-app, session 6dcb769b-ec5c-48c6-8f82-b14653f9548c. Joe saw the Biller Groups deck and said these reports "could be stupidly helpful".

Starting point, tied to that demo and gitignored in zng-app: `C:\Users\tecno\Desktop\Projects\zng-app\.for_bepy\presentation\demo-src\` (`lib.cjs` recording helpers with fake cursor and captions, `rec-*.cjs` takes, `build-deck.cjs`, `check-deck.cjs`). Copy what is useful out of there before that folder is cleaned up. Result: `..\biller-groups-feature-demo.html`.

Measured cost of that deck: 97,555 output tokens, 15.3M cache read, 303K cache write over 70 Opus 5.5 calls, about 219K context per call. About $12 at assumed, unchecked API rates. Most of it was one-time discovery. Claude's unmeasured estimate for a report added to a test whose flows are already scripted: $1-2.

## Joe's requirements

**When a report is made (his answer, 2026-11-04):** every longer test, enabled or disabled per project. zng repos: always. Personal projects: rarely, so off by default there.

1. **Spoken narration.** A tool reads out the captions, using a free local model. It must always finish a line before the next one starts. Joe: "we gotta make sure that works properly".
2. **Subtitles higher up,** so the video's progress bar never covers them.
3. **Player:** full screen, and click the video to pause or play.
4. **Styling:**
   - Next button at the bottom right.
   - The step list is smaller and scrollable, not a huge full-height list.
   - The list auto-scrolls and highlights the current step as the video plays.

## Approach

- **Recording:** Playwright `recordVideo` during the test. Captions and the pass or fail rows come from the test's step names, so most of the report costs no tokens. Claude only writes the first slide (what Joe needs to know), a short explanation per surface, and checks frames by eye. Consider a narrow Sonnet subagent for that part.
- **Narration sync:** make the speech first, measure each clip's length, and hold each caption on screen for that long during recording, so a line can never be cut off. Speeding the video up afterwards would break this, so narrated takes should not be sped up. Check for overlap in the final file by measuring it, not by assuming.
- **Text to speech:** Piper and Kokoro are candidates from memory, UNVERIFIED. Run the packages safety check before adding one.
- **Size:** the preview push caps at about 2MB. The silent deck was 1.37MB with 248s of video at VP9 crf 50, 8fps, 1000px wide, so audio may not fit. Decide between a page per surface, or a lower bitrate.
- **Full screen:** the deck uses native `<video controls>`, which already has a full screen button, and Joe still asked for it. Check whether the panel's sandboxed frame blocks full screen. If it does, that part is a Conductor app change. Click to pause needs a small handler, and it must not double-toggle if the browser already does this.
- **Per-project switch:** decide where it lives (project `CLAUDE.md` line or an imported snippet) and what counts as a "longer test".
- **Deck content rules:** memory `feedback_feature_reports_fe_first_show_it_working` in the zng-app project.

## State, 2026-11-04

Built: `skills/test-report/` (recorder, Kokoro voice, encode, template, build, check, push), the switch in `refs/test-report-repos.txt`, the rule in global `CLAUDE.md`. The Biller Groups deck was re-recorded with it and pushed to the zng-app chat's panel: 29 of 29 steps, 0 overlaps measured across 53 line boundaries, 27 of 27 player checks in a frame sandboxed like the panel's. Measured cost of a small run: about $0.29 and 83 seconds in a Sonnet subagent, with the cache write rate assumed at 1.25x input.

Still open: Joe's confirmation in the real panel of the voice and click to pause, and real full screen, which needs Conductor's pc-1606 (`claude_usage_in_taskbar` backlog). The same todo raises the 2MiB page cap. Afterwards raise `MAX_BYTES` in `build-report.cjs`.

## Done when

- A zng repo's longer test run produces the report with no extra request from Joe, and a personal project does not unless switched on.
- All 4 requirements hold in the Conductor panel itself, not only in a headless browser. The Biller Groups playback check only ran headless.
- No two narration lines overlap in a real output file.
- The added cost of one real run is measured and reported to Joe.


## Notes

- Finished 2026-11-04: Joe confirmed the voice and click to pause in the panel, and accepted full screen filling the window for now (Conductor's pc-1606 stays in that repo's backlog). Skill commits f75775f and 70de46f. The CLAUDE.md rule line is active but uncommitted, because another chat's uncommitted line shares the file.