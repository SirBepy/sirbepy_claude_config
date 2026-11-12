# /grill: stance, receipts, schemas and subagent prompts

> Read once per run, before the first lane. SKILL.md says when each prompt below is used.

## Stance

- **A settled decision is a suspect, not a constraint.** The pilot's one big miss was designing
  around Joe's own earlier calls instead of judging them. Every examined cluster gets a ruling.
- **The main chat judges; subagents look things up.** Devils propose alternatives, scouts measure,
  refuters attack. None of them rules KEEP or CHANGE, and none writes a file.
- **Outcome evidence beats opinion.** A ruling cites what happened after the call: cost per chat
  kind (L1), commits (L4), complaints (L5), the cluster's `revisits`, an L3 measurement.
- **A reversed decision is evidence, never a candidate.** Its `revisits` count is what the first
  call cost. It is listed as a pattern with no verdict.
- **UI: show the real screen, never a taste verdict.** A UI candidate carries a screenshot of the
  actual surface; whether it looks good is Joe's call alone.
- **Every candidate carries one tag:**
  - `PRODUCT`: Joe's call (what to build, for whom, how it should behave);
  - `EXECUTION`: Claude botched a sound call;
  - `TOOLING`: rule or skill friction.

## Receipts (one form)

```
{"file": "<absolute path>", "line": <1-based physical line>, "quote": "<8+ chars, exact substring of that raw line>"}
```

- `file` is a repo file, a transcript, a decisions log, a digest, or a run-dir JSONL file.
- Lines are counted by splitting the UTF-8 file on `\n` only. In JSONL the quote is the escaped
  text as stored: a path reads `C:\\Users`, with doubled backslashes.
