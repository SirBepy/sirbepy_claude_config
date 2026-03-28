---
name: skills-help
description: Triggers on /skills-help only.
---

# /skills-help

> List all available skills with a short description of each.

## Workflow

### Step 1 - Find all skills

Read the global skills folder at `~/.claude/skills/`. List all subdirectories, each one is a skill. Read the SKILL.md file inside each one.

### Step 2 - Extract name and description

From each SKILL.md, extract:

- The `# /skill-name` line - the command name
- The `> one liner` line directly below it - the description

### Step 3 - Print the list

Print a clean list, grouped by category if obvious, otherwise alphabetical:

```
Available skills:

/commit          Commit changes into clean, well-organized commits
/commitpush      Run the full commit flow then push
/autocommit      Toggle automatic committing after each completed task
/portfolio-data  Generate or update portfolio metadata and write-up
/readme          Generate or update README.md for the project
/meta-tags       Ensure index.html has all required meta tags
/skills-help     List all available skills
...
```

No extra explanation needed. Just the list.
