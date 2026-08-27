<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=4, reconfirm-count=1, content-hash=c45ee8c9 -->
<!-- duplicate-checked -->
# Prose enforcement is one hardcoded character ban, not a style profile

**Type:** task
**Origin:** ai

## Goal

Generalize the em-dash guard into a voice profile: a documented set of style tells, audited
mechanically, so AI-flavoured writing gets caught rather than only one punctuation mark.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current prose enforcement is narrow but real: `em-dash-guard.py` (Stop hook), `todos-em-dash-guard.py`,
`skills/commit/em-dash.sh` as a commit prefilter, plus `snippets/terse-replies.md` for chat tone. That
covers exactly one character and one tone directive. CLAUDE.md separately carries strong outbound
writing rules (the receipts rule for anything Joe sends as his own words, no estimated percentages,
never draft a reply to a thread not given in full) but those are judgment rules with no detector.

Reference: `repos/mickzijdel_dev-hooks/plugins/writing/skills/voice-profile/SKILL.md`. The mechanism,
which is the part worth stealing:

1. A markdown profile with Do / Don't / banned-words / before-after sections, **built by contrasting
   the person's real writing samples against an AI draft of the same content.** The contrast is what
   makes it a profile rather than a generic style guide.
2. Enforcement via a PostToolUse `voice-reminder.sh` running `voice_audit.py`, which injects an
   advisory nudge and **never blocks**.

Also in the corpus: `conorbronsdon/avoid-ai-writing` (cited in awesome-claude-code), with 49+
AI-writing-tell categories and a deterministic zero-dependency scoring engine with detect, rewrite and
edit-in-place modes. Worth reading for its tell taxonomy even if not adopted wholesale.

Why advisory rather than blocking matters here: the em-dash ban is absolute and mechanically checkable,
so a hard block is correct for it. "This reads like AI wrote it" is a judgment, and a hard block on a
judgment produces workarounds. Note this cuts against the general lesson from the harvest that
prose-only rules fail here; the distinction is that a detector can be advisory and still work, because
it puts the tell in front of the model at the moment it matters.

Scope question to settle early: this applies to at least three different surfaces with different
stakes. Chat replies to Joe (already covered by `terse-replies.md`), committed prose in this repo
(skills, refs, todos, commit messages), and **outbound text Joe sends as his own words** (Slack,
standups, ticket comments). The third is where a voice profile earns the most, because that is where
sounding like an AI actually costs Joe something, and CLAUDE.md already treats it as a distinct scope.

## Approach

1. Read `voice-profile/SKILL.md` for the profile format and the contrast-building method. Skim
   `avoid-ai-writing` for its tell categories.
2. Decide scope first, and treat it as the real fork: which surface does this guard? Recommend
   starting with outbound text Joe sends as his own words, since that is the highest-stakes and the
   most clearly under-served. Committed repo prose is second. Chat replies are already handled.
3. Build the profile by contrast, not from a generic list. This needs real samples of Joe's own
   writing. **That is a dependency on Joe, so ask for samples rather than inventing a profile from
   inferred preferences.** A profile guessed from the tone of past sessions is a made-up profile.
4. Write the tell list from the contrast plus the `avoid-ai-writing` taxonomy, restricted to tells
   actually observed in the contrast. Include the em-dash as one entry so there is one place the prose
   rules live, but **do not remove `em-dash-guard.py`** - a hard block on an absolute rule is stronger
   than an advisory detector, and that guard exists because the rule broke three times anyway.
5. Wire it advisory. If the chosen scope is outbound text, the trigger is not a file write, so a
   PostToolUse hook may be the wrong shape entirely; a skill Claude invokes before drafting may fit
   better. Establish the trigger before writing the enforcement.
6. Measure the false-positive rate on real text before trusting it. Run the detector over existing
   committed prose in this repo and report the hit count.

## Acceptance

- The profile is built from real samples of Joe's writing, not inferred. If samples were not
  available, say so and stop rather than shipping a fabricated profile.
- Scope is explicitly chosen and written down.
- `em-dash-guard.py` still fires; its test still passes.
- The detector is advisory, never blocking, and that is deliberate and stated.
- False-positive count over existing repo prose reported as a real number.

## Notes

The failure mode is a generic AI-slop checklist dressed up as Joe's voice. If the samples are not
there, the honest move is to stop and ask, not to approximate.

Do not fold this into `terse-replies.md`. That governs chat tone with Joe, which is a different
surface with different rules, and merging them would apply chat terseness to outbound professional
writing.
