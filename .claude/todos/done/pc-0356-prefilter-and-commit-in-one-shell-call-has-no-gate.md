<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=9, reconfirm-count=1, content-hash=27881814 -->
# Running `/commit`'s prefilters and `git commit` in one shell call lets a flagged diff through

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it structurally impossible to commit while `comment-noise.sh`, `em-dash.sh` or
`secret-scan.sh` has flagged something, instead of relying on the orchestrator to read the output
before the next line of the same shell command runs.

## Context

Observed first-hand 2026-08-16 in this repo, during an `/auto-do-todos` run.

`skills/commit/SKILL.md` step 8 states the gate correctly: prefilters must "come back clean or
already-trimmed" before `git commit`, and explicitly warns "do not call `git commit` first and
rationalize the check afterward". The orchestrator followed the letter of it and still shipped a
violation, like this:

```
bash skills/commit/comment-noise.sh $F; bash skills/commit/em-dash.sh $F; \
bash skills/commit/secret-scan.sh $F; echo "(clean)"; git commit -q -m "..." -- $F
```

`em-dash.sh` printed two hits. `echo "(clean)"` printed unconditionally right after them. `git
commit` ran in the same non-interactive call, so nothing ever read the flagged output before the
commit landed. Commit `8abd412` shipped two em dashes; `330a59e` removed them one commit later.

The rule was read in full that session and quoted correctly. This is the same enforcement-gap shape
as todo 331: a correct rule with no mechanism, where the failure has no signal until later.

Note the near miss: had `secret-scan.sh` been the script that fired, the same shell line would have
committed a hardcoded credential, and `secret-scan` is the one prefilter `/commit` marks as
never-auto-fixable and always a full stop.

## Approach

Prefer a structural fix. Options, roughly in order of strength:

1. **A prefilter wrapper that exits non-zero.** One script that runs all three and returns a failing
   exit code when any of them prints. Then `&&` between it and `git commit` genuinely gates, and the
   whole sequence collapses to one safe line. This is the smallest change with the biggest effect,
   because it turns "read the output" into "the shell enforces it".
2. **Fold it into a per-todo commit helper.** The same run repeated the sequence
   prefilter -> `git commit` -> `complete-todo.ps1` about thirteen times by hand. A helper taking a
   todo id, a pathspec and a message would remove the retyping AND host the gate from option 1. Note
   `complete-todo.ps1` and `claim-todo.ps1` already establish the shape and the `-RepoRoot` convention.
3. A `PreToolUse` hook on `Bash` that blocks a `git commit` whose command string also contains a
   prefilter invocation. Mechanical, but narrower than it looks: it does nothing about a commit
   issued in a separate call after unread output.

Do NOT "fix" this by rewording step 8. It was read, quoted and followed in every other respect
during the session that broke it.

## Acceptance

- A shell sequence that runs the prefilters and then `git commit` cannot reach the commit when any
  prefilter flags a line.
- The three prefilters still behave identically when invoked individually, since other skills call
  them directly.
- Demonstrated with a real crafted diff containing an em dash: the wrapper exits non-zero and the
  chained commit does not run.

## Notes

- Filed 2026-08-16 by `/close` from that run's own retrospective.
- Related: [[331-dispatch-preamble-not-enforced]] in `done/`, the same correct-rule-no-mechanism
  shape, and its `hooks/dispatch-preamble-guard.py` is a working example of the fix landing as a
  mechanical check rather than louder prose.
- 100f666: prefilter-gate.sh wrapper, exits non-zero so a flagged diff structurally blocks the commit. Verified in a scratch repo: chained gate+commit refused an em-dashed diff, allowed a clean one.
