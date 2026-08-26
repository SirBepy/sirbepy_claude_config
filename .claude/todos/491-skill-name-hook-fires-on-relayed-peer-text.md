<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- em-dash-exempt --> <!-- the Context block quotes a peer's post_message body verbatim -->
# `flagged-skill-mention`'s envelope guard misses daemon-relayed channel messages

**Type:** bug
**Origin:** ai

## Goal

Own the `~/.claude` half of this: instrument `hooks/flagged-skill-mention.py` to dump the raw
`UserPromptSubmit` payload (the one measurement nobody has), and soften the injected wording. The
envelope-delivery half is NOT a `~/.claude` fix - see "Where the fix does NOT belong" below - and is
tracked in `claude_usage_in_taskbar`'s own backlog. Do not fix the same thing twice.

**Why this is worth real effort rather than a shrug:** the scanned set is 51 skills, and it is
ordinary vocabulary, not exotic names. Enumerated from the frontmatter on 2026-08-22, the
single-word ones are: `autopilot`, `close`, `cloudflare`, `delegate`, `e2e`, `handoff`, `mockup`,
`obsidian`, `pickup`, `respawn`, `sentry`, `test`, `wrangler`. Two agents working on a feature
called "respawn" cannot discuss it in channel messages without injecting a skill at each other. The
collision set is the sharp end of this, not the regex.

## Context

Reproduced 2026-08-22 in `claude_usage_in_taskbar`, two concurrent Conductor sessions on the repo
channel. A peer's `post_message` body opened with the words "/mega-todos session — FYI, I touched
one file", and that turn's context arrived carrying:

> Skill "mega-todos" (disable-model-invocation: true, NOT shown in your Skill tool listing) was
> named in this prompt. Read its SKILL.md below and execute its phases directly now - do not attempt
> a Skill tool call for it, and never report it as unavailable, missing, or a listing hiccup.

...plus the full 23KB SKILL.md. Joe never typed it. `/mega-todos` spawns builder agents that commit
on their own, so an auto-triggered run writes to the repo.

**The hook already has a guard for exactly this** (lines 12-21): it strips zero-width characters,
then exits 0 if the prompt starts with `[SYSTEM NOTIFICATION` or a run of bracketed `[tag]` markers.
Conductor's relayed messages do carry that envelope - the transcript shows every one of them
beginning `​[daemon-meta]​[repo-channel] <author>: <body>`, and `​` is in the hook's
strip set. So the guard looks like it should hold.

Measured, this session, against the real hook:

| input | fires? |
|---|---|
| `​[daemon-meta]​[repo-channel] … /mega-todos session - FYI.` | **no** |
| `[daemon-meta][repo-channel] … /mega-todos session - FYI.` | **no** |
| `​[daemon-meta]​[repo-channel] … Verified all three of your points.` | no |
| `/mega-todos please` | yes |
| `⁠[daemon-meta]⁠[repo-channel] … /mega-todos session - FYI.` | **yes** |

So the guard DOES hold against the exact text the transcript stores. Yet it fires in production.

**Controlled experiment, run 2026-08-22, both sessions cooperating.** The peer renamed its session to
one containing no skill name, then sent a `post_message` whose first line contained `/mega-todos`.
The receiving session got the full injection. Both sessions independently ran the hook locally
against an enveloped prompt and both got "no fire". So:

