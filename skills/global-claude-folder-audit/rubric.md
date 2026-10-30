# Global ~/.claude audit rubric - run <YYYY-MM-DD>

You are one of ~20 parallel auditors sweeping the dev's global Claude Code config repo at
`C:\Users\tecno\.claude`. You own ONE slice. Read it properly, judge it hard, report findings.

## Hard constraints

- **Read only, except your one report file.** Do not edit, create, or delete any file other than
  the report path your dispatch names. No `git add`, no commit, no `git stash/reset/checkout`.
- Never run the repo's CI (`ci/run_all.py`), hook test suites, or any long-running command. Cheap
  read-only shell is fine: `cat`, `sed -n`, `grep`/`rg` scoped to a folder, `wc`, `ls`, `git log`,
  `git show`. Never grep from `C:\`, `$HOME` or `C:\Users\tecno` recursively: scope to
  `C:\Users\tecno\.claude\<subdir>`. A whole-tree recursive grep of this repo times out.
- Do not start any long-lived process. Do not background anything.
- Before calling a file an orphan, also grep the dev's auto-memory directory and `git log` for it:
  memories point at refs by path, and a file a memory cites is not dead.

## What counts as a finding

A concrete defect, risk, or cost a competent reviewer would want fixed. Not a style opinion, not a
restatement of what the file does.

**Every finding needs a receipt: `path:line` you actually read in this dispatch.** No receipt, no
finding. A suspicion you cannot prove from your slice gets labelled `UNVERIFIED:` plus the file that
would settle it. Ten real findings beat forty soft ones. A healthy slice says so.

## Prior-decision check (before reporting anything)

1. `skills/global-claude-folder-audit/ledger.md` lists what earlier audits deleted or the dev
   declined. Never re-propose those.
2. The dev keeps some overlapping skills separate on purpose for autocomplete (he rejected merging
   `cleanup-todos` / `auto-do-todos` into `batch-todos`, 2026-08-01) and keeps aliases left by
   earlier merges (`test-flow`, `obsidian-pickup-ticket`, `setup-flutter-cicd`). A merge or delete
   finding must name a cost beyond one extra autocomplete entry.
3. Grep `.claude/todos/*.md` (live backlog) and `.claude/todos/done/` for the file or subject. Live
   todo already covers it: one line citing the todo id, not a new finding. Done but the defect is
   still there: that IS a finding (the fix did not land or regressed).

## Your lens

Read `skills/global-claude-folder-audit/lens.md` in full and apply all of it to your slice, with its
severity scale. Also apply `skills/bepy-skill-creator/SKILL.md`'s "Validation checklist" FAIL rules
to any SKILL.md in your slice, reporting only the FAILs that matter to an agent following the skill.

## Report format

Write your report to the path in your dispatch, markdown, in this exact shape:

```
## SLICE: <slice name>

### <SEVERITY> | <short title, under 70 chars>
- **Where:** `path/to/file:123` (and `other/file:45`)
- **What:** one sentence stating the defect.
- **Why it matters:** the concrete failure or cost, with a trigger.
- **Fix:** what to do, 1-3 sentences.
- **Verdict:** keep | merge into <X> | delete | rewrite | fix   (skill-level findings only)
- **Confidence:** high | medium | low
- **Effort:** S | M | L
- **Lens:** trigger | merge | drift | clarity | weight | research

### ... (repeat)

## Skill verdicts
One line per skill in your slice: `<skill> - keep | merge into X | delete | rewrite - <reason, with usage numbers>`.
(Skip for slices that own no skills.)

## Slice health
Two or three sentences: what is good, the single worst thing.

## Genuinely good
At least two specific things worth keeping, with receipts.

## Out-of-slice observations
One line each, with a path. Do not investigate.
```

Your final chat message (your return value) is SHORT, max 15 lines: severity counts, the titles
of every CRITICAL and HIGH, and every delete/merge verdict. The orchestrator reads the file for detail.

## Project context (the orchestrator fills this in per run)

- **What this is:** the dev's global Claude Code config: skills under `skills/`, global rules in
  `CLAUDE.md` (always loaded) plus `refs/`, `snippets/`, `code-style/`, `context/` read on demand,
  Python hooks under `hooks/` wired in `settings.json`, `agents/`, offline `tools/`, `ci/`.
  Fill in current counts.
- **Who uses it:** one developer, many concurrent Claude sessions across dozens of repos (personal
  and client). Always-loaded token cost and per-tool-call hook latency are multiplied costs, and a
  broken shared hook takes shell access from every live session.
- **Usage data:** `<run folder>/usage.json`. State its window and known undercounts (sessions run
  under other config dirs, compressed transcripts). Zero means "no evidence of use in the window".
- **Vendored skills:** list them; judge only keep-installed vs remove and overlap.
- **Slash-only flag:** `disable-model-invocation: true` skills cost nothing in the listing.
- **Last audit:** from the ledger.
