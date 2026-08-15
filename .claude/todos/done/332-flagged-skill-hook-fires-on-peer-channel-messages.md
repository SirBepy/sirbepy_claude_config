<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=9, reconfirm-count=1, content-hash=d8fcc292 -->
# flagged-skill-mention hook fires on peer/daemon channel messages

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop `hooks/flagged-skill-mention.py` from injecting a flagged skill's SKILL.md
when the `/name` appears inside a machine-injected peer or daemon message rather
than a prompt Joe typed. Today a peer session saying "I'm in /close" loads the
whole close skill into the receiving session's turn and instructs it to execute.

## Context

Reproduced 2026-08-14 in `revaire-mobile`. A Conductor peer session posted to the
repo coordination channel; the message arrived as a user turn beginning:

```
<ZWSP>[daemon-meta]<ZWSP>[repo-channel] Hold sign-off until review lands: Go ahead, no
conflict. ... I'm in /close and will not commit anything.
```

The hook fired and injected 20049 bytes of `close/SKILL.md` plus the standard
"execute its phases directly now" instruction. Verified by feeding a
reconstructed payload straight to the script: `FIRED: True`, skill `close`.

Two existing guards both miss this case:

- `flagged-skill-mention.py:15` skips only prompts starting with
  `[SYSTEM NOTIFICATION`. Peer messages carry a different prefix
  (`[daemon-meta][repo-channel]`, preceded by a zero-width space) so they sail
  past.
- `flagged-skill-mention.py:20` limits matching to `first_line`, on the
  reasoning that a real invocation is typed first. That holds for humans but not
  here: a peer's opening paragraph is one long unwrapped line, so a `/close`
  three sentences deep is still "line 1".

The damage is real, not cosmetic. `close` closes the terminal; `autopilot` and
`create-pr` are on the same flagged list. A peer merely *reporting* what it is
doing reads to the receiver as an instruction to do it. In this instance the
receiving session recognised the false trigger and declined, but that is a
judgment call the hook is supposed to make unnecessary - and Joe reports hitting
the same thing separately in another session.

Related but distinct, both in `done/`: `298-handoff-skill-hook-did-not-fire.md`
is the false-negative direction; this is a false positive.

## Approach

**Discriminate on PROVENANCE, not on where the `/name` sits.** Joe rejected a
position rule on 2026-08-14: he routinely names several skills in one prompt and
uses skill names as keywords mid-sentence, so anything that demands the `/name`
lead the prompt breaks his normal usage. Do not re-propose it.

Checked while filing this: the `UserPromptSubmit` payload gives the hook no
"who sent this" field. Other hooks in the tree read `session_id`, `cwd`,
`transcript_path`, `tool_input` - none carries provenance. So provenance has to
be inferred from the message ENVELOPE.

Settled direction - skip the whole prompt when it is a machine-injected
envelope, detected by SHAPE rather than a list of channel names: after stripping
leading whitespace and zero-width characters, the prompt opens with one or more
`[...]` bracketed tags (`[SYSTEM NOTIFICATION`, `[daemon-meta][repo-channel]`,
whatever the next channel calls itself). This subsumes the existing line-15
check, costs Joe nothing, and does not need updating per channel format.

Open, needs Joe: once the envelope guard is in, what should the match SCOPE be?
The current `first_line` restriction (line 20) exists only as a weak proxy for
provenance, and the envelope guard replaces that job. But widening it has its
own tradeoff, since Joe pastes chat logs and CI output into prompts:

- keep `first_line` - smallest change, but Joe's own `/skill` on line 3 keeps
  silently not firing, which is the same bug pointing the other way
- scan the whole prompt - matches how he actually writes, but a pasted log
  containing `/close` would fire
- scan the whole prompt EXCLUDING pasted-log blocks and code fences - the
  behaviour he described, most work

Rejected: leaving it to the model to notice. The hook's own header comment says
its whole reason for existing is that "Claude has to remember a written rule"
is unreliable, so relying on the model to spot a false positive gives back
exactly what the hook was built to guarantee.

Whichever scope lands, add a regression test alongside the existing hook tests
(`test_em_dash_guard.py` is the nearest pattern to copy) covering: a genuine
`/close` typed by Joe (must fire), the same mention inside a `[daemon-meta]`
peer message (must not fire), a `[SYSTEM NOTIFICATION` prompt (must not fire,
already passing), and - if the scope widens - a `/close` inside a pasted log.

## Acceptance

- A peer/daemon channel message containing `/close`, `/autopilot`, or
  `/create-pr` anywhere in its body injects nothing.
- A prompt Joe types as `/close --dont-close` still injects `close/SKILL.md`.
- Joe naming two skills in one prompt still injects both, and a skill name used
  mid-sentence is not penalised for its position.
- The existing `[SYSTEM NOTIFICATION` skip does not regress.
- `hooks/flagged-skill-mention.py` exits 0 on every path, as it does now.

## Notes

- Note the zero-width space characters in the real prefix. A guard matching
  `[daemon-meta` with `startswith` fails unless the prompt is stripped of
  zero-width characters first.
- Filed from a `revaire-mobile` session per the global rule that findings about
  the `~/.claude` tree belong in this backlog. Not fixed here - editing global
  hooks from a project session is off-limits without Joe saying so in that
  session, and he asked for it to be logged.
- Narrow half completed via /auto-do-todos 2026-08-15: hooks/flagged-skill-mention.py now strips zero-width chars then skips any prompt whose normalized start is a run of bracketed [tag] groups, generalising by envelope SHAPE rather than a literal prefix list, so peer/daemon/task-notification envelopes never trigger injection. The [SYSTEM NOTIFICATION prefix check is preserved verbatim. Reproduced the bug before the fix (FIRED True, 19126 bytes injected) and proved it gone after, while a genuine typed /close still fires. New subprocess-based test_flagged_skill_mention.py covers 7 cases including the accepted tradeoff that a Joe prompt opening with [tag] also reads as an envelope. The wider match-scope question (first_line vs whole prompt) was deliberately NOT touched and remains open for Joe, see Open questions.
