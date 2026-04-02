---
name: bepy-skill-creator
description: Triggers on /bepy-skill-creator only.
---

# /bepy-skill-creator

> Create, validate, and improve skills following bepy conventions.

## Modes

When triggered, ask using AskUserQuestion:

- "Create a new skill"
- "Validate and improve an existing skill"
- "Validate all skills"

---

## Mode 1 - Create a new skill

Ask the user using AskUserQuestion and open-ended follow-up if needed:

1. What should the skill be called? (becomes the slash command name)
2. What should it do in one sentence?
3. Any specific rules or context needed?

Then ask: where should it live?

- "Global (~/.claude/skills/)"
- "Project-level (.claude/commands/)"

Generate the skill following the conventions below, then show it to the user for review before writing to disk.

---

## Mode 2 - Validate and improve an existing skill

Ask which skill to validate. Read its SKILL.md and run the full checklist below. Show a report with FAIL/WARN/PASS for each rule, then ask:

- "Apply all fixes automatically"
- "Show me each fix and I'll approve"
- "Just show the report, I'll fix manually"

---

## Mode 3 - Validate all skills

Read every SKILL.md in `~/.claude/skills/`. Run the validation checklist on each one. Print a summary table:

```
Skill                 Fails  Warns
/commit               0      0
/portfolio-data       1      1
/favicon              0      2
...
```

Then ask:

- "Fix all issues automatically"
- "Fix one by one"
- "Just show the report"

---

## Validation checklist

Rules are split into two severity levels. FAIL means the skill has a real problem that will hurt agent effectiveness or break conventions. WARN means it's worth flagging but might be intentional.

### FAIL rules (must fix)

- [ ] Frontmatter exists with `name` and `description` fields
- [ ] First line after frontmatter is `# /skill-name`
- [ ] Second line is `> one liner description`
- [ ] No em dashes anywhere, use commas, colons, or hyphens instead
- [ ] No true duplicate content (same info repeated in two places within the skill)
- [ ] Steps are clearly numbered and named
- [ ] Each step does one thing
- [ ] If the skill depends on another skill's conventions, it references that skill by name instead of duplicating rules

### WARN rules (flag but don't force)

- [ ] `description` is ideally one sentence under 120 chars, but longer is fine if it improves agent triggering
- [ ] Description ideally starts with "Triggers on /skill-name only" for slash-command skills, but alternative phrasing is fine if the trigger intent is clear
- [ ] One-liner is ideally under 80 chars
- [ ] Ideally under 150 lines total, but longer is fine if the extra detail helps the agent
- [ ] Check for sections that could be cut, but don't flag sections that serve a distinct purpose even if they look similar to another section (e.g., a standalone planning gate that catches casual requests vs a gate check inside a command flow)
- [ ] No unnecessary examples of things the agent can figure out, but detailed examples that ensure consistency (like hex colors, specific error messages) are fine
- [ ] If the skill uses a script, the script path and usage is clearly stated

### Report format

Show the report as a table with three columns: Rule, Status (FAIL/WARN/PASS), Issue. Group by severity with FAILs first.

---

## When creating or fixing

- Never use em dashes
- Keep descriptions slash-command focused and trigger-specific
- Prefer compact tables over bullet lists where possible
- When cutting for length, always ask: "does removing this make the agent less effective?" If yes, keep it.
- Reference other skills rather than repeating their rules
- Always show the result to the user before writing to disk
