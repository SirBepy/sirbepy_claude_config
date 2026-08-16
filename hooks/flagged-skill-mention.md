# flagged-skill-mention match scope: measurement (todo 342, 2026-08-16)

Settles the scope question todo 332 left open, by measurement against real
session transcripts on this machine, per the hook doctrine in
`.claude/todos/PLAN.md`.

## Corpus

- Source: every `*.jsonl` transcript under `C:\Users\tecno\.claude\projects\`.
- 2574 files, 503026 total JSONL lines.
- 7128 genuine Joe-typed prompts extracted (`type == "user"`, `role == "user"`,
  `isSidechain` false, `message.content` a plain string - excludes tool
  results, subagent sidechain turns, and attachments).
- Of those, 1101 prompts contained a literal `/flagged-skill-name` token for
  one of the 37 skills with `disable-model-invocation: true`.

## Classification of the 1101 matches

- **300** already matched on line 1 (today's `first_line` scope catches these
  regardless of any change).
- **586** were not real free-typed invocation candidates either way:
  - **455** were Claude Code's own `<command-message>/<command-name>` slash
    dispatch template - literal `/close` etc. typed via the CLI's native
    command autocomplete, which Claude Code executes directly; this hook
    firing or not on these is moot.
  - **131** were `<task-notification>`/`<auq-answer/>` wrapped bodies (task
    completion relays, answered question-card echoes) - bot/CLI-generated
    envelopes, not Joe typing an invocation.
  - **6** more (found further down, no separate leading tag) were bracket
    `[tag]` peer/daemon envelopes already caught by todo 332's guard.
- **509** were genuine Joe-typed prompts mentioning a flagged skill:
  - **493 true invocations** (Joe wants the skill run), of which:
    - 300 on line 1 (`first_line` already catches).
    - 74 on a later line but starting that line, e.g.
      `"lets finish off all of the todos!!!\n/auto-do-todos \nbut first..."`.
    - 119 mid-sentence, e.g. `"so basically use /clockify-reconciliator but
      for this fibo project"`.
  - **16 false positives**: Joe discussing or asking about a skill, not
    invoking it, e.g. `"do we rly need both /flutter-cicd and
    /setup-flutter-cicd? sounds like a duplicate?"`, `"myb update the
    /flutter-bump skill to make sure to handle that too?"`. All 16 were
    mid-sentence, none were line-starts.

## Scope comparison (denominator: 493 true invocations / 16 false positives / 131 synthetic bodies)

| Scope | True invocations caught | False positives fired | Fires inside the 131 task-notification/auq-answer bodies? |
|---|---|---|---|
| `first_line` (today) | 300 / 493 | 0 / 16 | No |
| `whole_prompt` | 493 / 493 | 16 / 16 | **Yes - all 131**, 47 of which contain 2+ mentions (discussion dumps). This reproduces the exact 19KB-SKILL.md-injection bug todo 332 fixed, just via `<task-notification>`/`<auq-answer/>` wrappers instead of `[bracket]` ones, which the existing guard does not cover. |
| `first_line_or_explicit_slash_anywhere` (line starts with the mention, checked on every line) | 374 / 493 | 0 / 16 | No - measured 0 / 131 |

## Decision

Adopted `first_line_or_explicit_slash_anywhere`: match in `first_line`, OR any
line in the prompt whose trimmed content starts with `/skill-name`. It beats
`first_line` (+74 genuine catches, zero new false positives) and is safe
where `whole_prompt` is not (0/131 vs 131/131 firing inside synthetic
envelope bodies).

It still misses the 119 mid-sentence true invocations. Catching those safely
needs a rule that separates genuine mid-sentence asks from mid-sentence
discussion/feature-requests about a skill - that's a semantic judgment call,
not a mechanical one, so per doctrine it isn't shipped without its own
measurement. Left as a possible follow-up, not required by this todo.
