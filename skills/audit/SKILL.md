---
name: audit
description: Whole-repo audit - read-only subagent fan-out, ranked verified findings. For "what's wrong with my app", not diffs.
argument-hint: "[optional scope note, e.g. `just the backend` or `security only`]"
---

# /audit

> The whole-repo counterpart to `/code-review`. That one judges a diff; this one judges the thing.

Built 2026-09-26 after a survey of every publicly available Claude Code audit skill found nothing
worth adopting: the official Anthropic marketplace has no whole-repo audit plugin, and the five
community candidates each carried a disqualifying cost (a large unwanted plugin surface, a hard
requirement on Opus plus a memory MCP server, a TS/JS-only scope, or a single-commit repo whose star
count was not a quality signal). Three ideas from them were worth stealing and are baked in below:
a mandatory "looks bad but is actually fine" section, an adversarial refutation pass over the worst
findings, and file:line-or-it-does-not-exist.

## What this is not

- **Not `/code-review`.** That reads a diff. This reads the repository.
- **Not `/code-check`.** That is a structural/convention sweep that writes straight to the backlog.
  This deliberately does not write todos until the dev has accepted each finding.
- **Not `/rate-it`.** That returns a score. This returns a defect list with receipts.

## Phase 1 - Map before you partition

Do this yourself, inline. It is cheap and it is what makes the fan-out good.

    find <src roots> -name '*.<ext>' | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn
    find <src roots> -name '*.<ext>' -exec wc -l {} + | sort -rn | head -40
    ls <each big dir>

You are looking for: total LOC, the directories with the most files, the twenty largest files, and
the actual file names inside each big directory. Read the repo's `CLAUDE.md` too.

Then build the partition. **Every slice gets a concrete file list, never a directory glob.** A slice
described as "the frontend" produces a generic report; a slice described as twenty named files
produces findings with line numbers. Aim for 10-25 files or ~5k lines per slice.

## Phase 2 - Write the rubric to disk

Write `.for_bepy/audit/RUBRIC.md` (or the project's scratch equivalent) once, then have every
dispatch read it. This keeps each dispatch prompt short and guarantees one shared severity scale and
one report shape across 25 agents. Copy `rubric-template.md` from this skill's directory and fill in
the project-specific context section at the bottom.

The rubric's non-negotiables:

- **Read-only.** No edits, no `git add`, no commit.
- **No build tools.** No `cargo`, `pnpm`, `vite`, `tsc`, `vitest`, `gradlew`. In a repo with a live
  daemon or concurrent sessions, a `cargo` invocation takes a global target lock and can kill the
  dev's running app. Auditors read source; they do not compile it.
- **Every finding carries a `path:line` read in that dispatch.** No receipt, no finding. A suspicion
  that cannot be proven from the slice is labelled `UNVERIFIED:` plus the file that would settle it.
- **A fixed report shape**, so 25 reports merge mechanically.
- **No padding.** Ten real findings beat forty soft ones. A healthy slice says so.

## Phase 3 - Fan out

Every dispatch needs the canonical builder preamble from `~/.claude/refs/builder-preamble.md`, with
the literal line `READ-ONLY DISPATCH` (audits capture no screenshots, so the screenshot-id
requirement is exempted by that marker). `model: 'sonnet'` on every one - a well-written dispatch
prompt is what determines quality here, and the orchestrator controls that.

**The concurrency cap is 20.** `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` governs it; the 21st dispatch
returns "Concurrent subagent limit reached" and is simply not launched. Launch in waves and refill
slots as reports land. Tell the dev they can raise the env var and `/respawn` if they want the whole
fan-out live at once.

### The two kinds of slice

**Area slices** own a bounded file list and apply all four lenses to it. One per coherent subsystem.

**Cross-cutting slices** own one lens across the whole tree and go grep-first. These find what no
single-directory auditor can see, and in practice they produce the best findings. Run at least:

| Slice | What it sweeps |
| --- | --- |
| Security | every listener, every auth check, every `Command::new`, every path from a request, every `innerHTML`, the CSP, secret handling |
| Panics and races | every `unwrap`/`expect`/index, every lock held across an `await`, lock ordering, blocking IO on a UI thread, unbounded channels, swallowed errors |
| Product and UX | the feature inventory with orphans named, surface counts, the core loop traced click by click, the concept vocabulary, where a new user stalls |
| Duplication and dead code | the same rule implemented twice and already diverged, dead exports, dead files, dead flags |
| Test coverage | density vs risk, false-pass risk, brittleness, isolation, what a regression test would have caught |
| Idle cost and performance | every timer with its period, totalled; the slow paths under load; what grows forever |
| Docs drift and backlog archaeology | every checkable claim in `CLAUDE.md` verified; the backlog clustered by cause, not symptom |

### Feeding results forward

As reports land, add a "already reported, do NOT re-report" list to the dispatches still being
launched. It stops three agents spending output on the same non-constant-time comparison.

## Phase 4 - Verify, do not relay

**This is the phase that separates an audit from a pile of model output.** A subagent's report is a
claim, not a finding.

For **every CRITICAL and HIGH**, read the cited lines yourself before it goes in the report. Follow
each link of a multi-step chain separately. Then classify:

- **Confirmed** - you read the lines and the claim holds. Say so and keep the severity.
- **Confirmed but narrower** - the mechanism is real, the impact is smaller than claimed. Rewrite the
  impact honestly. An exaggerated CRITICAL costs more credibility than a missed MEDIUM.
- **Unverified** - part of the claim depends on something outside the repo (a third-party binary's
  behaviour, a runtime property). Label that part `UNVERIFIED` explicitly, in the report and in
  anything you tell the dev. Do not let a verified half launder an unverified half.
- **Wrong** - drop it, and add it to the "looks bad but is actually fine" section with the reason.

Two independent agents converging on the same finding from different slices is a strong signal, not
a duplicate to merge away: say so in the report, and verify it anyway.

Surface a confirmed CRITICAL to the dev **the moment it is verified**, not at the end. They may want
it fixed before the audit finishes.

## Phase 5 - The report

One markdown file. Findings ranked by severity, then by whether the dev would hit it in a normal
day. Each finding keeps: where (`path:line`), what, why it matters with a concrete trigger, the
proposed fix, confidence, effort, lens.

Three sections the report must have:

1. **Themes, not just a list.** Fifteen findings that are all "a sync command doing blocking IO" are
   one finding about a habit. Cluster them and name the habit. This is the part the dev actually
   acts on.
2. **Looks bad but is actually fine.** Every finding you rejected, with the reason. This is what
   stops the report padding itself, and it is often the most reassuring part to read.
3. **What is genuinely good.** At least three, specific, with receipts. An audit with no positives
   is an incomplete audit, not a rigorous one.

## Phase 6 - Accept, then file

**Do not write todos yet.** Walk the dev through the findings and let them accept or reject each
one. Only accepted findings become `.claude/todos/` entries, per
`~/.claude/skills/close/ai-todos-format.md`. A rejected finding is worth one line in the report
saying the dev declined it and why, so a future audit does not re-file it.

Fixes are a separate, explicitly requested step. `/audit` reads; it does not edit.

## Cost

Roughly 25 sonnet agents at 150k-250k tokens each. This is a deliberate, expensive, occasional
operation. Confirm the dev wants it before launching unless they have already said so in this
session.
