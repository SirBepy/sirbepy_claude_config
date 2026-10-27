---
name: name-brainstorm
description: Triggers on /name-brainstorm only. Brainstorms product or company names with parallel agents, checks domain availability, ranks a shortlist.
argument-hint: "<what the name is for> [--person|--place] [--out <dir>] [--round N]"
disable-model-invocation: true
---

# /name-brainstorm

> Parallel naming search: idea agents, a domain checker script, a three-judge pass, a shortlist the dev can send on.

Built from four real rounds (a mail tool, an AI assistant, a calm Pomalo-mood variant, a person-like name). Everything heavy lives in sidecars:
`angles.md` (brief template, dispatch preamble, idea-agent angles), `judges.md` (judge prompts, shortlist template), `checker-notes.md` (script usage, signals, limits).

## Step 1 - Intake (one ask, before any work)

Take the product from the args and the conversation. Ask only what is still missing, in ONE `ask_user_question` call (domain `tooling`, 2-4 options each, mark a recommended pick):

- what it is and who it is for; markets and languages that matter
- the **sentence test**: how someone will say it ("open my ___", "ask my ___", "a ___ for architects"); person-like, place-like or either (`--person`, `--place`)
- tone limits (sober vs playful), words and brands to avoid, domains that matter (.com, a country TLD, .ai)
- a previous round to extend: the old `names*.txt` files become exclude lists so nothing repeats

Output folder: `--out`, else `docs/naming/<slug>/` of the current project. Do not use a folder named `out/` (many repos gitignore it); use `results/`.

## Step 2 - Brief

Write `<out>/00-brief.md` from the template in `angles.md`. It is the only context idea agents and judges get, so it must hold the product, the sentence tests, the avoid list and the strict output format.

## Step 3 - Ideation (6 agents, parallel)

Pick six angles from the catalogue in `angles.md` that fit the product and tailor each. Dispatch all six in one message: `general-purpose`, `model: 'sonnet'`, `effort: 'high'`, with the dispatch preamble from `angles.md` pasted verbatim. Each agent **writes its own file** to `<out>/ideas/N-<slug>.md` and returns under 15 lines. Never use the `READ-ONLY DISPATCH` marker here: it blocks the agent's file write.

Do not poll. Save the agents' returns only as a log line; the files are the record.

## Step 4 - Merge

```
node ~/.claude/skills/name-brainstorm/extract-names.mjs <out>/ideas <out>/names.txt --exclude <older names files, comma separated>
```

It keeps one-word ASCII names of 4-12 letters, lowercased, deduped, minus the exclude lists. Report the count.

## Step 5 - Availability and judges (in parallel)

1. Start the checker in the background: `node ~/.claude/skills/name-brainstorm/check-availability.mjs <out>/names.txt --skip hr --extra ai --out <out>/results --resume <out>/results/cache.json`. About 4 checks a second; 300 names take roughly 12 minutes. `.hr` is skipped here because its registry allows about 6 lookups a minute. Read `checker-notes.md` before interpreting results.
2. Dispatch the three judges from `judges.md` at the same time. Judges do not need availability.

## Step 6 - Finalists and sentence forms

When both finish, build the finalist list from judge consensus (a name that three judges rate highly beats one that tops a single list). Then, for the finalists only:

- run the checker **with** `.hr` (and `.eu`) on them;
- if the bare names are taken (real words and first names almost always are), add `hey<name>`, `my<name>`, `ask<name>`, `get<name>` forms and run those with `--skip hr`;
- run your own standard web search on the top 3 to 5 (one query each is enough; the judges' search is fuzzy, so say so);
- run `view-cache.mjs` to read statuses (`list a,b,c`, `comfree`, `aifree`).

Any domain claim the dev disputes is re-verified directly (DNS `NS`, port-43 whois, RDAP) before you repeat it: the script's TAKEN includes parked names.

## Step 7 - Shortlist

Write `<out>/README.md` from the template in `judges.md`. A table of 5 to 12 names with meaning, domains and what each judge said; names dropped with the reason; an honest read; and a **Not checked yet** section (trademarks, company registers, native speaker, a real Google pass). Facts in it each need a source: a judge line, a script result or a search you ran.

## Step 8 - Commit and report

Commit the folder by pathspec through `/commit` (data and prose only, so the code-check scope is empty). Report to the dev in one short message: the top names with one reason each, the domain finding, what was dropped, what is unchecked. Offer the next move (a new round with the shortlist's style, or trademark and register checks on 3 to 5 names).

## Rules

- Every subagent is `model: 'sonnet'`; the dispatch prompt carries the staging line, the `run_in_background` ban and the screenshots line (all in `angles.md`).
- No em dashes anywhere. Meanings must be real: tell agents to flag anything unverified, never invent an etymology.
- Never claim a name is "free" from the script alone: it means "not registered today". Say so in the shortlist.
- A name proposed by a judge was not scored by the other judges; label it that way.
- Never register, buy or reserve anything.
