<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=b221a2da -->
# Skill scripts silently do nothing when invoked via the .claude-personal path

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop skills instructing sessions to run their scripts through a path where those scripts exit 0
having done nothing.

## Context

Found and reproduced 2026-08-10 in hubbub-game-music-guesser.

Skills are loaded from `~/.claude-personal/...` and announce that as their base directory. So
`impeccable`'s SKILL.md says: "if the runtime shows this skill's loaded base directory, run
`node <skill-base-dir>/scripts/context.mjs`". Following that instruction literally produces:

```
node "C:/Users/tecno/.claude-personal/skills/impeccable/scripts/concept-seed.mjs" --scope direction --mode experience
# no output, exit 0
node "C:/Users/tecno/.claude/skills/impeccable/scripts/concept-seed.mjs" --scope direction --mode experience
# full seed output, exit 0
```

`md5sum` confirms the two files are byte-identical, so this is not drift.

Cause: these scripts guard their CLI entry with
`if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) { ... }`.
Node's ESM loader realpath-resolves `import.meta.url`, and on Windows a hardlink resolves to its
canonical MFT name (the `~/.claude` one), so `argv[1]` never matches and the entire main block is
skipped. No error, no warning, exit 0.

The failure mode is the dangerous part: it reads as "the script produced no output" rather than
"the script never ran". In that session it burned several minutes on `--help` and `--schema`
probes before the `.claude` path was tried by chance.

Affected: every skill script using this guard. `concept-seed.mjs` is confirmed; `detect.mjs`,
`serve-question.mjs`, `surface-brief.mjs`, `pin.mjs` and `doctor.mjs` use the same pattern and
should be checked.

Related and already in the vault under `Claude Code.md`: `~/.claude` and `~/.claude-personal` are
per-file hardlinks, so *editing* from either path is safe. Only *executing* is not. That asymmetry
is exactly why this is easy to miss.

## Approach

Two independent fixes; do both, they cover different failure paths.

1. **Make the guard path-agnostic.** In each affected script, compare realpaths rather than raw
   strings, e.g. `fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))`,
   or drop the guard where the file is only ever run as a CLI. This fixes it regardless of which
   path a session uses.
2. **Fix the instruction.** Update `impeccable`'s SKILL.md (and any other skill telling sessions
   to use `<skill-base-dir>`) to invoke through `C:\Users\tecno\.claude\skills\...` explicitly, or
   to normalise the announced base directory from `.claude-personal` to `.claude` before use.

## Acceptance

- Running each affected script through the `.claude-personal` path produces identical output to
  running it through `.claude`.
- A fresh `/impeccable` session following SKILL.md verbatim gets real output from the first
  script invocation.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - every affected script uses a realpath-based main-module guard, and a live run through the .claude-personal path produced real output. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
