<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=f9322e1a -->
<!-- duplicate-checked: grepped this backlog and done/ for "run_in_background" and "FORBIDDEN". The hits are about the preamble guard's string checks and about orphan processes, not about the rule lacking a legitimate exception. This is the rule's content, not its enforcement. -->
# The run_in_background ban has no escape for a real concurrency test

**Type:** skill-improvement
**Origin:** ai

## Goal

`refs/builder-preamble.md`'s `run_in_background` ban should either carry a documented exception for
the one case that legitimately needs two processes at once, or say explicitly that such a test is
out of scope for a builder. Right now a builder that needs it has to break the rule to do its job.

## Context

Observed 2026-09-26 in a `countoff` session. **Two independent builder subagents, on unrelated
todos, both broke the same rule for the same reason, and both flagged it themselves rather than
hiding it.** Two sightings in one session is the signal; neither was careless.

The preamble says:

> `run_in_background` is FORBIDDEN in builder subagents, and so is `Monitor` - a long build is
> waited out, never handed off to fire later.

The two cases:

1. **Todo 57's builder** had to prove a probe was safe to run concurrently. Its own words: "for the
   two genuine-concurrency tests I had to start two `node` processes at once, and had to pass
   `run_in_background: true` to do it (two Bash tool calls in one message still doesn't guarantee
   true wall-clock overlap without it)". It then waited them out with a bounded poll loop and
   reported in the same turn. The test it produced is the strongest evidence in that whole todo: two
   concurrent runs of the OLD code gave 40/40 and 39/40, the fixed code gave 40/40 twice.
2. **Todo 56's builder** hit the harness auto-backgrounding a foregrounded suite run past the 600s
   cap, and chose `run_in_background: true` deliberately on the retry so it could read the real log
   rather than end the turn on "still waiting".

**The rule's intent was honoured in both cases**: nothing was handed off to fire later, nothing was
left running, both reported complete results in their own turn. Only the letter was broken, and in
case 1 the letter is genuinely unsatisfiable, because true wall-clock overlap of two processes
cannot be expressed with synchronous foreground calls.

Case 2 is arguably already covered: the preamble's last paragraph describes what to do when the
harness auto-backgrounds a command past its cap. But it describes that as something that happens
TO you, not as something you may choose, so a builder facing a second run reads it as forbidden.

## Approach

The ban exists to stop a dispatch ending with work still in flight, which is the failure it names.
A test that starts two processes and waits for both before reporting does not do that. So the fix
is to make the rule say what it means:

1. Reword the ban in `refs/builder-preamble.md` to prohibit the OUTCOME (ending a turn with
   anything unfinished, or deferring a report) rather than the flag. Name the one allowed use: two
   or more processes that must genuinely overlap in wall-clock time, where the dispatch waits for
   every one of them and reports in the same turn.
2. Make explicit that the auto-backgrounded-past-the-cap paragraph also covers a deliberate retry,
   so case 2 stops reading as a violation.
3. Check whether `hooks/dispatch-preamble-guard.py` needs any change. It only string-checks that
   `run_in_background` and `FORBIDDEN` both appear in the prompt, so a reworded block must keep both
   tokens present or every dispatch in every repo starts failing. That constraint is the reason to
   reword carefully rather than rewrite freely.

Do not simply drop the ban. Both builders stayed honest here, but the failure it prevents (a
dispatch that ends on "will report back") is real and the rule is doing work.

## Acceptance

- The reworded paragraph still contains the literal tokens `run_in_background` and `FORBIDDEN`, so
  `dispatch-preamble-guard.py` keeps passing. Show a dispatch going through with the new text.
- The allowed case is stated concretely enough that a builder needing true concurrency can tell it
  applies to them without asking.
- `python ci/run_all.py` passes.
