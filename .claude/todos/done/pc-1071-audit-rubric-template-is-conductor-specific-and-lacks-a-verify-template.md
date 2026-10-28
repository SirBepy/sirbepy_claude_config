<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=8faa6ef6 -->
<!-- duplicate-checked: hook hits (1067, 101, 210, 216, 221) share only generic words; grep of the backlog and done/ for skills/audit and rubric-template found no todo about /audit's own files -->
# /audit's rubric template is Claude-Conductor-specific and the skill ships no refutation template

**Type:** skill-improvement
**Origin:** ai

## Goal

`/audit` works on any repo without the orchestrator rewriting its rubric from scratch, and its
verify phase has a ready-made refuter brief, so a whole-repo audit is one skill run rather than a
hand-built pipeline.

## Context

Fibo frontend2 audit, session e3334a4a, 2026-10-01 to 2026-10-03: 21 read-only auditors, then one
refuter per report, then the orchestrator read every confirmed HIGH. The refutation pass earned its
cost: it rejected 3 findings outright and downgraded about 16, mostly HIGH to MEDIUM. It was built by
hand because the skill has no template for it.

1. `skills/audit/rubric-template.md` is written for Claude Conductor, not as a generic template. Its
   lenses name a Tauri/Rust daemon, `serde(default)` data loss,
   `daemon/remote_transport_table.rs`, pairing secrets and `escape-html`, and its closing "Context
   you should know" section describes Conductor. Phase 2 says "copy it and fill in the
   project-specific context section", but the lens bodies themselves are project-specific, so for a
   React/TanStack Query repo the whole file had to be rewritten (the result is at
   `C:\Users\tecno\Desktop\Projects\fibo\.for_bepy\audit\RUBRIC.md`).
2. Phase 4 says verify every CRITICAL/HIGH by reading the lines yourself. At 21 reports that does not
   fit in the orchestrator's context, so a per-report refuter subagent was added, driven by a shared
   brief (`C:\Users\tecno\Desktop\Projects\fibo\.for_bepy\audit\VERIFY.md`): verdicts are CONFIRMED,
   NARROWER, UNVERIFIED or WRONG, plus a corrected severity and a "Missed" section. Refuters also
   added two real HIGHs that the auditors had missed.
3. Write-permission inconsistency: auditors could write their reports to `.for_bepy/audit/reports/*.md`
   with the Write tool, but the merge subagent was refused writing `.for_bepy/audit/REPORT.md`
   ("Subagents should return findings as text, not write report files"). It returned 79KB inline
   instead, which the orchestrator had to extract with a script. Find out which hook or harness rule
   blocks this, and make the skill route around it deliberately, rather than discovering it mid-run.

## Approach

1. Split `rubric-template.md` into a stack-agnostic core (constraints, the receipt rule, severity,
   report shape, the prior-decision check against `.claude/todos/done/`) plus per-stack lens packs
   (e.g. `lenses/react-tanstack.md`, `lenses/tauri-rust.md`). Phase 2 picks the pack.
2. Add `verify-template.md` from the fibo VERIFY.md, and a Phase 4 rule: one refuter per report (or
   per 2-3 small reports), each writing a verdict file. The orchestrator then reads only the
   CONFIRMED HIGH/CRITICAL lines itself.
3. Fold in the code-check lenses that worked: size with a seam, DRY by grep, dead code by grep count,
   and convention findings that must quote the rule they break.
4. Add a drift-check step for audits that outlive a trunk move: re-check each finding whose cited
   file changed between the audited sha and current trunk.
5. Settle item 3 and state in Phase 5 who writes the merged report.

## Acceptance

- A fresh `/audit` on a non-Conductor repo needs no rubric rewrite beyond the project-context section.
- Phase 4 names the refuter template and its verdict vocabulary.
- The merged-report write path is documented and works on the first try.

## Notes

- Evidence: `C:\Users\tecno\Desktop\Projects\fibo\.for_bepy\audit\` (RUBRIC.md, VERIFY.md,
  reports/, verify/, REPORT.md, partition.mjs). `partition.mjs` slices a tree into ~5k-line file
  lists. It is generic and could ship with the skill too.
- Completed by /loop-todos cycle 1 (2026-10-05); full CI green (7/7) before commit.
