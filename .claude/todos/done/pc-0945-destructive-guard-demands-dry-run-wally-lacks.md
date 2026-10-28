<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=8, reconfirm-count=1, content-hash=362d356b -->
<!-- duplicate-checked: no existing todo covers destructive-command-guard.py's publish rule; this is about a remedy the target tool cannot offer, not about gate exit codes. -->
# destructive-command-guard demands `--dry-run` for `wally publish`, which wally does not support

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/destructive-command-guard.py` from blocking a package publish with a remedy the tool in question cannot satisfy, leaving no in-session path forward.

## Context

Hit 2026-09-05 in `C:\Users\tecno\Desktop\Projects\sirbepy_roblox`. Joe had explicitly approved publishing `sirbepy/obby-system@0.3.4`. The hook refused:

```
[destructive-command-guard] package publish with no --dry-run/-n ships to a public registry
irreversibly; add --dry-run/-n first. To bypass a false positive, set
CLAUDE_DESTRUCTIVE_HOOK_BYPASS=1 in this session's environment (settings.json "env", or exported
before launching claude) - an inline prefix on the command itself does not reach this hook.
```

But `wally` 0.3.2 has no such flag:

```
$ wally publish --project-path packages/obby-system --dry-run
error: Found argument '--dry-run' which wasn't expected, or isn't valid in this context
USAGE:
    wally.exe publish --project-path <project-path>
```

So the remedy is unreachable. The documented bypass is also unreachable mid-session, since the env var must exist before `claude` launches. Net effect: an action the dev explicitly authorised cannot be performed at all, and the run has to park it.

The rule is correct for `npm publish` / `cargo publish` (both have `--dry-run`). It over-generalises to publishers that do not.

## Approach

Read `hooks/destructive-command-guard.py` and find the publish matcher. Two candidate fixes, pick after reading:

1. Keep a per-tool table of which publishers actually support a dry-run, and for one that does not (`wally`), fall through to whatever the hook's normal "irreversible, confirm" path is rather than demanding an impossible flag. `wally package --output <file>` is the closest real equivalent - it builds the exact upload artifact without uploading - so the message could name that as the pre-flight step instead.
2. If the hook has no non-blocking confirm path, at minimum correct the message for these tools so it does not instruct the operator to pass a nonexistent flag.

Also worth checking in the same pass: whether any other rule in this hook prescribes a flag that its matched tools lack.

## Acceptance

- `wally publish --project-path <p>` either proceeds under the hook's normal irreversible-action handling, or is refused with a message naming an action that actually exists.
- `npm publish` / `cargo publish` with no `--dry-run` are still blocked exactly as today.
- `python ci/run_all.py` passes, including this hook's own `test_*.py` self-tests.

## Notes

Immediate consequence to unblock separately: `sirbepy/obby-system@0.3.4` is committed (`834426a`) and validated but unpublished. See `C:\Users\tecno\Desktop\Projects\sirbepy_roblox\.for_bepy\autopilot-logs\wally-publish-blocked-by-guard.md`.
- DONE 2026-09-10 via /loop-todos cycle 1. wally is no longer told to pass a flag it does not have. hooks/destructive-command-guard.py:233 adds NO_DRYRUN_PUBLISH_RE for wally publish, line 249 excludes it from the CORE add-a-dry-run rule, and lines 254-263 add a MIDDLE-tier match_publish_no_preflight whose message names the real preflight (wally package --output <file>) instead of an impossible flag. Both directions proven with real hook output: wally publish now returns exit 0 with permissionDecision ask and a reason quoting wally package --output, carrying no "add --dry-run" text; npm publish is still CORE-denied at exit 2 with the original wording. python ci/run_all.py exits 0. Out-of-scope and NOT verified this run, filed as its own todo instead of guessed at: whether gem push, twine upload and yarn v1 publish actually support --dry-run, since the same generic matcher prescribes it for them too.
