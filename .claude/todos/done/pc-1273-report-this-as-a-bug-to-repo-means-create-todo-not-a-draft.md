<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the grep hits (pc-1206 write-draft rule for ticket comments, pc-1252 duplicate drafts, pc-1250 kickoff unsent drafts) are about the Drafts panel itself, none about "report this to a repo" meaning a backlog todo -->
# "Report this as a bug to <Joe's own repo>" should file a cross-repo todo, not a Drafts-panel message

**Type:** skill-improvement
**Origin:** ai
**Summary:** When Joe says to report a bug or issue to one of his own repos (claude-conductor above all), Claude files it with /create-todo in that repo's backlog and does not write a Drafts-panel message.

## Why

Joe, 2026-10-29, after Claude wrote a bug report to the Drafts panel: "lol why did you write it to me as a draft, thats new...? ... no, i wanted you to write it to me as /create-todo in that repo".

## Goal

Claude has a written rule that "report this to <repo>" for a repo Joe owns (his own projects, claude-conductor) means the cross-repo `/create-todo` flow, so the Conductor system-prompt rule "a message for Joe to send somewhere else goes in the Drafts panel" is not applied to it.

## Context

- The Conductor system prompt tells Claude to put any message "whose recipient is not this chat" into `write_draft`. A bug report to a repo of Joe's own matched that wording in the 2026-10-29 zng-admin chat (session 7c4c3445-9a17-489e-beb2-f0956c9909d5): Claude wrote draft d9c1a2d7 to the GitHub platform, then Joe corrected it. The report was refiled as `pc-1492` in the Conductor repo.
- Nothing in `~/.claude/CLAUDE.md` or `skills/create-todo/SKILL.md` says which of the two applies. `create-todo` Step 0 covers "a finding whose fix lives in a different repo" but does not name bug reports to Joe's own tools.
- Where claude-conductor lives: `C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar` (remote `https://github.com/SirBepy/claude_conductor.git`, read from `git remote -v` on 2026-10-29). Its backlog is `.claude/todos/` there (75 open todos at that time).
- The Drafts panel stays right for messages to other people (Slack, tickets) per the system prompt; only reports into Joe's own repos change.

## Approach

1. Add one bullet to `~/.claude/CLAUDE.md` (it has a token ratchet, `ci/check_instruction_budget.py`) or to the `create-todo` skill's Step 0: a bug or feature report to a repo Joe owns is a cross-repo todo in that repo, never a draft; claude-conductor = `claude_usage_in_taskbar`.
2. If CLAUDE.md has no headroom, put the sentence in `skills/create-todo/SKILL.md` Step 0 plus the repo mapping in a short ref, and link it from the existing Cross-repo filing paragraph.

## Acceptance

- `python ci/run_all.py` passes (including the instruction token budget).
- The rule names claude-conductor's repo path so a future session does not search for it.

## Notes

- Fixed in 5ed8cb2 (create-todo and log-conductor-todo; the optional CLAUDE.md line was skipped, 24 tokens of headroom).
