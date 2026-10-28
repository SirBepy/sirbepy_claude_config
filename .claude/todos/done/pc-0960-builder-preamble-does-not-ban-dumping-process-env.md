<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=9, reconfirm-count=1, content-hash=4093f7a2 -->
<!-- duplicate-checked: this is about a subagent printing the host environment into a transcript, not about secret-scan (which only reads diffs) or about credentials in a dispatch prompt (already covered) -->
# builder-preamble does not stop a subagent dumping process.env into its transcript

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a line to `~/.claude/refs/builder-preamble.md`'s paste block telling a builder never to print
the whole process environment, so an API-probing dispatch cannot spray live credentials into a
session transcript on disk.

## Context

Happened 2026-09-05 in the `roblox-trend-pipeline` repo, during an `/auto-do-todos` run.

A sonnet builder working todo 16 needed to know whether Lune 0.10.4 exposes its own version at
runtime. Probing `@lune/process`, it printed the full `process.env` table to its tool output. That
output included several of the host's live API tokens. It then flagged this itself, under
"Out-of-scope findings", which is the only reason it was caught.

Nothing was written to a file and nothing was committed. `prefilter-gate.sh`'s secret-scan ran
clean on every commit in that run and would never have caught this, because it reads the diff, not
tool output. The exposure is the session transcript under
`~/.claude-personal/projects/<slug>/<session>/`, which persists.

The existing guards all miss this by construction:

- `refs/delegation-doctrine.md` says a dispatch prompt must never CARRY a credential, and names the
  env var instead. That is the opposite direction: the prompt was clean, the builder read the env
  itself.
- `secret-scan.sh` reads added lines in a diff.
- Nothing in `refs/builder-preamble.md`'s block mentions the environment at all.

Enumerating an environment is also a legitimate thing to want (checking whether a var is SET), so
the rule should ban printing values, not ban touching `process.env`.

## Approach

1. Add one sentence to the static block in `~/.claude/refs/builder-preamble.md`, near the existing
   secret-scan paragraph so it reads as part of the same concern. Draft: "Never print the whole
   environment. Checking whether a variable is set is fine, e.g. a boolean test on its presence;
   dumping `process.env` / `os.environ` / `Get-ChildItem Env:` puts live credentials in a
   transcript that persists on disk."
2. Decide whether it belongs in the block itself or only in `refs/delegation-doctrine.md`'s prose.
   The block is what actually gets pasted, and the doctrine file's own history says a requirement
   living only in prose is a requirement builders do not see (todo 791). Prefer the block.
3. Consider whether `hooks/dispatch-preamble-guard.py` should gain a fourth marker for it. Probably
   not: `refs/builder-preamble.md`'s "Read-only opt-out" section already argues against raising the
   rejection surface for a line the pasted block carries unconditionally.

Rejected: extending `secret-scan.sh` to cover tool output. It is a diff-reading script by design,
it has no access to a subagent's transcript, and the exposure is upstream of anything it can see.

## Acceptance

- The paste block in `~/.claude/refs/builder-preamble.md` names the ban.
- The wording permits a presence check and forbids printing values, rather than banning env access
  outright.
- `python ci/run_all.py` passes.
- No change to `hooks/dispatch-preamble-guard.py` unless step 3 concludes otherwise, in which case
  its own test suite is updated with it.

## Notes

Filed from a `roblox-trend-pipeline` session, per the global rule that a finding about the
`~/.claude` tree belongs in `~/.claude`'s own backlog. Nothing in `~/.claude` was edited from that
session.

**2026-09-10:** landed in `refs/builder-preamble.md`'s pasted block, directly after the prefilter
paragraph's secret-scan sentence, per Approach step 1/2. Wording permits a presence check, forbids
printing values. No change to `hooks/dispatch-preamble-guard.py` (Approach step 3's own prediction
held - the read-only opt-out section's reasoning against a fourth marker applies here too, and
`ci/run_all.py` passed 30/30 hook suites unchanged).
- DONE 2026-09-10 via /loop-todos cycle 1. refs/builder-preamble.md line 73-75 now carries the ban inside the pasted block, placed next to the secret-scan sentence as this todo asked so the two read as one concern: printing the whole environment while probing or debugging is forbidden, checking whether a variable is SET stays explicitly allowed, and the paragraph states why the existing gate cannot cover it, namely that secret-scan reads diffs rather than tool output. That last clause is the load-bearing part, since a builder would otherwise assume the prefilter already catches this. hooks/dispatch-preamble-guard.py was left untouched, exactly as this todo predicted in its step 3. python ci/run_all.py exits 0 and the prefilter gate exits 0.
