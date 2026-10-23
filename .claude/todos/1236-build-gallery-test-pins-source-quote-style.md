<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/1230 added the test; no live todo covers it -->
# test_build_gallery.py proves the single render-URL site by counting a source substring

**Type:** task
**Origin:** ai

## Goal

The test that `build_gallery.py` forms the preview render URL in one place checks behaviour, not
the spelling of one source line.

## Context

Found by the 2026-10-23 loop-todos cycle-2 `/code-check` over `7269733..HEAD`.
`skills/preview/test_build_gallery.py:259` asserts `source.count(".rstrip('/')") == 1` on
`build_gallery.py`. A quote-style change (`rstrip("/")`) or any unrelated `rstrip('/')` elsewhere
flips it, and a second URL join spelled differently evades it. It exists because the `--check` call
site in `main()` needs a live render daemon plus chromium.

## Approach

Make the `--check` path testable without a daemon: monkeypatch `post_render_check` (or the HTTP
call under it) in-process and assert the URL it is handed comes from `render_url`, or patch
`render_url` and assert both call sites hit it. Then drop the substring count.

## Acceptance

- The substring-count check is gone; a behavioural check covers both call sites.
- `python skills/preview/test_build_gallery.py` and `python tools/test_build_gallery.py` pass.
