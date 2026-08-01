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

## Anti-patterns this rubric exists to prevent

- **Bloat.** Volume degrades retrieval. More entries is not more memory.
- **Stale confidence.** An old fact retrieved today reads exactly as authoritative as a fresh one.
  Timestamps and evidence are the only defense.
- **Contradiction drift.** Two records disagreeing, neither marked superseded.
- **Conclusion without conditions.** The single most expensive failure mode: a verdict recorded as
  fact, its test conditions omitted, so its wrongness is invisible until it misleads someone.

Numeric 1-to-10 importance scoring was tried by early systems and largely abandoned as too subjective
to filter on. The ADD/UPDATE/DELETE/NONE gate above replaces it deliberately.
