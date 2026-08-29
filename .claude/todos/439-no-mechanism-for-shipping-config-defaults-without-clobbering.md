<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=3, reconfirm-count=2, content-hash=79260454 -->
<!-- duplicate-checked -->
# No mechanism for updating a config default without overwriting local edits

**Type:** task
**Origin:** ai

## Goal

A deep-merge bootstrap for JSON config, so a tracked default can be updated without clobbering
machine-local edits, and so a fresh machine gets a working config without hand-assembly.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Current state: `settings.json` is tracked directly, `settings.local.json` is not tracked at all (todo
415), and there is no install or bootstrap script anywhere in the repo. Setting up a new machine means
cloning and hoping, and there is no defined answer to "the tracked default changed and this machine
has local edits to the same file".

Reference: `repos/IvanKuzyshyn_dotfiles/bootstrap.sh:200-241` with
`configs/claude/dot-claude/settings.sample.json`. The mechanism:

- The deploy script globs `*.sample.*`.
- If the real target does not exist, copy the sample.
- If the target exists and both are JSON and `jq` is present, **deep-merge with the existing user file
  winning on key conflicts, and arrays unioned and deduped.**
- Otherwise leave the existing file untouched.

Two other corpus repos solve the same problem differently and are worth knowing:
`repos/DazzleML_dazzle-claude-code-config`'s `ccs` seeds personal files **only if absent, never
overwriting** (simpler, no merge), and `repos/davidbaines_claude_configs/claude_configs.py` deep-merges
config fragments with a `{claude_dir}` placeholder resolved per OS.

This is the mechanism todo 415 needs. 415 asks whether `settings.local.json` should be tracked; the
honest answer depends on having a way to reconcile a tracked default with a local override, which is
exactly this. **Do 415's audit first**, since if everything in `settings.local.json` turns out to be
portable and simply moves into `settings.json`, the merge problem largely evaporates and this todo
shrinks to a bootstrap script.

Constraints specific to this environment, both non-negotiable:

- **No shell-written file content.** CLAUDE.md hard-bans `Set-Content`, `Out-File` and `>` for file
  content because Windows PowerShell 5.1 prepends a UTF-8 BOM that breaks `serde_json` and friends. A
  bootstrap script that writes JSON must use `[System.IO.File]::WriteAllText` or be written in Python.
  The BOM incident that produced this rule was itself a `settings.json` corruption, so this is exactly
  the file at risk.
- `jq` may not be present on Windows. The reference implementation degrades to leaving the file alone;
  a Python implementation avoids the dependency entirely and Python is already required by 27 hooks.

## Approach

1. Run todo 415's audit first, or run it here. The answer determines whether this is a merge problem or
   just a bootstrap problem.
2. Decide the shape based on that. If `settings.local.json` ends up holding only genuinely
   machine-local keys, then seed-if-absent (the `ccs` model) is sufficient and simpler than deep-merge.
   Prefer the simpler one if it suffices, and say so.
3. Write it in Python, not shell. This sidesteps both the BOM ban and the `jq` dependency. Read JSON,
   merge, write with explicit BOM-less UTF-8.
4. Define merge semantics explicitly and write them into the script's docstring: local wins on scalar
   conflicts, arrays union and dedupe, and **decide what happens to `hooks` arrays specifically**,
   since a unioned hooks array could wire the same hook twice. That case is the one most likely to
   silently break something.
5. Make it idempotent and prove it: running twice on an unchanged tree must produce no diff.
6. Cover the fresh-machine path too, since that is the other half of the value: the script should
   produce a working config from a clean clone. Note the junction setup (`.claude-personal` and
   `.claude-fibo` are junctions into `skills/`, per memory) is part of a fresh-machine setup and may
   belong here or may deserve its own todo. State which.

## Acceptance

- Written in Python or via `WriteAllText`. Verified BOM-less: check the first bytes are not
  `239,187,191`.
- Merge semantics documented, including the `hooks`-array decision.
- Idempotent: two consecutive runs produce no diff, shown with real output.
- A local edit provably survives a default change, tested on a scratch copy, never on the live
  `settings.json` first.
- Claude Code still starts and `python ci/run_all.py` still exits 0 after any settings change, real output
  pasted.

## Notes

Test on a scratch copy before ever running this against the live `settings.json`. A merge bug in this
file breaks every hook at once, and the existing precedent is a BOM in exactly this file causing a
silent fall back to defaults that then rewrote Joe's config.

If 415's audit shows the merge case is rare, ship the simpler seed-if-absent version. Deep-merge is
only worth its complexity if there is real per-machine divergence to reconcile.
