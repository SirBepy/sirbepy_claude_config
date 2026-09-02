<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "cargo", "pipe", "quote", "mask". 780 (done/) shipped the
     guard; 877 wants it widened to build/check/clippy. Neither covers quote handling. -->
# cargo-test-pipe-guard fires on a `cargo test | tail` string inside a quoted argument

**Type:** task
**Origin:** ai

## Goal

Stop `hooks/cargo-test-pipe-guard.py` blocking a command that only *mentions* a piped cargo test
inside a quoted string, rather than actually running one.

## Context

Reproduced 2026-09-02, on the second shell command after wiring the guard, by the orchestrator that
had just dispatched todo `780`. The blocked command was a probe feeding a JSON payload to the guard
itself:

```
echo '{"tool_name":"Bash","tool_input":{"command":"cargo test --lib 2>&1 | tail -25"}}' | python hooks/cargo-test-pipe-guard.py
```

Nothing here runs cargo. The `cargo test` text and the `| tail -25` both sit inside a single-quoted
JSON literal. The guard splits the command on `|` without tracking quote state, so it sees segment
one ending in `cargo test --lib 2>&1` and segment two starting with `tail`, and denies.

**780's builder considered this case and concluded it was already handled**, recording in its report:

> Did not add quote-masking/command-position checks (unlike shell-content-write-guard) since the
> todo's scope is narrower [...] the "mentioning cargo test in a grep pattern" case still passes
> correctly because it lacks a cargo-test segment feeding a downstream filter in the same pipeline.

That reasoning holds for a `grep` pattern with no pipe in it, which is what was tested. It does not
hold for a quoted string that itself contains a pipe, which was not.

**The failure direction is SAFE** - a false positive that blocks a harmless command, never a false
negative that lets a real hang through. This is a usability defect, not a correctness hole.

The sibling guard is the counter-example worth copying: `hooks/dev-server-guard.py` (todo `441`,
landed the same run) tokenizes with `shlex` and checks command position, and was probed the same day
with `grep -c "npm run dev" refs/process-hygiene.md` - it correctly did NOT fire.

## Approach

1. Reproduce first, exactly as above. Confirm the guard's own `hooks/test_cargo_test_pipe_guard.py`
   passes before and after, so the fix is additive.
2. Mask quoted spans before splitting on `|`. `hooks/shell-content-write-guard.py` already does this
   for redirect detection and is the in-repo precedent named by 780's own todo; check whether its
   masking helper is reusable as-is rather than writing a second one. If it belongs in
   `hooks/_hooklib.py`, note that 19 guards import that file and treat the move as its own change.
3. Alternative, cheaper, and worth pricing before doing the masking: require the `cargo` token to be
   in command position within its segment (the `dev-server-guard.py` approach). A `cargo test` buried
   mid-string is never in command position, so this may fix the whole class without any quote
   tracking.
4. Add the reproducer above as a fixture case, plus a `git commit -m "..."` whose message quotes the
   same example - that shape is reachable whenever a commit or todo describes the very bug the guard
   exists for, which is exactly what this repo does constantly.

## Acceptance

- The reproducer command above runs without being blocked.
- A genuinely piped `cargo test --lib 2>&1 | tail -25`, unquoted, is still blocked.
- `cargo build 2>&1 | tail -5` is still NOT blocked (780's own negative).
- A commit message quoting a piped cargo-test example does not block the commit.
- `python ci/run_all.py` exits 0.

## Notes

- Worth roughly a 6. Cheap to fix, and it fires on the exact shape used to document and test the
  guard, so it will keep being hit by whoever works on the guard next.
- Coordinate with `877`, which wants the subcommand list widened to `build`/`check`/`clippy`.
  Widening the trigger set without fixing this makes the false-positive surface strictly larger, so
  do this one first if both are picked up.
