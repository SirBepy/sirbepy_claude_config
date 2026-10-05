<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=29426150 -->
<!-- duplicate-checked -->
# Two orchestration papercuts: `Explore` scouts have no Write tool (the doctrine's "scout writes the spec pack" fails silently), and `commit-pathspec.sh --expect-sha` refuses a short sha

**Type:** task
**Origin:** ai

## Goal

`refs/delegation-doctrine.md` "Scout before builder" says which agent type a spec-pack-writing scout must use (the `Explore` type strips `Write`, so a read-only scout that must persist a file under `docs/research/` needs `general-purpose` with an explicit OFF LIMITS list, or the orchestrator writes the file from the report), and `skills/commit/commit-pathspec.sh` accepts a 7-char `--expect-sha` (resolving it with `git rev-parse` before comparing) or its refusal message says the full sha is required.

## Context

Head Soccer autopilot session 51bc2e71, 2026-09-12: three of four `subagent_type: Explore` scouts asked to write `docs/research/spec-pack-*.md` reported "no Write tool" (one confirmed it via ToolSearch) and returned the pack inline, so the orchestrator had to rewrite 12 to 14 KB by hand each time (two other Explore scouts did write their files, so the tool set may vary by harness build; the failure mode is the same either way: the doctrine names a mechanism the agent type cannot use). Separately, the first `commit-pathspec.sh --expect-sha 105355b` call was refused by the head guard with "expected 105355b, HEAD is now 105355b1007a..." because the comparison is a string equality on the full sha; the handoff had passed the short form.

## Approach

1. Doctrine: one sentence under "Scout before builder": use `general-purpose` for a scout that must write, or accept the inline pack and have the orchestrator write it; `Explore` is search-only.
2. Script: `expect=$(git -C "$repo" rev-parse "$expect" 2>/dev/null || echo "$expect")` before the HEAD comparison, plus a test in `skills/commit/test_commit_pathspec.sh`.
3. `skills/commit/SKILL.md` step 8: correct the documented invocation to the script's real required signature, `--expect-branch <branch> --expect-sha <sha> -m "<message>" -- <files>`. As written it shows `bash ~/.claude/skills/commit/commit-pathspec.sh -m "<message>" -- <files>`, which exits 2 with `ERROR: --expect-branch, --expect-sha, -m and -- <files> are all required`.
4. Same step: the own-range flag is spelled `--own` in the prose (inherited from `foreign-hunk-check.sh`, where that IS the name) but `--own-range` in `commit-pathspec.sh`. Name both explicitly so a caller does not have to fail once to learn which is which.

## Context, second visit

2026-09-24, claude_usage_in_taskbar session 3d7a6d6a: both papercuts in items 3 and 4 cost one failed invocation each on a routine single-file commit, before the third call succeeded. The script itself behaved correctly every time; only the documented signature is wrong.

## Acceptance

- `bash skills/commit/commit-pathspec.sh --expect-sha <7 chars> ...` passes the head guard when HEAD matches.
- The doctrine names the agent type for a writing scout.
- A first-time caller can copy the invocation out of `skills/commit/SKILL.md` step 8 and have it exit 0 without a flag-name retry.
