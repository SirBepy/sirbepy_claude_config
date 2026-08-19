<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=5, reconfirm-count=1, content-hash=11dbc1bd -->
# "Claim-bearing" is defined in three places and they can drift apart silently

**Type:** task
**Origin:** ai

## Goal

Give the outbound gate one authoritative answer to "does this write assert something about the
code", instead of three independent ones that must be kept in sync by hand.

## Context

Found by `/code-check` during the 2026-08-18 `/close`, on code written earlier that same session.

Joe's decision was that ticket UPDATES are gated only when **claim-bearing** (they rewrite text),
never for state moves or self-assign. That rule is now encoded three separate times, in three
different notations:

1. `hooks/shortcut-mutation-guard.py:42` - `CLAIM_BEARING_KEYS = ("name", "description", "text")`,
   matched against `tool_input` dict keys.
2. `hooks/linear-update-guard.py:44` - `CLAIM_FIELD_RE = re.compile(r"\b(title|description)\b")`,
   matched against a raw command string.
3. `refs/outbound-ground-check.md` - the prose rule in its "Updates are a different question"
   section, which is what a human or agent actually reads before writing the marker.

Note they already disagree in vocabulary: Shortcut calls it `name`, Linear calls it `title`. That
part is legitimate, the platforms genuinely differ. The problem is that **nothing connects them**,
so adding a fourth claim-bearing field means finding all three sites unaided, and missing one
produces a silent hole rather than an error.

The failure mode is asymmetric and quiet: a missed field means a claim-bearing write sails through
ungated, and no test fails, because the tests assert current behaviour rather than the rule.

## Approach

The two mechanisms cannot be merged; one inspects a dict, the other regexes a string. So unify the
KNOWLEDGE, not the code:

1. Put the canonical field list in `hooks/_hooklib.py` as a per-platform mapping, e.g.
   `CLAIM_FIELDS = {"shortcut": ("name", "description", "text"), "linear": ("title", "description")}`.
2. Have each guard derive its own matcher from that mapping rather than restating the fields, so the
   regex is built from the tuple instead of hand-written alongside it.
3. Make `refs/outbound-ground-check.md` point AT the mapping rather than restating the list in prose,
   the same "reference the ref, don't re-type it" principle
   [[373-rate-it-panel-dispatch-fails-preamble-guard]] applies to the builder preamble.
4. Add one test asserting each platform's guard gates every field in its own list, so a future
   addition to the mapping fails loudly if a guard doesn't honour it.

## Acceptance

- Adding a field to the mapping causes both the guard behaviour and the test expectation to follow,
  with no other file edited.
- A comment-only or state-move update still passes ungated on both platforms; a title, name,
  description or comment write still requires a fresh marker.
- All hook suites pass.

## Notes

- Do not widen what counts as claim-bearing while doing this. Joe chose the narrow scope explicitly
  on 2026-08-18, and `refs/outbound-ground-check.md` states the reasoning: *"a gate that fires on
  maybes trains the dev to click through, which turns stopped back into informed."*
- Related: [[380-guard-hooks-duplicate-their-marker-constants]] moves the other shared guard
  constants into the same file, and is worth doing in the same pass.
- de55513: claim-bearing field list unified into _hooklib.py as a separate CLAIM_FIELDS mapping; both guards derive their matcher. Scope deliberately not widened.
