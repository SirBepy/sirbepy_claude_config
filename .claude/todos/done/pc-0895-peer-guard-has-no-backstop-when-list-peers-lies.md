<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The peer guard has no backstop when `list_peers` returns a false negative

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the concurrency rule a cheap second signal, so an empty `list_peers` is no longer the only
thing standing between a session and another session's uncommitted work.

## Context

Global CLAUDE.md's harness section says to call `list_peers` before editing a file another session
might touch, and `/commit` step 7a repeats it before committing. Both treat an empty result as
permission to proceed. There is no fallback if the tool is wrong.

It was wrong on 2026-09-02, in `claude_usage_in_taskbar`:

- `list_peers` returned `{"peers":[]}` twice during one session.
- Three commits landed in that window from a session that was not this one: `34a0ae39`,
  `00fc4912`, `c46dd54f`.
- `34a0ae39` swept in a 4-line working-tree edit belonging to the calling session.

The tool-side bug is filed in that repo as todo 856 (it looks like a regression from todo 503's
dead-pid expiry). This todo is the separate, harness-side half: the rule should not collapse the
moment its single sensor is wrong, and a fix landing in Conductor does not help sessions running
against an older build.

## Approach

The cheap backstop is already sitting in git, and it needs no MCP tool. Before editing a shared file
or committing, `git log` for commits in the last few minutes authored outside this session, and
compare `HEAD` against the sha this session last recorded. A HEAD that moved without this session
moving it is proof of a peer regardless of what `list_peers` says.

Candidate homes, pick one rather than adding the check in three places:

- `/commit`'s step 8 branch guard already re-reads `git rev-parse HEAD`. Widening it to "HEAD moved
  and it was not me" costs one command and covers the commit path.
- The peer-check bullet in CLAUDE.md's harness section, for the edit path.

Do not simply reword the rule to say "be careful". The failure was a sensor returning a confident
wrong answer, so the fix has to be a second sensor, not more caution.

## Acceptance

A session that runs the check while another session commits underneath it detects the peer from git
alone, with `list_peers` still returning empty. The rule names what to do on detection: announce,
narrow the pathspec, or stop.

## Notes

- Completed in /mega-todos wave 1, commit fd90f58: the pre-edit hook now persists this session's last-seen HEAD per repo and warns on a HEAD move independent of list_peers, and /commit step 8 gained a matching HEAD guard alongside the branch guard.
