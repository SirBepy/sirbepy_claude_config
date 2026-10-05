# Memory write rubric

> What earns a memory, what doesn't, and how to write it without corrupting what's already there.
> Applies to BOTH stores: native per-project Auto Memory and the global Obsidian vault.
> Read once per session, before the first memory write.

## The gate: decide an action, not a feeling

Never ask "does this feel noteworthy". For every candidate fact, first search existing memory for
the same subject, then pick one:

- **ADD** - genuinely new subject. Write a new file.
- **UPDATE** - same subject, materially different value. Edit the existing file in place, keep its
  name. Say what changed and when.
- **DELETE** - the new fact contradicts a stored one and the stored one is now wrong. Remove it.
  Being wrong is expected; staying wrong is the failure.
- **NONE** - already captured, or fails the bar below. Do nothing. This is the most common answer.

A near-duplicate written as ADD is worse than no memory at all: it crowds out rarer, more useful
entries and leaves two records with no signal about which is current.

## Bar for writing at all

Write only when ALL of these hold:

1. **Confirmed, not merely mentioned.** Joe stated it, or it was verified against the live system.
   An inference from one ambiguous remark is not a fact. Write-on-confirm, never write-on-mention.
2. **Reusable beyond this session.** It will still matter in a future session with no memory of today.
3. **Not already knowable.** Skip anything the repo, git history, CLAUDE.md, or the code already says.
   Memory is for what the codebase cannot tell you.
4. **No live contradiction.** If it conflicts with an existing memory, resolve that first (UPDATE or
   DELETE), don't stack a second opinion next to the first.

Repetition is not evidence. Three observations from the same conversation, the same prompt, or the
same misunderstanding are one observation. Independent support is what counts.

## Never write

- Generic acknowledgments, pleasantries, assistant-side chatter.
- Ephemeral session state ("currently editing X", "the build is running").
- Characterizations of Joe that he didn't confirm.
- Routine auto-decisions he'll never read. See [[feedback_kill_unread_note_mechanisms]].
- Anything already captured. Check first, every time.

## Always include evidence, not just the verdict

A record that states a conclusion without what proved it is worse than no record, because it will be
trusted later with no way to tell it went stale. Every `feedback` and `reference` memory carries:

- **What happened** that produced this (the incident, the correction, the measurement).
- **Under what conditions** it was verified, when that matters. "Confirmed working" is worthless if
  the test conditions made failure impossible.
- **When**, as an absolute date, never "recently" or "last week".

## Negative results are first-class

"X is NOT the cause, here is the proof" is often worth more than a positive finding: it permanently
removes a branch from the search tree, and without it the same dead end gets retried by future
sessions forever. Worth writing when the theory was plausible enough that someone would retry it.

Shape: what was tried, what disproved it, and the evidence. Type is `reference` for a fact about the
system, `feedback` for a rule about how to work.

## Index ordering (MEMORY.md only)

MEMORY.md truncates at **24.4KB of bytes, not at a line count**; anything past that offset is
silently dropped. Measured 2026-09-25 on a 150-line index that cut at line 134, nowhere near the
200 lines this file previously claimed. Lines are the wrong unit because a chained entry
(`[a](x.md) + [b](y.md) + [c](z.md)`) can run 500 bytes while a short one runs 90, so an index
breaches on bytes long before it looks long.

`skills/cleanup-memory/reachability.mjs` derives its line cap from that byte budget by default;
never pass `--line-cap` unless a host genuinely has a different rule, because a line cap above the
real cut makes the script report `orphan-file: 0` on a corpus that is dropping files.

The vault has no such cap, so this section governs the native per-project index only.

**Ordering is the lever, not length.** Truncation is not preventable for long: encoding tricks buy
a few hundred bytes against an index that grows every session. What IS controllable is which
entries sit below the cut. Behavioural rules that apply every turn belong above it; task-specific
references (a tool's quota rules, a harness flag, a one-tool workflow) are cheap to lose because a
session doing that task will look them up anyway.

Keep the index in three ordered blocks, top to bottom:

1. **Axioms** - entries meeting `skills/cleanup-memory/SKILL.md` Step 1.5's three-question test
   (Claude defaults wrong without it, failure is silent, applies every session).
2. **Recent** - file mtime within 7 days of today.
3. **Rest** - everything else.

Within a block: sort by file mtime descending (newest first); break ties by filename ascending.
Deterministic on purpose - re-sorting an already-sorted index must be a no-op.

Rule for every ADD/UPDATE that touches the index: insert or move the entry's line to the TAIL of
its own block, never to the end of the whole file. This keeps fresh writes out of the truncation
zone between `/cleanup-memory` runs, which perform the full canonical re-sort.

## Receipts beyond memory writes

The same evidence-before-verdict discipline this rubric enforces for memory also governs two
claim shapes `CLAUDE.md`'s Execution Discipline UNVERIFIED rule does not spell out by name. Both
extend that rule rather than replace it; this section is their only full write-up, kept here
because `CLAUDE.md` had no token headroom to carry the extra prose (ratchet ceiling,
`ci/check_instruction_budget.py`) and this file already loads every session.

- **A third-party artifact (repo, skill, plugin, package) being judged for adopt/reject.** A
  `WebFetch` of a README or landing page answers through a small summarizing model, so its output
  is a paraphrase, not the artifact. 2026-09-25: Claude judged
  `github.com/ayghri/i-have-adhd` from one such summary and said "take nothing from it"; reading
  `SKILL.md` verbatim via `raw.githubusercontent.com` reversed the verdict and two of its rules
  were adopted (`03e79a5`). The receipt that satisfies a verdict here is the artifact's own
  load-bearing files, read directly (`raw.githubusercontent.com`, or a trees-API listing for which
  files exist) - never a fetched summary.
- **A token count volunteered as a per-turn or per-request COST**, not asked for. 2026-09-28,
  `claude_usage_in_taskbar` session `7099dea0`: Claude measured MCP tool schemas by character count
  and presented it as a recurring bill across two question cards before the dev pushed back; the
  figure was off by roughly 10x because the schemas were deferred behind `ToolSearch` and what
  wasn't deferred was cache-read from turn 2 on. Before stating a token count as a bill, check
  whether that content is cached or deferred - a raw character or word count alone is a
  context-footprint figure, not a bill.

## Anti-patterns this rubric exists to prevent

- **Bloat.** Volume degrades retrieval. More entries is not more memory.
- **Stale confidence.** An old fact retrieved today reads exactly as authoritative as a fresh one.
  Timestamps and evidence are the only defense.
- **Contradiction drift.** Two records disagreeing, neither marked superseded.
- **Conclusion without conditions.** The single most expensive failure mode: a verdict recorded as
  fact, its test conditions omitted, so its wrongness is invisible until it misleads someone.

Numeric 1-to-10 importance scoring was tried by early systems and largely abandoned as too subjective
to filter on. The ADD/UPDATE/DELETE/NONE gate above replaces it deliberately.
