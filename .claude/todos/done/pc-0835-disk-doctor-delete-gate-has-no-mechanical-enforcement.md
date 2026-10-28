<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=1, content-hash=bc2fbb19 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for destructive-command-guard / disk-doctor / delete gate: 462 and 776 both name adjacent files but neither touches tier coverage. -->
# disk-doctor's delete-confirmation gate is prose only, and nothing prompts under auto mode

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `skills/disk-doctor/gate.md`'s delete-confirmation gate a mechanical backstop, so the
capability it grants (Claude may run `Remove-Item`, `Clear-RecycleBin`, `cleanmgr`,
`docker system prune`, an uninstaller) cannot be exercised by simply not reading the gate.

## Context

`skills/disk-doctor/gate.md` and `windows.md` were changed on 2026-08-29 to let Claude run a
delete or uninstall itself rather than only handing the command to Joe, gated per item on
`mcp__cc_conductor__ask_user_question`. Joe confirmed the capability in that session.

Verified 2026-08-29 that nothing enforces it:

- `hooks/destructive-command-guard.py`'s CORE tier catches `Remove-Item` only with BOTH
  `-Recurse` and `-Force` AND a drive-root or home target (`hooks/destructive-command-guard.py:222`).
  Its MIDDLE (ask) tier is `match_git_reset_hard`, `match_git_clean_force`,
  `match_sql_delete_no_where`, `match_diskpart` (`:401-406`). No other delete verb appears in
  either tier.
- A scoped `Remove-Item -Recurse -Force C:\Users\tecno\AppData\Local\SomeApp\Cache`,
  `Clear-RecycleBin`, `cleanmgr`, `docker system prune`, and every uninstaller match no tier.
- `settings.json:128` sets `"defaultMode": "auto"`, so those commands do not raise a permission
  prompt either.

So the gate is the only barrier, and a session that never reads `gate.md` has nothing stopping it.
That is the same shape as the `/supervised-run` gap in todo `441` and the testing-floor gap in
`427`: a rule with no enforcement path.

Rated 4/10 during a `/rate-it-and-commit` pass on the change, which is what surfaced this.

## Approach

1. Decide the mechanism. A MIDDLE-tier `ask` in `destructive-command-guard.py` is the obvious fit,
   since a hook `ask` fires even under `defaultMode: auto`.
2. **Measure before wiring, per the hook doctrine in `.claude/todos/PLAN.md`.** A blanket
   `Remove-Item` ask would fire on every scratch cleanup (two ran in the 2026-08-29 cleanup-todos
   session alone) and would get the hook switched off, which is the failure mode
   `dev-backend-guard.py`'s own docstring warns about. Todo `466`'s corpus harness is the tool.
3. Likely shape, to be confirmed by step 2: ask only when the target is outside the session's own
   scratch and repo paths, or only for the specific verbs `gate.md` names
   (`Clear-RecycleBin`, `cleanmgr`, `docker system prune`, uninstallers) plus a scoped
   `Remove-Item` over some size threshold.
4. Add cases to `hooks/test_destructive_command_guard.py` in both directions.
5. Once wired, replace `gate.md`'s "no mechanical enforcement" paragraph with a pointer to the tier.

## Acceptance

- [ ] A delete verb named in `gate.md` cannot run unprompted under `defaultMode: auto`
- [ ] An ordinary scratch cleanup (`Remove-Item C:\tmp\...`) still runs without a prompt
- [ ] Corpus measurement pasted, not just asserted
- [ ] `python ci/run_all.py` exits 0
- [ ] `gate.md`'s enforcement-gap paragraph updated to match reality

## Notes

- Filed during a `/rate-it-and-commit` review of another session's uncommitted work, before that
  work was committed. The doc change itself was kept, since Joe confirmed the capability; only the
  unnamed gap was the defect.
- Related but distinct: `462` (destructive-command-guard should use `_hooklib`'s `ask`) touches the
  same file and would be cheap to land in the same pass.
- Completed in the mega-todos wave 1 run, commits 16c2600 + aace76f: destructive-command-guard.py gained match_disk_doctor_delete covering the recycle-bin, cleanmgr, docker-prune, winget and choco uninstall, Uninstall-Package and a scoped msiexec check, measured against a freshly harvested 86,430-command corpus (9 genuine hits, 0 false positives). gate.md's enforcement-gap paragraph was rewritten by the orchestrator to match, since it sat outside the builder's lane. An ordinary scoped delete stays deliberately uncovered - a broader match would prompt on routine scratch cleanup under defaultMode auto.
