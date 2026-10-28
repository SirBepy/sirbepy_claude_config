<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Nothing mechanically blocks a Croatian AskUserQuestion card to Joe

**Type:** skill-improvement
**Origin:** ai

## Goal

"Reply to Joe in English only" is stated in three places and still gets violated on question
cards. Add a mechanical guard instead of a fourth restatement.

## Context

2026-09-02, zng-app session (sc-55365): a full `ask_user_question` card - question body, all four
option labels and descriptions - went out in Croatian. Joe's reaction: "what the fuck is wrong
with you, ask me in english / we NEVER speak croatian to eachother".

The rule was already recorded everywhere it could be:

- global `CLAUDE.md` communication section
- zng-app auto-memory `user_writing_voice.md`, which explicitly says the rule "covers every
  surface Joe reads, not just prose: AskUserQuestion question text/options/headers included"

That memory entry exists **because of an earlier identical incident** ("i hate reading croatian
when i dont gotta"). So this is the second occurrence of the same failure with the rule already
written down - which is the signal that a written rule is not the fix here.

Distinct from `done/305-check-people-language-before-croatian-default.md`: that one is about
drafting messages Joe SENDS to teammates, where Croatian is often correct. This is about text
Claude addresses to Joe himself, where it never is.

## Approach

A `PreToolUse` hook on the question tools - both the built-in `AskUserQuestion` and
`mcp__cc_conductor__ask_user_question` - that inspects the payload's question/header/option
strings and blocks when the text looks Croatian.

Detection worth keeping cheap and boring:

- Croatian-only diacritics (`ÄŤ Ä‡ Ĺľ Ĺˇ Ä‘`) anywhere in the payload, plus
- a small stopword list (`jel`, `nije`, `samo`, `ovo`, `treba`, `kad`, `sto`, `ako`, `bi`) to catch
  diacritic-free Croatian, which is how Joe himself usually types it.

Both need to tolerate the legitimate case: quoting Joe's own Croatian back to him, or a Croatian
string that is the subject of the question (a teammate message draft being reviewed). A blocked
call should say which strings tripped it and name the escape - simplest is a marker in the
payload, matching how `todo-duplicate-guard.py` lets a false positive through.

Check `hooks/` for an existing text-inspection hook to model this on rather than writing a new
shape from scratch; the em-dash prefilter already does the "scan added text for a banned pattern"
job for commits.

## Acceptance

- A Croatian question card is rejected before Joe sees it, naming the offending strings.
- Quoting Joe's own Croatian back to him still works via the documented escape.
- English cards are unaffected - no measurable latency on the common path.

## Notes

- Filed from a zng-app session per CLAUDE.md's "a finding about the global `~/.claude` tree goes
  in the `~/.claude` repo's own backlog" rule. Not executed there.
- If a hook is judged too heavy for this, the honest alternative is to accept it as a recurring
  miss and say so in the rule, rather than restating the rule a fourth time and expecting a
  different outcome.
- Completed in /mega-todos wave 1, commit c5ed7c1: hooks/croatian-question-guard.py scans both the built-in and MCP ask-question tools for Croatian diacritics and stopwords, with a documented marker to bypass legitimate quoting. 16 test cases pass.
