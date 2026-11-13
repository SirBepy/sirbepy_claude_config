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
chat's own model keeps all judgment and invents goal-specific measurements, and free scouts pick
their own measurements from the scope's logs, code and decision docs, which is where the pilot's
best finds came from (restart causes, lost wakes, writer-slot waits, RAM, a push-guard gap). The
skill only guarantees the steps the pilot skipped: judging Joe's settled decisions instead of
designing around them, cost per chat kind up front, commit outcomes as a standing source, a refute
pass on every candidate, and an ending in a card plus todos.

**The main input is Joe's own card answers.** The dump ranks them before anything else; a digest
line counts only when it is marked `Joe:`. On 2026-11-12 the first build examined 0 of Joe's 175
card answers in claude_usage_in_taskbar because Claude's after-job notes took all 40 slots.

Sibling files:

| File | Job |
|---|---|
| `suspect.md` | stance, receipts rule, row schemas, devil/scout/refuter prompts, L3 fallback menu |
| `grill_dump.py` | `dump` (also lists scout sources), `check-receipts`, `gate`, `cost` (stdlib Python, run with `python -I`) |
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
   `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py dump --scope <path>[,<path>] --days <n> --out <rundir> [--logs <dir>[,<dir>]]`
   `--logs` names the app's own log folders outside the repo, when the scope's `CLAUDE.md` or
   project memory says where it writes them (claude_usage_in_taskbar:
   `C:\Users\tecno\AppData\Roaming\claude-conductor`). In-repo `*.log` files are found anyway.
   Read `<rundir>\summary.md`, then only the specific JSONL lines a lane needs. Its table cells are
   cut to fit, so full text always comes from the cited JSONL line. Surface every `WARNING:` line
   (stderr, and the summary's `## Warnings` section) to Joe as-is: a log-format warning means the
   month is not quiet, the reader is blind.
4. **Phase 0** is the `## Phase 0` section of `summary.md`: every slug from every past archive of
   the scope, each from the newest archive holding it, with its state (open / closed / missing /
   not-picked; `closed` is not proof of a fix) and surface (reuse them), and the "never raise
   again" slugs (declined twice, in any runs). Never raise those.
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
  input-equiv tokens and wall time per kind, per scope. `main` is a chat that owns a decisions
  log; `other` is every chat that neither owns one nor is a logged sub (gate chats, helpers, plain
  CLI chats). Compare `main` against the two sub kinds; never fold `other` into `main` (that put
  499 chats in the main bucket on 2026-11-12, when 5 were real mains). The pilot's 22x
  question-sub cost came from exactly this split.
- [ ] **L2, decisions as suspects (the core lane).**
  1. `clusters.jsonl` holds Joe's calls in the window, ranked. Card answers come first; a digest
     line is in only when marked `Joe:` (the rest are Claude's own calls and are only counted). A
     sub's card answers form one **thread** (a sub is one job on one surface): its `size` is the
     number of rounds and `revisits` the rounds after the first, the cost of the first call.
     Main-chat cards group by word overlap. Logistics cards (`noise`: a "May Claude edit that
     file?" permission ask, a "which of these lifts" pick) rank last and get a slot only when one
     is free; the summary lists the rest by name, so pull a misfiled product call in with
     `--include-refs`. Ranking: logistics last, cards before digest lines, then most rounds, then
     the oldest call first; at most 40 are `examined`, shared
     round-robin across scopes so one busy scope cannot take every slot.
  2. **Every age counts** (Joe, 2026-11-13: "even 1/4 days old is fine"). Each cluster carries
     `age_days` and a `basis_hint`: `reasoning` when it is under 7 days old with no later round,
     else `outcome`. A `reasoning` call has had no time to show an outcome: judge it on its
     reasoning at the time, never as if it had failed.
  3. `reversed` is set only when the log marks a card entry `Closed by`, which today's logs never
     do (they close finish entries). Read reversals from a thread's later rounds instead, in the
     summary's "Threads with later rounds" list. A reversed cluster is a pattern, never a candidate.
  4. **Devils:** `ceil(examined / 10)` Sonnet devils (at most 4), each with up to 10 examined
     clusters: only each cluster's `id` and FIRST entry (date, question, answer) plus the Card 2
     goal for its scope. Never later entries, commits or complaints. Take the full question and
     answer from `entries[0]` of the cluster's `clusters.jsonl` line, never the cut summary cell.
     Prompt in `suspect.md`.
  5. **Ruling:** read the outcome evidence (L1, L4, L5, a thread's later rounds in its
     `entries`, the L3 rows), then write `<rundir>\l2_rows.jsonl` with the Write tool: exactly one
     row per examined cluster, `KEEP` or `CHANGE-CANDIDATE`, with its `basis` (`outcome` when the
     receipt is something that happened after the call, else `reasoning`). Never edit the devil's
     `alternative` or `alt_receipt`. A KEEP carries a `why_fails` of its own that names what in
     the alternative loses; a template filled in per row fails the gate.
  6. **Gate:** `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py gate <rundir>\l2_rows.jsonl --clusters <rundir>\clusters.jsonl --scope <path>[,..]`
     must exit 0 before refuters start. Print its `KEEP=n CHANGE=m` line. `--allow-all-keep
     "<reason>"` waives the 10% CHANGE floor only with a real reason, repeated in chat and archive.
  7. Report the per-scope examined and unexamined counts from the summary; the archive records them.
- [ ] **L3, measurements by scouts.** At most 6 Sonnet scouts per run, each returning at most 3
  rows (`suspect.md`). Write each reply to `<rundir>\l3_<n>.jsonl`, then run
  `python -I C:\Users\tecno\.claude\skills\grill\grill_dump.py check-receipts <rundir>\l3_*.jsonl`
  and drop every `BAD` row before a ruling or candidate uses it. Two kinds:
  - **Measuring scouts** (up to 4): the main chat invents a measurement for the confirmed goal,
    anchored to an L2 cluster id or a goal clause (`anchor`). Pilot examples that worked: the
    median wait of a question sub, daemon restarts by cause, the share of transcripts ever compacted.
  - **Free scouts** (at least 2, Joe's call 2026-11-13: "scouts pick what to measure"): each gets
    the goal and the `## Sources for scouts` rows (decision docs with their who-decided marks,
    plans, app logs, the code root) and picks its own measurements there. One free scout per
    source kind that exists: logs, then decision docs and plans, then code.
  - A call found in a decision doc carries `decided_by` from the doc's own mark (`Joe`, `Dane`,
    `Claude's call`, or `unmarked`). A `Claude's call` row is EXECUTION, never PRODUCT; a call
    another person made is PRODUCT with their name on the card.
- [ ] **Open lane.** Anything else worth measuring or checking, from any source, mid-run. Rows
  use `lane: open`, need no `anchor`, follow every other rule, and may use scout slots L3 left unused.
- [ ] **L4, commit outcomes.** `git.jsonl`: FEAT / FIX / REVERT counts per path group, FEATs
  fixed within 21 days, added-then-deleted and never-touched files (the `*_count` fields are the
  totals; the lists are samples of 10). `.claude/` paths (todos, plans, memory) are left out. A
  standing source, but hotspots and rework are never a PRIMARY candidate source: they are
  evidence for a ruling.
- [ ] **L5, complaints traced upstream.** `complaints.jsonl` holds one hit per Joe message (with
  every regex `categories` it matched) over main and other chats. Sentences Claude wrote before
  the turn (a respawn brief, a scheduled prompt, a pasted card question), tagged blocks and
  daemon relays are removed first, so `text` is Joe's own words. A hit becomes a candidate only
  when you can name the upstream decision (a cluster id); list the rest by session and date as
  `unlinked`. Low counts are normal.
- [ ] **UI scopes:** show the real screen (a screenshot) next to a UI candidate. Never a taste verdict.

## Refute every candidate

Joe settled this: hunt wide, refute every candidate.

1. **Rank and fill.** Write `<rundir>\candidates.jsonl`: every L1/L3/L4/L5/open candidate plus
   each L2 CHANGE-CANDIDATE (field map in `suspect.md`), with `rank` = PRODUCT first, then
   `basis: outcome` before `basis: reasoning` (a fresh call is never ranked as if it had already
   failed), then cost times evidence strength. 8 refuters x 12 items = 96 slots: candidates fill them first in rank
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
- A `basis: reasoning` row's description opens with "No outcome yet, judged on the reasoning at
  the time:". A call someone else made names them ("Dane's call:").

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
| `declined` | Phase 0's count for the slug (0 when new), +1 when the card showed the row and Joe did not pick it; unchanged for not-shown rows |

Every survivor goes in, picked or not. Below the table:

- each row's receipt with the quoted line copied in full, the refuter reason, and your tiebreak note;
- the cost line, per-lane counts of candidates, survivors and picks, the per-scope not-examined
  cluster counts, each row's `basis`, and the gate's `KEEP=n CHANGE=m` line (plus any
  `--allow-all-keep` reason).

## Agents and cost

At most 18 Sonnet subagents per full run (4 devils, 6 scouts, 8 refuters), every one with
`model: 'sonnet'`, `run_in_background: false` and the `suspect.md` preamble. No haiku; no Opus
subagent, since the main chat is the judge. Roughly 0.9-1.1M Sonnet tokens per full run; the
judge's 2026-11-12 review session cost 4.38M main input-equiv with 32 agents, an upper bound.

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
   comparably strong ones; otherwise L3 switches to the fixed menu in `suspect.md`. The free
   scouts must not be told the pilot's finds: that would contaminate this check.
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