- Numbers cite the run-dir JSONL line they came from (`summary.md` prints each row's `file:line`).
  A scout's number cites the line of `l3_<n>.jsonl`, which the main chat wrote from the reply.
- `grill_dump.py check-receipts` and `gate` prove the quote is on the line. Whether the claim is
  TRUE is the refuter's job.
- The only exception: an L2 KEEP row's `receipt` may be `{"none_searched": "<what was searched>"}`
  (8+ chars). A CHANGE-CANDIDATE, and every row in `candidates.jsonl`, needs a real receipt.

No receipt, no row.

## Row schemas

**L2 row** (`l2_rows.jsonl`, one per examined cluster, written by the main chat):

```
{slug, cluster, scope, surface, decision, alternative, alt_receipt?, receipt, verdict, why_fails?}
```

- `cluster`: the cluster `id`, copied exactly from `clusters.jsonl`.
- `decision`: the first entry's `question + " -> " + answer`, cut to 300 chars.
- `alternative` and `alt_receipt`: the devil's, copied unedited.
- `receipt`: the ruling's own outcome evidence.
- `verdict`: `KEEP` or `CHANGE-CANDIDATE`.
- `why_fails`: required on KEEP, 20+ chars, one line on why the alternative loses, unique per row.

**Candidate** (`candidates.jsonl`):

```
{slug, scope, rank, lane: L1|L2|L3|L4|L5|open, tag: PRODUCT|EXECUTION|TOOLING, surface, claim, receipt, anchor?, cluster?, proposed_change}
```

An L2 CHANGE-CANDIDATE row becomes a candidate with `lane: L2`, `tag: PRODUCT`, `cluster` = its id,
`claim` = the decision, `proposed_change` = the devil's alternative, `receipt` = the strongest
outcome receipt for the ruling. L3 rows carry `anchor` (an L2 cluster id or a goal clause).

**Subagent replies** (one JSONL line per item, inside one fenced block):

| Reply | Fields |
|---|---|
| devil | `{cluster, alternative, alt_receipt?}` |
| scout (`l3_<n>.jsonl`) | `{measurement, anchor, value, unit, receipt, note}` |
| refuter (`refute.jsonl`) | `{slug, verdict: survives\|refuted\|keep\|reopen, knowable_then, looks_bad_but_fine, reason, receipt?}` |

**Slug:** kebab-case of the surface plus the decision, at most 6 words. Reuse a prior slug from
Phase 0 when the surface and decision match; Phase 0 matches rows across runs by slug.

## Dispatch rules

- `model: 'sonnet'` and `run_in_background: false` on every dispatch. No haiku, no Opus subagent.
- At most 17 per full run: 4 devils, 5 scouts, 8 refuters.
- Subagents return text only. The main chat writes each returned fenced block into the run dir
  with the Write tool, never through the shell.
- Every prompt opens with the preamble below, verbatim (`hooks/dispatch-preamble-guard.py` checks it).

### Preamble (paste verbatim at the top of every prompt)

```
READ-ONLY DISPATCH

Leave all changes unstaged. Never run `git add`. The main agent will run /commit by pathspec after your report-back.

`run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
before ending your turn. The harness auto-backgrounds any command past 120 seconds; pass an
explicit timeout up to 600000 and wait it out, never hand the build off. (See
`refs/builder-preamble.md` for the full canonical block this is drawn from.)

HARD CONSTRAINTS:
- Do NOT write, edit or create any file. Return your answer as text only.
- Do NOT spawn further subagents. Do NOT ask questions.
- Your whole reply is ONE fenced ```jsonl block, one JSON object per line, nothing else.
```

### Devil prompt (L2, at most 4, about 10 clusters each)

```
<preamble>

You are the devil's advocate for product decisions Joe made. For each decision below, propose the
STRONGEST alternative product call he could have made instead, reasoning only from what was
knowable on the decision date. You see only the decision itself: you do not know what happened
afterwards, and you must not guess at it. If the answer text states a later status, ignore it.

The goal Joe confirmed for this scope: <Card 2 goal for this scope>

Rules:
- One line per cluster: {"cluster": "<id, copied exactly>", "alternative": "<one or two sentences>"}.
- An alternative is a different PRODUCT call (what to build, for whom, how it behaves), never
  "do the same thing better" and never a restatement of the decision.
- Optional "alt_receipt": {"file", "line", "quote"} when a file you read supports the alternative.
  Absolute path, 1-based line, quote of 8+ chars copied exactly from that line. Never invent one.

Decisions (id | date | question -> answer):
<id> | <first_date> | <question> -> <answer>
...
```

### Scout prompt (L3 and the open lane, at most 5, one measurement each)

```
<preamble>

Measure one thing and report the number with its evidence.

Measurement: <the question, e.g. "median minutes between a question sub's start and Joe's answer">
Anchor: <L2 cluster id or goal clause>
Where to look (absolute paths): <run-dir files, transcript paths, repo paths>

Rules:
- Read only what you need. Never load a whole transcript: stream it or grep it.
- Reply with one line: {"measurement", "anchor", "value", "unit", "receipt", "note"}.
- "receipt" is {"file", "line", "quote"} pointing at the evidence you read (absolute path,
  1-based line, 8+ char exact quote). "note" says how you computed the value and what it misses.
- If the data cannot answer the question, say so in "note" and set "value" to null.
```

### Refuter prompt (at most 8, about 12 items each)

```
<preamble>

You are an adversarial refuter. Try to kill each item below. Read each receipt's file:line first.

For each CANDIDATE (a proposed change to a past decision):
- "knowable_then": what Joe could actually have known on the decision date.
- "looks_bad_but_fine": the strongest case that the original call is fine after all. Mandatory,
  never empty.
- "verdict": "survives" if the change still holds after both, else "refuted".
- "reason": one or two sentences.

For each KEEP item (a decision the main chat chose to keep), argue FOR changing it:
- "verdict": "reopen" if the case for change is stronger than the keep reason, else "keep".
- A "reopen" should carry "receipt": {"file", "line", "quote"} for the evidence that tips it.

Reply with one line per item:
{"slug", "verdict", "knowable_then", "looks_bad_but_fine", "reason", "receipt"?}

Items:
<candidate rows with their receipts, then KEEP rows with decision, alternative, why_fails, receipt>
```

## L3 fallback menu

Used only when counted run 1 fails its L3 check (SKILL.md "Validation"): these three pilot
measurements, generalized to the scope, replace the invented set.

1. **Question-sub wait and cost:** median wall time from a `sub-with-card` chat's start to Joe's
   card answer, and its input-equiv tokens against a `main` chat's.
2. **Restarts by cause:** how often the scope's daemon, server or app was restarted, grouped by
   the cause the transcripts give.
3. **Compaction rate:** the share of the scope's in-window transcripts that were ever compacted.
