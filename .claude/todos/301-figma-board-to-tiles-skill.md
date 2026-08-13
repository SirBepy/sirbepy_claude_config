<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Skill candidate: turn a Figma board into readable per-screen tiles

**Type:** skill-improvement
**Origin:** ai

## Goal

Package the "get a Figma design board in front of Claude's eyes" workflow as a skill, instead of
re-deriving it from scratch each time a design review comes up.

## Context

Built from nothing on 2026-08-12 in `zng-app`, during a review of the lenderless loan flow. It took
three separate script rewrites to get right, and the first attempt cost Joe's Figma REST quota for
several days. That is a lot of wasted effort to repeat.

The working pipeline, once the dead ends were removed:

1. Resolve the section ids from a share URL (`node-id=7315-510278` becomes `7315:510278`).
2. Fetch the tree **per section at depth 2 or 3, never a whole page at depth 6**. The deep read is
   what exhausted the quota: `Retry-After: 233999` on the files endpoint, then `397845` on images,
   from a single request.
3. Render each phone frame at scale 2 through `/v1/images`, which is a separate quota from
   `/v1/files`.
4. If the API is unavailable, have the dev export the section as a PNG from the desktop app and
   slice it locally instead. This path needs no API at all.
5. Slicing that actually works: mask against the sampled canvas colour rather than hunting for
   white; trim the section's own outline first or it bridges every row and column into one box;
   split recursively alternating rows and columns, because connector arrows defeat naive
   projections; upscale tiles under 500px wide by 2x; cut tall scroll mockups into overlapping
   1750px strips so text stays legible.
6. Pull `/v1/files/:key/comments` and flatten it into threaded markdown. On that file it held 130
   threads of decisions that had never reached a ticket, and turned out to be the single highest
   value artifact of the session.
7. Fan subagents out over the tiles for screen-by-screen review.

Working implementations to lift, all in `zng-app` at `.for_bepy/figma/`: `slice_any.py` (generic,
detection only), `crop_export.py` (exact, uses cached node boxes), `comments_digest.py`,
`sweep.py` (the API path, including the backoff that was added after the first 429).

## Approach

1. Read those four scripts and merge them into one entry point that takes a Figma URL or a local
   export, and produces a tile folder plus a comments digest.
2. Write the SKILL.md around the quota rules, since those are the part that bites: depth limits,
   which endpoints share a budget, and the export fallback.
3. Note the Figma desktop Dev Mode MCP (`127.0.0.1:3845`) as the unmetered alternative, with the
   caveat that it is selection-driven and cannot sweep a board.

## Acceptance

- One invocation turns a board into legible per-screen tiles plus the comment threads.
- The quota rules are enforced by the tool, not left to the operator to remember.

## Notes

Do not do this work from inside a project session. It belongs to a session working on
`C:\Users\tecno\.claude` itself. See `reference_figma_access_and_quota` in the zng-app project
memory for the full incident record.

- Renumbered 288 -> 301 on 2026-08-13 (todo 286): id 288 was claimed by two different files. The other file kept it because it was filed earlier. Any older reference to todo 288 may mean this one.
