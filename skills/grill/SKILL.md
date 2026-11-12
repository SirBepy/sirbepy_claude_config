---
name: grill
description: "Monthly grill of Joe's recent product calls in one scope: right problems, right solutions, better calls? /grill."
argument-hint: "[--measure]"
---

# /grill

> Grills Joe's recent PRODUCT decisions in one scope. For each one: was this the right problem,
> was it solved the right way, would a different product call have been better?

Joe runs it about once a month, attended, in a visible Conductor chat. **Success is picks, not a
report:** it surfaces product calls Joe would actually change, and he ticks them on a card that
turns them into todos.

It is the claude_usage_in_taskbar pilot chat (session a6b0b8fa, 2026-11-11/12) made repeatable. The
chat's own model keeps all judgment and invents goal-specific measurements, which is where the
pilot's best finds came from. The skill only guarantees the steps the pilot skipped: judging Joe's
settled decisions instead of designing around them, cost per chat kind up front, commit outcomes
as a standing source, a refute pass on every candidate, and an ending in a card plus todos.

Sibling files:

| File | Job |
|---|---|
| `suspect.md` | stance, receipts rule, row schemas, devil/scout/refuter prompts, L3 fallback menu |
| `grill_dump.py` | `dump`, `check-receipts`, `gate`, `cost` (stdlib Python, run with `python -I`) |
| `test_grill_dump.py` | its self-test |

**Read `suspect.md` in full before step 5.**

## What this is not

- Not `/audit` (defects in code) and not `/rate-it` (a score for one idea). This judges calls Joe
  already made, against what happened afterwards.
- Not a report. A run that ends without a card has failed.
- Never a taste verdict on UI.

## `/grill --measure`

The cheap mode, and the kill rule's fallback shape: L1 and L4 from the dump, plus L3 measurements
the main chat runs itself (it writes `l3_0.jsonl` with the Write tool so receipts still cite a
run-dir line). No devils, scouts or refuters, so no L2 and no refuters. `check-receipts` still
runs on `candidates.jsonl`; the card, todos and archive follow as usual, with every row archived
as `unrefuted`.

## Run flow

Run dir: `C:\Users\tecno\AppData\Local\Temp\grill\<YYYYMMDD-HHMM>\`, outside every repo, so no hook or
commit sees it. Call it `<rundir>` below.

1. **Plan.** `write_plan` with one row per step and one per lane (L1-L5, open). A lane row closes
   only when its output exists.
2. **Card 1 and Card 2** (`ask_user_question`, `domain` and `badges` set, 2-4 options each).
   - Card 1, two questions:
     - **Scope** (multiSelect, at most two): the 2-3 repos with the most recent Joe turns, from
       `python -I C:\Users\tecno\.claude\skills\recall\recall.py activity --since <today - 30 days> --json`
       (each row has `repo`, `cwd`, `human_turns`; sum `human_turns` per `cwd` repo root), plus
       `C:\Users\tecno\.claude` tooling.
     - **Window:** 30 days, 60 days, or since the last archive. "Since the last archive" is the
       days from the newest archive date in `C:\Users\tecno\.claude\.claude\grill\<scope-slug>\`
       (for two scopes, the older of the two) to today; with no archive it is 30.
   - Card 2, one question per chosen scope: **its goal.** Propose one from the scope's open plans
     and todos (`<scope>\.claude\todos\`, its `PLAN.md`) as the recommended option, plus
     alternatives. Joe may restate it in his own words.
3. **Dump.**
   `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py dump --scope <path>[,<path>] --days <n> --out <rundir>`
   Read `<rundir>\summary.md`, then only the specific JSONL lines a lane needs. Its table cells are
   cut to fit, so full text always comes from the cited JSONL line. Surface every `WARNING:` line
   (stderr, and the summary's `## Warnings` section) to Joe as-is.
4. **Phase 0** is the `## Phase 0` section of `summary.md`: last run's picks with their state
   (open / closed / missing / not-picked; `closed` is not proof of a fix), every prior slug with
   its surface (reuse them), and the "never raise again" slugs (declined twice). Never raise those.
5. **Lanes** (below), in order. **Read `suspect.md` first.**
6. **Refute** every candidate (below).
7. **Output,** in this order:
   1. the top ~10 survivors in chat;
   2. the card;
   3. todos for the picks;
   4. the cost line (PowerShell; in Bash the variable is `$CLAUDE_CODE_SESSION_ID`):
      `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py cost --session $env:CLAUDE_CODE_SESSION_ID`
      prints `Cost: main <N> input-equiv tokens, <k> agents, <m> min` and writes nothing. Print it.
      (`rename-session.ps1 -GetId` is the wrong id here: it prints `<pid>-<ticks>`, not the transcript stem.)
   5. the archive, with `joe` and `todo` filled and the cost line copied into its body;
   6. `/commit` for the todos and the archive.

## Lanes

