<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new defect in 64273e8's /close trigger rewrite -->
# /close: define the task-text and trailing-flag forms its argument-hint advertises

**Type:** skill-improvement
**Origin:** ai
**Summary:** Make /close say exactly which message shapes count as "do this task, then close", so `/close fix the typo` and `do X /close --now` behave predictably.

## Goal

`skills/close/SKILL.md`'s Trigger and Arg parsing sections cover every form its `argument-hint` (`[task text] [--now] ...`) advertises.

## Context

Found by the 2026-10-30 pre-push `/code-check` over 64273e8 (/close absorbed /then-close), cited from the reviewer's report:

- `skills/close/SKILL.md:4` hint vs `:26-46` Trigger/Arg parsing: only task text BEFORE a trailing `/close` is defined. `/close fix the typo` (a form the deleted /then-close supported) is undefined, because Arg parsing treats remaining args as a chain of slash commands. `do X /close --now` and `do X /close /sleep-when-done` are undefined too: Trigger requires `/close` as the first or last word, and the last word there is the flag or the chained command.
- `skills/close/SKILL.md:70` (Host app integration) says Conductor marks the row Closing "the moment a /close turn starts (it sees the prompt began with /close)" without saying a trailing `/close` does not, which `skills/gate-chat/SKILL.md` relies on.

## Approach

Decide the grammar: text before or after `/close` that is not a slash command or flag is the task; flags and chained commands after a trailing `/close` still count as the trigger. Write that into Trigger and Arg parsing, or narrow the hint to what is supported. Qualify line 70 to prompts that begin with `/close`.

## Acceptance

- Each of the three example messages above has one stated outcome in the skill text.
- `skills/release/test_pipeline_order.py` still passes.
