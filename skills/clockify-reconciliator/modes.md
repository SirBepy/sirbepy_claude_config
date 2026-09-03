# clockify-reconciliator - optional modes

Read this file at step 3a of the main skill flow, only after the dev's phrasing has triggered
Reconstruction or Audit per SKILL.md Step 3a's rules. A plain Reconciliation run never reads this
file. The billable/overlap/hours rules both modes defer to still live in SKILL.md's `## Rules`
section, not here - they are cross-cutting, not mode-specific.

## Reconstruction mode

Gated in by step 3a. Builds an entire period from scratch when little or nothing is logged. Sources,
in priority order:

1. Git commits (author-date, all configured repos) - the primary evidence.
2. The recurring standup block, if one is named in the project config.
3. An optional commute-app timestamp source for bounding unexplained gaps as likely in-person
   meetings: first daily timestamp before ~1PM = arrival, a second same-day timestamp or one after
   ~1PM = departure. A missing departure is normal, not an error. Durations anchored this way are a
   starting hypothesis, not ground truth - always ask the dev to confirm meeting content/duration from
   memory, and let the dev's memory win when it conflicts with the timestamp-derived guess.

**Clustering defaults** (proven 2026-07-21, 46 entries; tightened 2026-08-27 after a sparse zng-app
day produced 4-6h of unbacked padding): session break at a 3h commit gap bridges commits into one
loosely continuous session for boundary-grouping purposes only, never as license to invent hours. Pad
each rendered chunk +20min lead-in and +20min trail-off around its own actual commit cluster, capped
at last-commit + pad even when that leaves a gap before the next meeting or entry - never stretch a
chunk's end to reach a scheduled carve-out. Split sessions over 3h into ~2-2.25h sub-chunks with
per-chunk commit-derived descriptions. Never render a chunk in the leftover window between two
carve-outs unless a commit actually falls inside it - a zero-commit gap between meetings is not
evidence of work; leave real 1h+ commit-free stretches unlogged instead of solid-filled. This cap
only bites when a chunk would otherwise stretch toward a distant boundary; a densely-packed session
(like the original 46-entry set) has no such distant boundary to stretch to, so its rendered span is
unchanged. Carve named recurring non-commit activities (e.g. a daily 09:45-10:00 standup) around
sessions instead of double-booking them. Create via `POST` (plain Reconciliation mode stays
`PUT`/description-only, never creates).

**Hard rule:** never invent hours not backed by a real commit/PR or an explicitly named real activity
- a weekly target the dev states is a ceiling to fill toward from real evidence, never a target that
justifies inventing unbacked hours (see SKILL.md's Rules section). SKILL.md's step 3a confirms the
target's scope (existing-inclusive vs additional-only, exact window) before this mode is ever reached
- never re-derive that confirmation here or assume it from context.

## Audit mode

Gated in by step 3a. Runs a checklist over a period that already has entries, cheapest check first:

- **Hard overlap check:** any two entries in the range with overlapping `[start, end)` - always a bug,
  fix immediately, no judgment call.
- **Mechanical-split fingerprint:** consecutive entries with near-identical (within a few seconds)
  durations - a sign a raw block got auto-split without checking for real gaps. Re-derive each half's
  commit backing independently rather than trusting the original split point.
- **Chopped-session fingerprint:** two short entries (roughly under 30min) separated by a gap of an
  hour or more, with nothing else nearby, on the same night/day. Default hypothesis is ONE continuous
  session with untracked (non-commit) work in the gap - ask the dev before assuming two real separate
  sessions instead.
- **Total-duration sanity:** any single day over ~9-10h, or a duration wildly disproportionate to a
  trivial-sounding description, gets a second look.

**Script the overlap/gap checks once past ~10 entries or ~30 commits** (i.e. anything past a single
day) instead of reasoning through them by eye. A manual read produced a real false positive
(2026-08-27 zng-app: a block's end time misread against a commit timestamp, caught only because a
second look happened to occur, after it was already shown to the dev as confirmed alongside a real
finding). Convert every entry's `[start, end)` and every commit's timestamp to epoch seconds once,
then check coverage/overlap in a loop; a finding presented to the dev as confirmed must come from
that script's output, not an earlier manual pass. Precompute interval epochs into arrays before the
per-commit loop - a nested loop calling `date -d` per commit-times-interval pair timed out at
93 x 23 = 2139 subshell spawns; precomputing cut that to 93 + 23 calls.

**Multi-pass verification**, reusable pattern for a full-month audit: 2 independent `sonnet` agents
padding-hunting from different angles/date ranges, then 1 `sonnet` agent explicitly tasked as
devil's-advocate-for-longer (catches over-trimming), then 1 final high-reasoning **read-only** solo
pass told to look for systemic issues (overlaps, cross-day inconsistency, "does this look
reverse-engineered") rather than re-litigate individual entries already checked. Give every subagent
the live API key/workspace/project ids inline and tell it explicitly whether it has write access or is
report-only - each one re-pulls data itself rather than trusting a prior agent's summary. Follow the
global sonnet-by-default / opus-only-for-final-solo-verify model rule. Paste the canonical preamble
from `refs/builder-preamble.md` into every subagent's dispatch prompt - `hooks/dispatch-preamble-guard.py`
rejects a prompt missing its markers.
