# CLAUDE.md rule-force audit

Todo 429 proposed prefixing every `CLAUDE.md` bullet with ALWAYS / NEVER / PREFER / AVOID, and
called the classification itself "the real find" rather than the tags. **The tags were not
applied. This file is the find.**

Audited 2026-08-22 against `CLAUDE.md` at 145 lines / 81 list-item bullets. Costs nothing against
the token ceiling, because nothing here is loaded.

## Why no tags were applied

- One unverified community report is the whole evidence base for tagging improving compliance.
- ~143 tokens against a ceiling that todo 424 had just spent real work cutting.
- Joe does not review diffs, so an 81-bullet force reclassification would land unreviewed, and
  429's own Notes name that as where "a 'Prefer' quietly becomes an 'ALWAYS'".
- This repo's own record says force comes from hooks, not adjectives. `hooks/em-dash-guard.py` is
  why the em-dash rule holds; no wording made it hold.

## The four findings

**1. Four entries are not rules at all. They are scope definitions.** Tagging them would invent a
force they never had, which is the specific damage 429's Notes warn about:

- Testing floor: *"Slow end-to-end suites are NOT part of this floor; projects opt in via..."*
- Testing floor: *"`/test` means the normal (fast) tests... `/e2e` is a separate command"*
- The whole `.for_bepy Folder` section, which is a directory description
- Subagent section: *"Full-orchestrator mode... Adopted by `/delegate` and `/autopilot`, not by
  default"*

These define a boundary. They instruct nobody.

**2. One bullet carries two different forces in a single sentence.** Packages:

> Prefer a subagent for the research; required for anything load-bearing or crypto/network.

`Prefer` is a default. `required` is absolute. A single tag on this bullet would have to pick one
and would silently demote or promote the other half. **This is the only real tagging casualty in
the file, and it is an argument for splitting the bullet, not for tagging it.**

**3. Exactly one genuine AVOID exists in 81 bullets.** Subagent model tier:

> Above sonnet (opus/fable): almost never.

It then names three specific escape conditions. Nothing else in the file occupies that middle
ground. A four-value tag vocabulary for a file with one AVOID is over-built.

**4. The soft defaults are already unambiguous in prose, and there are only five.** Everything
else reads as absolute and is meant that way. The five:

| Bullet | Section | Reads as |
|---|---|---|
| "Default to PowerShell... Fall back to Bash only if" | Shell Commands | PREFER |
| "Prefer the platform primitive over a library" | Execution Discipline | PREFER |
| "Work quietly... Surface mid-task only for a real decision" | Communication | PREFER |
| "Falsified theories are worth saving" | Memory Discipline | PREFER, and arguably not a rule |
| "Tune `effort` freely" | Subagent model | PREFER |

Each already contains its own hedge word. A `PREFER:` prefix would restate what the sentence says.

## Conclusion

The distinction tagging was meant to expose is already carried by the prose in 76 of 81 bullets,
absent in 4 that are not rules, and genuinely broken in exactly 1. **Fix the 1 by splitting it;
tagging the other 80 buys nothing.**

## Re-open trigger

This was a judgement call on current evidence, not a permanent close. Re-open 429's tagging half if
either becomes true:

- A recorded incident traces to a rule being read at the wrong force. None exists today; the
  closest, the unasked-for push of 2026-08-21, traces to a file going unread, not to a rule being
  misread once read.
- `CLAUDE.md` bullets exceed ~120, at which point scanning for priority is a different problem than
  it is at 81.
