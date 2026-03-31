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

Ask which skill to validate. Read its SKILL.md and run the full checklist below. Show a report with pass/fail for each rule, then ask:

- "Apply all fixes automatically"
- "Show me each fix and I'll approve"
- "Just show the report, I'll fix manually"

---

## Mode 3 - Validate all skills

Read every SKILL.md in `~/.claude/skills/`. Run the validation checklist on each one. Print a summary table:

```
Skill                 Issues
/commit               none
/portfolio-data       missing one-liner
/favicon              description too long
...
```

Then ask:

- "Fix all issues automatically"
- "Fix one by one"
- "Just show the report"

---

## Bepy skill conventions

Every skill MUST follow these rules. These are the validation checklist:

### Structure

- [ ] Frontmatter exists with `name` and `description` fields
- [ ] `description` is one sentence, under 120 chars, starts with "Triggers on /skill-name only" for slash-command skills
- [ ] First line after frontmatter is `# /skill-name`
- [ ] Second line is `> one liner description of what the skill does`
- [ ] One-liner is under 80 chars

### Content

- [ ] No em dashes anywhere - use commas, colons, or hyphens instead
- [ ] No duplicate content that already exists in another skill - reference instead
- [ ] No unnecessary examples of things that are obvious
- [ ] Steps are clearly numbered and named
- [ ] Each step does one thing
- [ ] No over-specification - if Claude can figure it out, don't spell it out

### Length

- [ ] Under 150 lines total
- [ ] No section that could be cut without losing meaning
- [ ] No repeated information across sections

### References

- [ ] If the skill depends on another skill's conventions, it references that skill by name instead of duplicating rules
- [ ] If the skill uses a script, the script path and usage is clearly stated

---

## When creating or fixing

- Never use em dashes
- Keep descriptions slash-command focused and trigger-specific
- Prefer compact tables over bullet lists where possible
- When in doubt, cut - a shorter skill is almost always better
- Reference other skills rather than repeating their rules
- Always show the result to the user before writing to disk
