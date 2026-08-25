---
name: bepy-skill-creator
description: Creates a new skill or validates/fixes an existing skill (or all skills) against bepy conventions - frontmatter, structure, description budget, global-mandate compliance.
disable-model-invocation: true
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

- "Global (~/.claude/skills/<name>/SKILL.md)"
- "Project-level (.claude/skills/<name>/SKILL.md)"

Generate the skill following the conventions below. Before writing to disk, run the **Description budget gate** (see "When creating or fixing"). Then write immediately - do not ask for review first; the dev will tell you what to change after.

---

## Mode 2 - Validate and improve an existing skill

Ask which skill to validate. Read its SKILL.md and run the full checklist below. Show a report with FAIL/WARN/PASS for each rule, then ask:

- "Apply all fixes automatically"
- "Show me each fix and I'll approve"
- "Just show the report, I'll fix manually"

---

## Mode 3 - Validate all skills

Read every SKILL.md in `~/.claude/skills/` via a subagent (fleet-wide reads are context-heavy; dispatch, don't read inline), one `model: 'sonnet'` dispatch per batch. Paste the canonical preamble from `refs/builder-preamble.md` into each dispatch prompt (it's read-only, so the `READ-ONLY DISPATCH` opt-out applies) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers. Run the validation checklist on each one. Print a summary table:

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

## Eval handoff - after any fix that changes behavior

This skill checks conformance to conventions. It cannot tell whether an edit made a skill BETTER at
its job, and it must not claim to. That question belongs to the eval harness.

After applying fixes in Mode 2, check whether the skill has `skills/<name>/evals/evals.json`:

- **It does** - tell the dev the exact before/after commands and let them decide whether to spend it
  (a pass costs real money, roughly $0.20 per fixture per side):

  ```
  python tools/skill_eval.py --skill <name> --label <before-label> --parent <prior label>
  ```

  Run the baseline BEFORE the edit when possible; `history.json` records the won/lost verdict and
  refuses to compare two runs whose fixture set changed.

- **It does not** - say so plainly rather than implying the fixes are verified. A convention fix with
  no eval behind it is unmeasured, and `/rate-it` is currently the only skill with fixtures.

Never invent a pass rate, and never grade a skill's output yourself in the same session that edited
it: the harness spawns a separate tool-less process for exactly that reason.

---

## Validation checklist

Rules are split into two severity levels. FAIL means the skill has a real problem that will hurt agent effectiveness or break conventions. WARN means it's worth flagging but might be intentional.

### FAIL rules (must fix)

- [ ] Frontmatter exists with `name` and `description` fields
- [ ] If the skill accepts arguments or subcommands, `argument-hint` is set in frontmatter (e.g. `argument-hint: "[on|off|push]"` or `argument-hint: "<ticket-id>"`). Skipped only if the skill takes no args.
- [ ] A slash-only skill (description says or means "Triggers on /X only", no natural-language trigger) has `disable-model-invocation: true` in frontmatter. **Critical exception: if any other skill invokes this one via the Skill tool (skill-to-skill call), do NOT add the field** - model invocation includes those calls, and the field would break the chain. Check for inbound callers before flagging this FAIL.
- [ ] First line after frontmatter is `# /skill-name`
- [ ] Second line is `> one liner description`
- [ ] No em dashes anywhere, use commas, colons, or hyphens instead
- [ ] No true duplicate content (same info repeated in two places within the skill)
- [ ] Steps are clearly numbered and named
- [ ] Each step does one thing
- [ ] If the skill depends on another skill's conventions, it references that skill by name instead of duplicating rules
- [ ] No hardcoded user names (e.g. "Joe"). Use "the dev", "the user", or "you" instead. Personal names leak identity and reduce portability.
- [ ] Every Agent tool dispatch the skill specifies pins `model: 'sonnet'` explicitly (never inherits the session model)
- [ ] Every subagent dispatch prompt includes the subagents-never-commit boilerplate: "Stage your changes but do NOT commit. The main agent will run `/commit` after your report-back."
- [ ] Comment-density guidance for any code the skill generates respects the global cap (2 lines typical, 4-line hard cap per block; under ~25% of added lines once a file adds 20+)

### WARN rules (flag but don't force)

- [ ] `description` is within the budget gate (~25 words / 120 chars), unless a trigger keyword forces it over - see the Description budget gate below
- [ ] Description ideally starts with "Triggers on /skill-name only" for slash-command skills, but alternative phrasing is fine if the trigger intent is clear
- [ ] One-liner is ideally under 80 chars
- [ ] Ideally under 150 lines total, but longer is fine if the extra detail helps the agent
- [ ] Check for sections that could be cut, but don't flag sections that serve a distinct purpose even if they look similar to another section (e.g., a standalone planning gate that catches casual requests vs a gate check inside a command flow)
- [ ] No unnecessary examples of things the agent can figure out, but detailed examples that ensure consistency (like hex colors, specific error messages) are fine
- [ ] If the skill uses a script, the script path and usage is clearly stated
- [ ] Heavy flag flows live in adjacent sidecar files. A flag's rules belong in `<flag-name>.md` next to `SKILL.md` if it materially changes the flow OR its body has its own heading and contains imperative steps. SKILL.md keeps only a single pointer line per offloaded flag: `If <flag>: read <file> before proceeding.` Lighter flags stay inline.
- [ ] Sidecar count is bounded. If a single skill needs 4+ sidecars, the skill itself is too broad - flag it for a split or simplification rather than spawning more files.

### Report format

Show the report as a table with three columns: Rule, Status (FAIL/WARN/PASS), Issue. Group by severity with FAILs first.

---

## When creating or fixing

### Frontmatter surface (modern fields)

- `disable-model-invocation: true` - skill is user-only (slash command, no NL trigger); drops it from the model-facing listing. Skip if any other skill calls it via the Skill tool.
- `user-invocable: false` - skill is background knowledge only; the model can pull it in but the dev never types the slash command.
- `allowed-tools: Tool, Tool` - restricts which tools the skill may use once invoked; set when a skill should never touch tools outside a narrow set.
- `context: fork` - runs the skill in an isolated subagent instead of the main thread; use for read-heavy or side-effect-risky flows that shouldn't burn main context.
- `agent: <type>` - pins which agent type handles the fork (e.g. `Explore`); only meaningful alongside `context: fork`.

### Description budget gate (enforced on create and on fix)

The `description` loads into the system prompt every session, so verbosity there is a per-session token cost. Before writing any skill:

1. Count the words in the `description`. Budget: <= 25 words / 120 chars.
2. If over budget, cut restated mechanics, examples, and filler - keeping every trigger clause verbatim in meaning (the `/name` trigger and all when-to-use keywords that make the skill fire).
3. If it cannot reach budget without dropping a trigger keyword, keep it over budget and note which keyword forced it. Never truncate blindly - a broken trigger costs far more than the saved tokens.

- Never use em dashes
- Never reference users by name; use "the dev"
- Keep descriptions slash-command focused and trigger-specific
- If the skill takes args or subcommands, include `argument-hint` in frontmatter. Use `[a|b|c]` for enum-ish choices, `<name>` for required free-form values. Skill autocomplete shows this hint after the slash command.
- Prefer compact tables over bullet lists where possible
- When cutting for length, always ask: "does removing this make the agent less effective?" If yes, keep it.
- Reference other skills rather than repeating their rules
- Always write the result to disk immediately. Never ask for review first; the dev will tell you what to change after.
