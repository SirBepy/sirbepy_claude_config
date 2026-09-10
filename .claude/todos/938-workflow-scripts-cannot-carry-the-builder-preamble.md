<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=7, reconfirm-count=1, content-hash=f47991b1 -->
<!-- duplicate-checked: done/472 gave us build-dispatch.ps1 so the block stops being retyped from memory. This is the NEXT gap: the script's output has no route into a Workflow script at all. Different failure, different fix. -->
# A Workflow script cannot carry the builder preamble without corrupting it

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/mega-todos` a working way to put the canonical preamble plus the injected commit block into a
Workflow script's `agent()` prompts, or state in the skill that the Agent tool is the sanctioned
vehicle when the preamble is involved.

## Context

Hit for real on 2026-09-05 during a `/mega-todos` run in
`C:\Users\tecno\Desktop\Projects\server_supervisor`. The run used the Agent tool instead of the
Workflow tool and reported the deviation, because there is no safe way to do what the skill asks.

`skills/mega-todos/SKILL.md` says to author the run as a Workflow script, and Workflow scripts are
plain JavaScript passed as the `script` parameter. Prompt text therefore has to live in a JS string
literal. The preamble that must be pasted VERBATIM (`refs/builder-preamble.md`'s fenced block, plus
the SKILL's own COMMITTING block) contains both:

- roughly 60 backticks, which terminate a template literal, and
- Windows paths such as `C:\Users\tecno\.claude\hooks\` and
  `Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-..."`. In a JS template literal
  `\t` is a TAB and `\U`/`\c` are silently-consumed escapes, so `\tecno\` becomes a literal tab plus
  `ecno\`.

So a correct script needs every backslash doubled AND every backtick escaped, by hand, across ~8KB
of text that the whole point of `refs/builder-preamble.md` is to stop anyone retyping. A single
missed backslash does not fail loudly - it silently alters the preamble a builder is told to obey.
`String.raw` does not help: it fixes backslashes but still cannot contain an unescaped backtick.

`skills/mega-todos/build-dispatch.ps1` (from done/472) does not close this. It emits finished prompt
text to stdout, and a Workflow script has no filesystem access, so there is no route from that
output into the script other than reading it into the orchestrator's context and re-emitting it,
which reintroduces exactly the hand-transcription risk.

## Approach

Options, roughly in order of preference:

1. Give the Workflow tool (or the skill) a way to reference a prompt file on disk, so `agent()` can
   take a path instead of an inline string. Cleanest, but may need a Workflow tool change rather
   than a skill change.
2. Have `build-dispatch.ps1` gain a `-AsJsLiteral` switch that emits the prompt already escaped for
   a JS template literal (backslashes doubled, backticks escaped), so the orchestrator pastes an
   escaped blob it did not have to escape itself.
3. Amend `skills/mega-todos/SKILL.md`'s Step D to say plainly that when a run needs the verbatim
   preamble, the Agent tool is the sanctioned vehicle and the Workflow tool is for preamble-free
   fan-outs, so a run following the skill is not forced into an undocumented deviation.

Whichever is chosen, the skill's "if the Workflow tool is unavailable ... do NOT silently fall back"
wording should be widened, since the real case is "available but structurally unusable here".

## Acceptance

- A `/mega-todos` run can dispatch builders with a byte-exact preamble without hand-escaping.
- `skills/mega-todos/SKILL.md` says which vehicle to use and why, so a run does not have to invent
  the answer mid-flight.
- `hooks/dispatch-preamble-guard.py`'s three markers still pass on whatever route is chosen.

## Notes

Filed 2026-09-05 by `/respawn`'s retrospective, from a `server_supervisor` `/mega-todos` run.
