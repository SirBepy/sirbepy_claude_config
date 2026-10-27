# name-brainstorm: brief template, dispatch preamble, idea-agent angles

## 1. Brief template (`<out>/00-brief.md`)

Fill every placeholder; remove a section only if it truly does not apply.

```
# Naming brief (shared by every naming agent)

We need a NAME for <product / company>. Today it is called "<placeholder>" (or: it has no name yet).

## What it is
<3-8 bullets from the dev's own words: what it does, how it feels, what it deliberately is not>

## Who it is for
<first customer or user, later markets, language order, company that runs it>

## The sentence tests (how a stranger should guess what it is)
- <e.g. "I want to open up my ___.">  <e.g. "Ask my ___.">  <e.g. "Hey ___.">
- <the local-language form with declension, if the market is not English>
Strategy label per candidate: S1 = a someone you talk to, S2 = a place or object you open (drop one if the dev wants only one).

## Desired qualities, in order
1. meaning clear or strongly suggestive   2. short, easy to say and spell in <languages>   3. tone: <sober/warm/...>
4. available: <TLDs that matter>, no same-name product or company in <market> or in <product space>, not drowned in search
5. no bad meaning in <list of languages>   6. room to grow beyond the first feature, trade or country

## Avoid
Famous brands and products in this space (list them), words the dev rejected, visual or verbal territory the dev disliked.
<Previous rounds: read these name lists and never repeat any of them: paths>

## Output rules (strict; a script parses the files)
- Write results to the file you are told to (Write tool). Final chat message under 15 lines: path, count, top 8 with one line each.
- File: first line `# <your angle>`, then at least 50 lines, each exactly
  `Name | S1 or S2 | origin/language | meaning | the test sentence | risk note`
  One word per Name, ASCII letters only (give the ASCII form of any diacritic), 4-12 letters. Then a blank line and up to 8 lines starting `TOP: `.
- Do not check availability (a script and other agents do). Drop famous brands from your own knowledge.
- Meanings must be real; mark anything unverified UNVERIFIED. No em dashes. Be bold and varied; duplicates across agents are fine.
```

## 2. Dispatch preamble (paste verbatim into every idea-agent and judge prompt)

The dispatch-preamble guard needs three markers: a staging line, `run_in_background` with `FORBIDDEN`, and the screenshots path.

```
Windows. PowerShell for shell commands. Working directory: <PROJECT_ROOT>.

Leave all changes unstaged. Never run `git add`. The main agent will run /commit by pathspec after your report-back.
Never edit files under ~/.claude/. Create or overwrite ONLY the one output file named below, nothing else. `run_in_background` is FORBIDDEN in this subagent, and so is Monitor; do all work synchronously and end with your report. If this dispatch captures screenshots (it should not) they go under .for_bepy/screenshots/<id>/.

First read <out>/00-brief.md in full (and the older name lists it names). It describes the product, the sentence tests and the strict output format.

YOUR OUTPUT FILE: <out>/ideas/N-<slug>.md
```

Then the angle paragraph. Judges use the same preamble with `<out>/judges/N-<slug>.md`; judges that search the web add: "(WebSearch and WebFetch are expected for you; load them with ToolSearch if they are deferred.)"

## 3. Angle catalogue (pick six that fit; tailor each; aim at 50-90 lines)

| Angle | What to mine | Best for |
|---|---|---|
| Descriptive real-world analogues | The place, object or role that already does this job (mailroom, registry, desk, clerk, ledger); direct words, compounds, other-language forms. Sentence-test every candidate | S2, tools with an obvious job |
| Native-language words | The home market's vocabulary for the idea, dialects, ASCII forms, declension check, "is it a dictionary word that Google will bury" | local-first products |
| Latin and Greek roots | Classical words for archive, memory, guidance, messenger; accurate meanings only; combining forms | sober, long-lived brands |
| Metaphor and feeling | What it does for the person (steady, nothing slips, calm); trade tools and nature words that carry it | benefit-led names |
| Invented coinages | 2-3 syllable names that read as names, blended roots, clipped words; flag accidental meanings | wake words, brandable |
| Wildcard and other languages | Myth and folklore companions, animals, words for friend or remember or calm in other languages, surprising pitches | breadth |
| Person names (first names) | Real given names with a fitting meaning, in the dev's languages; unisex; uncommon but real; flag famous bearers | "ask my ___" products |
| Literary confidants | Loyal friends, scribes, secretaries, chroniclers used as first names | person-like |
| Surnames used as first names | Old family names that work as first names; unisex | person-like |
| Invented human names | New first-name-shaped words with a hidden meaning root | person-like |
| Sibling-of-existing-brand | Names that share grammar, sound shape or imagery with an existing product the dev owns (read that product's docs first) | a family of products |
| English words and compounds | Plain English that states the promise, with twists likely to be free | global products |

Always add to every angle: "Reject famous brands, creepy or surveillance-feeling names, cutesy toys, and hustle or urgency words. Check meanings; flag accidental meanings in <the dev's languages> first. Mark gender for person names."