Every candidate carries a tag (`PRODUCT` / `EXECUTION` / `TOOLING`) and a receipt (`suspect.md`).
No receipt, no row.

- [ ] **L1, cost per chat kind (shown first).** From the Totals table and `chats.jsonl`: summed
  input-equiv tokens and wall time per kind (`main`, `sub-with-card`, `sub-without-card`), per
  scope. The pilot's 22x question-sub cost came from exactly this split.
- [ ] **L2, decisions as suspects (the core lane).**
  1. `clusters.jsonl` holds Joe's decisions in the window, grouped; at most 40 are `examined`.
     Reversed clusters (any entry superseded) are listed under "Reversed, not examined": report
     them as patterns with their `revisits` (the cost of the first call), never as candidates.
  2. **Devils:** `ceil(examined / 10)` Sonnet devils (at most 4), each with up to 10 examined
     clusters: only each cluster's `id` and FIRST entry (date, question, answer) plus the Card 2
     goal for its scope. Never later entries, commits or complaints. Take the full question and
     answer from `entries[0]` of the cluster's `clusters.jsonl` line, never the cut summary cell.
     Prompt in `suspect.md`.
  3. **Ruling:** read the outcome evidence (L1, L4, L5, the cluster's `revisits`), then write
     `<rundir>\l2_rows.jsonl` with the Write tool: exactly one row per examined cluster, `KEEP` or
     `CHANGE-CANDIDATE`. Never edit the devil's `alternative` or `alt_receipt`. A KEEP carries a
     `why_fails` of its own.
  4. **Gate:** `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py gate <rundir>\l2_rows.jsonl --clusters <rundir>\clusters.jsonl --scope <path>[,..]`
     must exit 0 before refuters start. Print its `KEEP=n CHANGE=m` line. `--allow-all-keep
     "<reason>"` waives the 10% CHANGE floor only with a real reason, repeated in chat and archive.
  5. Report the unexamined count (`N more not shown (not examined)`); the archive records it.
- [ ] **L3, invented measurements.** Invent 3-5 measurements for the confirmed goal, each anchored
  to an L2 cluster id or a goal clause (`anchor`). Up to 5 Sonnet scouts run them (`suspect.md`);
  write each reply to `<rundir>\l3_<n>.jsonl`. Pilot examples that worked: the median wait of a
  question sub, daemon restarts by cause, the share of transcripts ever compacted.
- [ ] **Open lane.** Anything else worth measuring or checking, from any source, mid-run (the
  pilot's best finds). Rows use `lane: open`, need no `anchor`, follow every other rule, and may
  use scout slots L3 left unused.
- [ ] **L4, commit outcomes.** `git.jsonl`: FEAT / FIX / REVERT counts per path group, FEATs
  fixed within 21 days, added-then-deleted and never-touched files. A standing source, but
  hotspots and rework are never a PRIMARY candidate source: they are evidence for a ruling.
- [ ] **L5, complaints traced upstream.** `complaints.jsonl` holds regex hits over Joe's own
  turns in main chats. A hit becomes a candidate only when you can name the upstream decision (a
  cluster id); list the rest by session and date as `unlinked`. Low counts are normal.
- [ ] **UI scopes:** show the real screen (a screenshot) next to a UI candidate. Never a taste verdict.

## Refute every candidate

Joe settled this: hunt wide, refute every candidate.

1. **Rank and fill.** Write `<rundir>\candidates.jsonl`: every L1/L3/L4/L5/open candidate plus
   each L2 CHANGE-CANDIDATE (field map in `suspect.md`), with `rank` = PRODUCT first, then cost
   times evidence strength. 8 refuters x 12 items = 96 slots: candidates fill them first in rank
   order, then L2 KEEP rows in cluster `rank` order get an "argue for change" pass. Whatever does
   not fit is archived as `unrefuted`. Nothing is dropped silently.
2. **Receipt check:** `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py check-receipts <rundir>\candidates.jsonl`
   exits 1 on any bad receipt. Fix or remove each `BAD` row before refuters run.
3. **Refuters** (prompt in `suspect.md`). Write their replies to `<rundir>\refute.jsonl`.
   - `survives` / `refuted` for candidates.
   - `reopen` on a KEEP makes it a surviving candidate (lane L2, tag PRODUCT) that goes on the
     card; its `receipt` must be real (the refuter's or yours) and pass `check-receipts`.
   - `keep` is archived as `kept`.
4. Settle refuter disagreements yourself and write the reason into the archive row.

## Output

### Chat

The ranked top ~10 survivors as a `send_message` table visual, PRODUCT rows first, ranked by cost
times evidence strength.

### The card

One `ask_user_question` call; no question count limit, 2-4 options per question.

- `domain`: `arch` for product calls, `tooling` for rules. Never `ux` (it demands previews).
- `badges: ["recommended"]` on the survivor ranked highest in each question.
- Each question is `multiSelect: true`, one option per survivor. Two pools, kept apart: PRODUCT
  first, then EXECUTION plus TOOLING. Within a pool:
  1. group survivors by surface;
  2. split a surface of 5+ into chunks of 4; a remainder of 1 borrows one survivor from the
     previous chunk, so every chunk holds 2-4;
  3. merge single-survivor surfaces into mixed questions of 2-4;
  4. a lone leftover in a pool gets a second option, "none of these".
- At most 10 survivor questions per card, plus an optional "Show the rest (N more)?" (Yes / No).
  Yes sends a second card built the same way. Nothing is hidden by a cap.
- Labels state the outcome in plain words; descriptions carry the receipt in plain words. No
  commit hashes, no code: Joe does not read code.

### Todos

Each pick becomes a todo in the repo it changes (often `C:\Users\tecno\.claude` for TOOLING), per
`C:\Users\tecno\.claude\refs\ai-todos-format.md`:

- `Origin: dev` (written after Joe's pick, so it is his decision);
- a Context section with a receipt per cause sentence;
- `Why: picked on /grill card <YYYY-MM-DD>`;
- a multi-step pick gets a short step plan in the body, not a separate file.

Commit them through `/commit`; client repos (`refs/client-repos.txt`) follow its commit window.

### Archive (the only committed run artifact)

`C:\Users\tecno\.claude\.claude\grill\<scope-slug>\<YYYY-MM-DD>.md`, one file per scope, committed in
the `~/.claude` repo through `/commit`. Scope slug: the repo folder name, lowercased;
`C:\Users\tecno\.claude` is `claude-tooling`. The run-dir files under Temp do not last, so the
archive copies everything it needs.

The FIRST table in the file has exactly these 8 columns (Phase 0 parses it; escape a `|` inside a
cell as `\|`, and `dump` warns when it cannot read a row):

```
| slug | surface | tag | lane | verdict | joe | todo | declined |
|---|---|---|---|---|---|---|---|
```

| Column | Values |
|---|---|
| `verdict` | survives / refuted / unrefuted / kept / reopened |
| `joe` | picked / declined / not-shown |
| `todo` | `<absolute repo path>:<todo id>` when picked, else empty |
| `declined` | the previous archive's count for the slug, +1 when the card showed the row and Joe did not pick it; unchanged for not-shown rows |

Every survivor goes in, picked or not. Below the table:

- each row's receipt with the quoted line copied in full, the refuter reason, and your tiebreak note;
- the cost line, per-lane counts of candidates, survivors and picks, the not-examined cluster
  count, and the gate's `KEEP=n CHANGE=m` line (plus any `--allow-all-keep` reason).

## Agents and cost

At most 17 Sonnet subagents per full run (4 devils, 5 scouts, 8 refuters), every one with
`model: 'sonnet'`, `run_in_background: false` and the `suspect.md` preamble. No haiku; no Opus
subagent, since the main chat is the judge. Roughly 0.8-1.0M Sonnet tokens per full run; the
main chat's own cost is unknown until the first counted run's cost line.

## Validation and kill rule

1. **Shakedown (not counted):** `/grill` on the `~/.claude` scope, over a window that includes the
   chats that designed and built it. Tests the dump, gate, card and archive mechanically.
2. **Blind label card (before counted run 1):** Joe labels 5 card decisions from the pilot window in
   claude_usage_in_taskbar KEEP or CHANGE (at least 2 KEEP), named by decisions-log D-number. The
   run passes them as `dump --include-refs <stem>#D<n>[,..]`, so they are examined even when
   reversed or ranked low; a reversed one is scored for the label check only and never becomes a
   candidate. Labels stay hidden from the run. Pass: at least 2 of Joe's CHANGE labels (all of them
   if he gave 2 or fewer) are ruled CHANGE-CANDIDATE, and none of his KEEP labels is.
3. **Counted run 1, claude_usage_in_taskbar:** L3 must resurface at least 2 of the pilot's 3
   measurement finds (question-sub wait and cost, daemon restarts by cause, compaction rate) or
   comparably strong ones; otherwise L3 switches to the fixed menu in `suspect.md`.
4. **Kill rule** (a pick = a row Joe ticked; the `closed` rate at the next Phase 0 is information only):
   - fewer than 5 PRODUCT picks across the first two counted runs: delete the skill;
   - L2 (devil-sourced) picks 0 after two counted runs: cut the devil step;
   - L3 supplies most picks: shrink to `--measure` (L1, L3, L4).

## Never re-add

A hard cap of 5 findings or a card that hides survivors; dropping commits as a source; a monthly
essay with no action per finding; AI taste verdicts on UI; a rigid pipeline ending at a ranked
file; a Sonnet row-per-agent pipeline that manufactures judgment; embeddings; free-text cause
labels; `expect:` trailers in digests; refuting only a top slice; subagents writing their own
files; an `archive` subcommand; extending recall.py for this. Hotspots stay evidence, never a
primary source; an end-of-chat or daily checker never replaces this run.
