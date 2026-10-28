<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Delegation doctrine tells subagents to stage, contradicting the never-stage rule

**Type:** skill-improvement

## Goal
Resolve the direct contradiction between the delegation doctrine's required dispatch line and Joe's never-stage rule, so dispatch prompts stop instructing subagents to do something the project forbids.

## Context
`~/.claude/refs/delegation-doctrine.md` ("Dispatch discipline") requires every builder prompt to embed verbatim: "Stage your changes but do NOT commit. The main agent will run /commit after your report-back." The same line is mandated in the global `CLAUDE.md` "Git Commits" section.

Memory `feedback_never_stage_leave_unstaged` records the opposite instruction from Joe: never stage, leave changes unstaged, because a shared `.git/index` blocks concurrent AI sessions, and `/commit` commits by pathspec anyway so staging buys nothing.

Both cannot be followed. In the sc-54911 session (2026-07-30) six dispatch prompts told subagents to stage. Nothing broke, because no concurrent session happened to be committing, but the risk the memory describes was live the whole time, and one subagent's report explicitly noted it found files staged by another agent and had to reason about whose they were.

**Second incident, 2026-08-03 (sc-55003/sc-55004) â€” this time it bit.** Four sessions shared the repo concurrently. A builder subagent staged six files per the doctrine line; the main agent had to `git restore --staged` them immediately. Separately, a `git update-ref` left a dropped commit's `_kMinHeight = 380` staged in the shared index while the working tree read 320 â€” a peer session spotted the mismatch and flagged it as an apparent edit war. Any bare `git commit` from any of the four sessions would have silently resurrected the dropped value into a production-bound branch. This is no longer a theoretical risk; raising priority.

## Approach
Decide which rule wins, then make the losing one stop existing rather than leaving both written down.

If never-stage wins (likely, since `/commit` is pathspec-based and does not need the index): edit the verbatim line in `~/.claude/refs/delegation-doctrine.md` and in the global `CLAUDE.md` "Git Commits" section to say "Leave your changes unstaged. Do NOT stage and do NOT commit. The main agent will run /commit, which commits by pathspec." Then update `feedback_never_stage_leave_unstaged` to note the doctrine now agrees.

If staging wins: delete or rewrite the memory so it does not contradict the doctrine, and state why the shared-index concern no longer applies.

## Acceptance
Grepping `~/.claude/` for "Stage your changes" returns either zero hits or only text consistent with the memory. A fresh dispatch prompt written from the doctrine no longer instructs staging, if never-stage won.

## Notes

- Shipped 2026-08-11 in commit df3d04e. The staging line is now conditional on whether the repo shares a git index with concurrent sessions, stated in both delegation-doctrine.md spots and CLAUDE.md, and <STAGING_LINE> became a fourth placeholder in the canonical builder preamble.
