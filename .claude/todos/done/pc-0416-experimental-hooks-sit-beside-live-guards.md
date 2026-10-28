<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Three EXPERIMENTAL hooks sit in hooks/ beside live guards with no separation

**Type:** task
**Origin:** ai

## Goal

Separate not-installed spike hooks from live enforcement hooks, so nothing can mistake a spike for
active machinery (or vice versa).

## Context

Found 2026-08-19 during a full inventory sweep of `~/.claude`.

These three live directly in `hooks/`, alphabetically interleaved with 27 real guards:

- `EXPERIMENTAL-bare-question-detector.py`
- `EXPERIMENTAL-command-chaining-detector.py`
- `EXPERIMENTAL-unverified-mechanism-detector.py`

Each carries a "SPIKE, not installed" docstring banner, which is the only thing distinguishing them.
That relies on a reader opening the file. A directory listing, a glob, a bulk edit, or an agent
skimming `hooks/` sees eleven-ish characters of prefix and nothing else.

This is the same class of problem as todo 414 (a hook whose docstring lies about its wiring state):
wiring status is encoded in prose rather than in structure. Two files in one directory, one live and
one dead, with the difference stated only in a comment, is a setup that fails on the first hurried
read.

Related history, all in `done/`: 308 (bare-question stop hook), 311 (no command-chaining hook), 270
(unverified-mechanism rule third repeat) created these spikes; 344 flagged that one of them
hand-rolls the module loader. None of them addressed where the files live.

## Approach

1. Read all three files. Confirm each is genuinely not wired by grepping `settings.json` and
   `settings.local.json` for its filename. If any IS wired, that is a bigger finding than this todo
   and gets reported, not silently fixed.
2. Pick one of these, do not invent a third option:
   - **Move to `hooks/experimental/`.** Preserves the code, removes it from the live listing.
     Check whether anything references the current paths first (`settings.json`, other hooks,
     `refs/`, skill files, `dispatch-preamble-guard.py`'s allowlists).
   - **Delete them.** Three ideas that were spiked and not adopted. `git log` preserves them, and
     the todos that produced them are already archived in `done/`. Choose this if reading them shows
     no intent to revisit.
3. Whichever is chosen, the naming convention becomes structural, not prefix-based: a hook's
   directory tells you whether it is live. Note that convention wherever hook conventions are
   already documented, if such a place exists; if it does not, that absence is itself worth a line
   in the repo README that todo-from-the-harvest proposes.
4. Re-run the hook self-tests afterwards. Several `test_*.py` files exist in `hooks/`; confirm none
   of them import the moved or deleted modules.

## Acceptance

- No file in `hooks/` top level is a non-wired spike.
- `settings.json` and `settings.local.json` grep clean for the three filenames (or the wiring is
  intact if a move preserved a referenced path).
- Every `test_*.py` in `hooks/` still passes, with the real output pasted, not claimed.
- `git status` shows only the intended moves or deletions.

## Notes

Deletion is the honest default if reading them shows the ideas were abandoned. SSD wear is a
non-issue and `git log` is the archive; do not keep dead code in the live directory out of caution.
Do not "fix" this by strengthening the docstring banner. The banner already says SPIKE and that did
not prevent the ambiguity; that is the evidence the prose approach does not work here.
- Done 2026-08-20, DELETED per Joe's call on the two-option card. Verified unwired first: zero hits for all three filenames in settings.json and settings.local.json. Removed hooks/EXPERIMENTAL-bare-question-detector.py, -command-chaining-detector.py, -unverified-mechanism-detector.py plus hooks/test_bare_question_detector.py and hooks/test_command_chaining_detector.py, which tested only the spikes. Rationale that made deletion the honest default: each spike's own archive note says a revisit would not reuse the code (308 'a smarter regex is the wrong direction', 311's CLAUDE.md rule was deleted outright in b28c296, 270 'next spike should test an LLM judge, not more regex'), and the measurements live in done/270, done/308, done/311 rather than in the code. Reference sweep: em-dash-guard.py's iter_turn_tool_uses docstring no longer points at the deleted spike, PLAN.md's Hook doctrine bullet now says deleted-with-measurements-in-done, and todo 428 records the new structural convention (everything in hooks/ is live; unadopted spikes are deleted, not parked) for the README it proposes. Stale suite counts fixed in skills/commit/SKILL.md, PLAN.md and todo 454's acceptance. python ci/run_all.py exits 0: 11/11 hook suites pass (was 13/13), 83 skills clean, CLAUDE.md 6732/6732.
