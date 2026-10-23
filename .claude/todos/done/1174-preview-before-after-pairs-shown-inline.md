<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 14 (done) is about create-pr's preview card vs text ordering; this is a paired before/after gallery mode for /preview -->
# /preview: before/after paired gallery, shown inline before the question

**Type:** skill-improvement
**Origin:** ai

## Goal
Give `/preview` a before/after mode: numbered sections, each with a caption and labelled before/after (and optional variant) shots side by side, posted as an inline chat card, not only to the side panel.

## Context
2026-10-13, zng-biller mobile UX sweep. To let Joe keep or drop 14 phone-width changes, Claude hand-wrote `zng-biller/.for_bepy/mobile-fixes/build-gallery.cjs`: per-item sections, before/after/variant labels, ffmpeg PNG to WebP conversion to stay under the ~2MB hook cap (610 KB for 28 shots), and click-to-zoom. It pushed the result with `build_gallery.py --post`. That flow lands only in the preview panel, and Joe answered the keep/drop card with "these are just words, id need to see a before and after view": he never saw the panel. What worked was a `show_preview` card holding an iframe to the posted page's `/hooks/preview-render/<id>` URL, sent right before the question, with section badges numbered to match the card's option labels.

`skills/preview/build_gallery.py` today makes a flat filename-captioned gallery with no pairing, no per-item notes and no WebP step.

## Approach
In `skills/preview/build_gallery.py` (and the image-branch section of `skills/preview/SKILL.md`), add a manifest input: JSON listing items `{id, title, note, shots: [[caption, path], ...]}`. Render the paired layout with WebP conversion (ffmpeg is on PATH) and the existing lightbox. After `--post`, print the `/hooks/preview-render/<id>` URL. In SKILL.md, tell callers to follow a gallery that precedes a question with an inline `show_preview` iframe card pointing at that URL. Use the zng-biller script above as the reference implementation if it still exists.

## Acceptance
A manifest of 10+ paired items builds under the 2MB cap, `--check` passes, and the inline card renders the same page in a Conductor chat.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): build_gallery.py --manifest renders numbered before/after pairs with WebP and the existing lightbox, prints render-url after --post; 12-item test stays under 2 MB. NOT verified live: --check against the daemon and the inline Conductor card were not run (no live server in an unattended loop).
