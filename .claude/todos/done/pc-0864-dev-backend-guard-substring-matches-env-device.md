<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# 864 - dev-backend-guard blocks .env.device on an `.env.dev` substring match

**Type:** task
**Origin:** ai
**Created:** 2026-09-01

## Goal

`hooks/dev-backend-guard.py` should block builds against the dev backend without also blocking `.env.device`, which points at a LAN address for local on-device testing.

## Context

Hit in zng-app on 2026-09-01. The command

```
fvm flutter build web --release --dart-define-from-file=.env.device --output c:/tmp/lan6
```

was rejected with the guard's full dev-backend message, naming `'.env.dev'` as what it matched. The file is `.env.device`, a different env whose `API_URL` is a `192.168.x.x` LAN address plus a local core port - exactly the local-testing case the guard exists to steer people toward. `.env.dev` is a proper prefix of `.env.device`, so a substring test matches it.

Real cost: the block is correct-looking and the message is long and confident, so the natural next move is to rename the env file or reach for `CLAUDE_DEV_BACKEND_BYPASS=1` - both of which weaken a guard that was never actually right to fire here.

Worth checking whether the same class of false positive exists for other patterns in that hook (e.g. any name that is a prefix of a longer legitimate filename).

## Approach

1. Read `hooks/dev-backend-guard.py` and find the `.env.dev` match.
2. Make it a whole-token match rather than a substring: require the match to end at a path/word boundary, so `.env.dev` and `.env.dev.json` still trip it while `.env.device` does not.
3. Add a case to that hook's `test_*.py` suite covering `.env.device` (allowed) alongside the existing `.env.dev` (blocked), so `python ci/run_all.py` proves it.

## Acceptance

`python ci/run_all.py` passes, a `--dart-define-from-file=.env.device` command is allowed through, and a `--dart-define-from-file=.env.dev` command is still blocked.

## Notes

- Completed in /mega-todos wave 1, commit 9cc117e: DEV_MARKERS now match on a path or word boundary, so .env.device no longer trips the .env.dev marker. All 20 test cases pass including the new one.
