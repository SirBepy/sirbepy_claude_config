# name-brainstorm: judges and shortlist template

Dispatch three judges in one message with the preamble from `angles.md`: `general-purpose`, `model: 'sonnet'`, `effort: 'high'`. Each reads the brief, every file in `<out>/ideas/`, and `<out>/names.txt`; each writes its own file `<out>/judges/N-<slug>.md` and returns under 25 lines. Judges do not wait for availability. Add the product's one-line description and the sentence tests to each prompt.

## Judge 1 - sentence tests and wake word (or meaning clarity)

Score plausible candidates (skip losers fast) on: does the sentence test read naturally ("ask my X", "open my X", "Hey X"); would a stranger guess the purpose; wake-word quality (2-3 syllables, distinct from common words and famous assistants, works with the local accent); declension and natural use in the local language; warmth and trust. Be harsh; reward names found independently by several agents.
Return: ranked top 25 with scores and one line each; 10 names to kill despite popularity, with reasons; 10 new ideas of its own.

## Judge 2 - language risk, famous bearers, search crowding (uses WebSearch)

Part A from knowledge: for about 80 candidates screen for bad or silly meanings and sound-alikes in the market languages (plus German, Italian, Spanish, French, English), famous people or characters who would dominate the name, brand and product clashes in the product's space, religious or political baggage, being the same word as an existing product of the dev in a neighbouring language.
Part B with web search: for the 30 best survivors run quick searches (`<name> app`, `<name> startup`, `<name> d.o.o.` or the local company suffix, `<name> AI assistant` or the space) and give a verdict CLEAR / CROWDED / CONFLICT with the competitor names and URLs actually seen. Never claim anything about a result it did not see. State that the search tool is fuzzy and "nothing found" is not proof of freedom.
Return: the 30 verdicts with evidence, names dropped in Part A with reasons, a final top 10 on safety plus distinctiveness.

## Judge 3 - brand story, trust and room to grow

Imagine the name on a splash screen, a chat header, an app-store listing, an invoice. Judge: the one-sentence story a user repeats; fit with the product's tone; trust (would you tell it everything); room to grow; logo shape; international reach; whether it can sit beside the dev's existing products as a family; penalise names that imply spying, servitude, one famous bearer, one trade or one country.
Return: ranked top 20 with a brand score, one-line story each; three family strategies with the best 3 names in each; 10 new ideas of its own.

## Synthesis rules

- Consensus beats a single top rank. A judge's new ideas were scored by nobody else: label them so and run them through the checker.
- Drop names the judges killed on language, trust or conflict even if the idea agents loved them.
- Check any domain claim the dev disputes directly (DNS, whois, RDAP) before repeating it.

## Shortlist README template (`<out>/README.md`)

```
# <Product>: name candidates and checks (<date>)
<one paragraph: what the product is, process used, "Status: shortlist only. Nothing is decided.">

## The finding that shapes the choice        (what is free and what is not; sentence forms if bare names are gone)
## Shortlist                                  (table: name | meaning | .com | .hr/.local | .io | .ai | .app | .eu | judges)
## Names dropped, and why
## Where the three judges landed
## Honest read                                (2-5 bullets: best for X, cost of each; no overclaiming)
## Not checked yet                            (trademarks: EUIPO TMview, national office, WIPO; company register; native speaker; real Google pass; domain prices)
## Files
```

Every fact in it needs a source: a judge line, a script result, or a search you ran. Do not state a name is "free"; write "not registered today".
