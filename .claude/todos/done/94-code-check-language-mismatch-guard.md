<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=25dc1833 -->
# Add a language-mismatch guard to /code-check's convention pass

**Type:** skill-improvement

## Goal
Stop `/code-check` from stretching a rule written for one language onto a diff written in another, which manufactures false findings.

## Context
`~/.claude/skills/code-check/SKILL.md` Step 4 tells the reviewer to judge the diff against written project rules and quote each one. It does not say what to do when the rules and the diff are in different languages.

In zng-app the `.cursor/rules` files are almost entirely Dart and Flutter: naming conventions, enum patterns, `DsButton` and design-system usage, Riverpod, GoRouter, `Spacing` and `CustomColors`. On 2026-07-30 the reviewed diff was one HTML file and four Python scripts, so nearly every rule was inapplicable. Claude added a guard by hand in the dispatch prompt ("do not stretch a Dart rule to fit") and the pass came back clean of false positives. Without that line a reviewer would plausibly have invented breaches.

Claude offered to add this to the skill during that session and deliberately held it back so the `.cursor/rules` change already made could be reviewed on its own. Filed so the idea is not lost.

## Approach
Add a short clause to Step 4, point 3 of `~/.claude/skills/code-check/SKILL.md`: a rule only applies to files in the language or stack it was written for. If a rule targets Dart and the file is HTML, Python or JS, it does not apply and must not be cited. If it is genuinely unclear whether a rule is language-scoped, treat it as an unwritten-rule observation rather than a finding.

Keep it to one or two lines; the skill loads per invocation.

## Acceptance
Running `/code-check` on a non-Dart diff in zng-app produces no findings that cite a Dart-specific rule, without needing the guard to be added by hand in a dispatch prompt.

## Notes

- completed, commit 540c946