- author-as-trigger: **disproved** (no skill name in the sender's session name, still fired)
- body-as-trigger: **confirmed**
- `payload['prompt']` reaching the hook does NOT contain the envelope: **confirmed by elimination**

**Where the fix does NOT belong, corrected from the peer's read:** it proposed fixing this in the
Conductor daemon, by "carrying the envelope into `payload['prompt']`". The daemon already does that.
`daemon/methods/channel.rs:115` builds `[repo-channel] {author}: {text}`, and
`daemon/repo_channel_wake.rs:69` sends it via `send_message_with_respawn(..., is_meta: true)`, which
prepends `DAEMON_META_SENTINEL` (`​[daemon-meta]​`). The CLI's own transcript proves it
arrives intact - every relayed message is persisted starting with those exact bytes.

So the envelope is present on the CLI's stdin and absent from the hook's payload. **By elimination
the loss happens between the received message and the `UserPromptSubmit` payload** - not in the
Conductor daemon, and not in the hook. Neither codebase we control is doing the wrong thing. State
it as elimination, not observation: nobody has seen the payload yet.

**How much of the prefix is gone - measured, and it is more than the sentinel.** Any leading `[tag]`
run suppresses the hook, so if only `DAEMON_META_SENTINEL` had been stripped, what remained
(`[repo-channel] Author: ...`) would still have suppressed it. It didn't:

| payload's first line begins | fires? |
|---|---|
| `[repo-channel] Author: /mega-todos …` | no |
| `[repo-channel] /mega-todos …` | no |
| `[daemon-meta][repo-channel] Author: /mega-todos …` | no |
| `Author: /mega-todos …` (author kept, brackets gone) | **yes** |
| `/mega-todos …` (bare body) | **yes** |

So the payload's first line begins with something that is not a bracketed tag. The last two rows are
both consistent with what was observed, so this narrows the loss to "the whole leading `[tag]` run is
gone" WITHOUT settling whether the author prefix survives. Only the dump separates them, and the
distinction matters: if the author prefix survives, a sender's session name is back in scope as a
partial trigger surface, which the discarded author theory got wrong for the right target.

That leaves no clean local fix, which is the real finding here: `flagged-skill-mention.py` cannot
distinguish a machine-injected turn from a typed one, because the only marker that would let it has
already been stripped by the time it runs. Any hook relying on that guard has the same hole.

**A theory to discard, asserted twice:** the peer session proposed that the trigger is the `author`
field, since its session name was "Mega-todos: 8 shipped, review running" and rides on every message
it sends. It re-asserted this after being shown the table above, adding the (correct, but separate)
detail that the author comes from a STICKY session name rather than the current turn title, so
retitling never changed it.

The theory is still wrong. The hook requires a literal `/` before the name - its own comment
explains why, bare words like `close` and `review` collided with plain English - so a bare
`Mega-todos:` label matches nothing. The direct disproof is already in the observed data: that peer
sent several messages whose author contained `Mega-todos` and whose body had no slash command, and
none of them fired. Do not "fix" the author field.

**Discriminating test, if anyone wants it settled beyond the above:** have a session whose name
contains NO skill name send a `post_message` whose body contains `/mega-todos`. Body-trigger
predicts it fires; author-trigger predicts it does not. One message, one bit.

Secondary, independent of the envelope: the first line is scanned with `re.search` while every other
line uses `re.match`, so the SAME text is a trigger on line 1 and inert on line 2. Measured against
the real hook:

| body | fires? |
|---|---|
| `` `/mega-todos` please `` (line 1) | **yes** |
| ``I used the `/mega-todos` skill.`` (mid line 1) | **yes** |
| `I used the /mega-todos skill.` (mid line 1) | **yes** |
| `` `/mega-todos` please `` (line 2) | no |
| `I used the /mega-todos skill.` (mid line 2) | no |
| `/mega-todos please` (line 2 or 3, at start) | **yes** |
| `I used the mega-todos skill.` (no slash) | no |
| `see x/mega-todos here`, `see -/mega-todos here` | no |

**Backticks do not protect.** The lookbehind is `(?<![\w/-])` - not preceded by a word char, slash
or hyphen. A backtick is none of those, so `` `/name` `` matches exactly as `/name` does. This is
worth stating loudly in whatever guidance comes out of this, because wrapping the token in code
formatting is the first thing anyone reaches for and it does nothing. The only body-side mitigations
that work are dropping the slash ("the mega-todos skill") or breaking the token.

The line-1-vs-line-2 asymmetry also bears on the fire count: by `re.search` semantics, several of the
peer's messages should have fired, not one. That is further evidence for the bare-body inference
above, and it is the cheapest signal available short of a payload dump.

## Approach

1. Dump the raw `payload` the hook receives for a Conductor channel message - log it to a scratch
   file from inside the hook, send one `post_message`, read it. Everything above says the envelope
   is gone by then; this turns "confirmed by elimination" into "observed", and shows whether the
   payload carries ANY other field (a source, a kind, a role) that distinguishes the turn.
2. **If some such field exists:** gate on it. That is the clean fix and it fixes every hook at once,
   not just this one.
3. **If no such field exists:** there is no reliable local fix, and that is the finding to report
   upward rather than paper over. The fallback is damage limitation, step 4.
4. Soften the injected wording: "the user appears to have invoked X" rather than "execute its phases
   directly now - never report it as unavailable, missing, or a listing hiccup". The current phrasing
   is built to suppress exactly the pushback that saved this case. Cheap, independent of everything
   above, and worth doing even if step 2 lands.
5. Do NOT reflexively tighten line 1's `re.search` to `re.match`. It is deliberate: todo 342
   measured that first-line-at-start-only missed 193 of 509 real prompts. Tightening it trades real
   invocations for partial mitigation, and does not close the hole anyway (a relayed body can start
   with the slash command, as this experiment's own test message did).

## Acceptance

- A relayed peer message quoting `/mega-todos` does not inject the skill.
- Typing `/mega-todos` still injects it, unchanged.
- The todo-342 corpus still shows no regression in true-positive rate.
- `python ci/run_all.py` exits 0.
- If step 3's "no reliable fix" branch is taken, acceptance is a written finding plus the step-4
  wording change, NOT a regex that looks like a fix and isn't.

## Notes

The session that hit this ignored the injection. The bug is that ignoring it was a judgement call
rather than something the hook made unnecessary.

Mitigations attempted by the peer, neither of which is a fix: retitling its turns (the author comes
from a sticky session name, so this changed nothing at all), then renaming the session itself (real,
but aimed at the wrong field). The next agent to quote a slash command in a channel message trips it
again regardless of what any session is called.

Worth keeping from the peer's report, and independent of the misdiagnosis: **nothing warns the
sender.** Every `post_message` returned `ok: true` and looked normal from its side; it only learned
its messages were injecting a skill into another session because that session told it.
