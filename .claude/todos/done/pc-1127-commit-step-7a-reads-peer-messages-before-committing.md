<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 890 (done) is /handoff checking peers before calling work unstarted; 1124 is --force foreign-hunk sweeping peer lines. Neither covers /commit never calling read_messages -->
# /commit's peer check posts to the channel but never reads it, so a peer's "stop" is missed

**Type:** skill-improvement
**Origin:** ai

## Goal

Before a commit (and before any deploy/staging step that follows it), Claude has read every
unread peer message on the project channel, so a peer's "stop / don't ship this" is acted on
before the commit lands, not after.

## Context

2026-10-07, mc_plugins_tag, session 71d6 (cartel "Marco's pistol" Shenron wish). The Player
Claude listener posted, targeted at 71d6, at 20:28 ("don't stage until the player answers"),
20:36 ("he REFUSED, don't commit to main"), 20:38 and 20:44 UTC ("URGENT, third time"). 71d6
followed `/commit` step 7a: it called `list_peers`, then `post_message` naming the pathspec at
20:38, and never called `read_messages`. It committed 30b1c43 and 8049126, pushed the server pack
to the site repo, and staged the jar on live before seeing any of those messages. It saw them only
when the next daemon-meta relay made it read the channel. A later Joe override made the work moot,
but the refused change had already been published.

The `read_messages` tool description says to call it "before editing or committing, alongside
list_peers". `skills/commit/SKILL.md` step 7a names only `list_peers` and `post_message`.

## Approach

Edit `skills/commit/SKILL.md` step 7a: when `list_peers` shows another active session, also call
`read_messages` before `post_message`, and stop if any message addresses this session or names a
file in the pathspec, the feature, or "stop/hold/don't commit". Then decide: proceed, narrow the
pathspec, or stop and ask. Consider a matching line in the Push pipeline (before `git push`) and
in `refs/builder-preamble.md` for deploy-style steps (uploads to live, publishing).

## Acceptance

- `/commit` step 7a names `read_messages` explicitly, with the stop condition above.
- Reading the updated step, a cold session that has a peer message "don't commit X" queued would
  read it before committing X.

## Notes

- commit SKILL.md step 7a now calls read_messages first on every commit (not gated on list_peers, which underreports), with the stop condition (addresses this session, names a pathspec file or the feature, or says stop/hold/don't commit), and repeats it before git push and deploy-style steps.
