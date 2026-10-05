<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=90d1dc7b -->
<!-- duplicate-checked: grepped this backlog for "receipt", "UNVERIFIED" and "causal". No hits. Filed from a claude_usage_in_taskbar session per root CLAUDE.md's rule that a finding about the global tree belongs in this repo's backlog. Id reserved via reserve-todo-id.ps1. -->
# The todo template lets a guessed CAUSE be written as fact

**Type:** skill-improvement
**Origin:** ai
**Priority:** Medium

## Goal

A todo that names a cause either carries a receipt for it or labels it `UNVERIFIED`, enforced by the
template and the writing skills rather than by the author remembering.

## Context

Found 2026-09-28 in a claude_usage_in_taskbar release-gate session, by doing exactly the wrong thing
twice in one hour on one finding.

A wdio spec failed on `element (".me-acc-field") still not existing after 15000ms`. I filed a todo whose
Context asserted the cause outright: a commit that hides the account field when the registry holds one
account. I had NOT measured the account count. I then relayed that cause to a peer session **that was
making a release decision**. Reading the spec's own header comment ("the harness's `wdio` daemon
instance starts with an EMPTY accounts registry") I reversed and rewrote the todo to say the first
explanation was wrong. A DOM dump then showed **one** account: the original cause was right, and the
spec's comment was simply stale. Three versions of one file, one wrong claim shipped to a peer, and the
decisive measurement was available for the cost of one spec run the whole time.

Root CLAUDE.md's Execution Discipline already forbids this:

> Before asserting "X does/causes Y because Z" about a system not read or run this session: read it
> first [...] If you can't check right now, write "UNVERIFIED: <claim>, would check <file/log>"

That rule is enforced for **outbound dev-facing prose** (`/ticket`'s ground check,
`hooks/shortcut-create-guard.py`, `hooks/linear-create-guard.py`). Nothing enforces it for a
`.claude/todos/` file, which is the artifact a future cold session trusts most and is least able to
sanity-check, since it arrives with no transcript.

Note what a fix must NOT do: banning causal claims would make todos worse. A labelled guess plus the
one command that would settle it is high-value - my own later todos in that session did exactly that
("UNVERIFIED mechanism [...] would check by dumping the daemon pid/pipe"), and that shape is what made
them useful. The target is the unlabelled assertion, not the hypothesis.

## Approach

Files involved:

- `skills/close/ai-todos-format.md` - the template and field contract every writer follows
- `skills/create-todo/SKILL.md` - the interactive writer
- `skills/code-check/SKILL.md` - writes findings straight to the backlog, same exposure
- `skills/close/SKILL.md` Phase 3 step 2 - the bulk writer

Two candidate mechanisms, cheapest first:

1. **Template-level.** Give the Context section an explicit contract: a sentence naming a cause carries
   either a `file:line` / command-output / log-line receipt, or the literal `UNVERIFIED` token plus the
   check that would settle it. State the failure mode inline so the next author sees why.
2. **Hook-level, only if 1 proves insufficient.** A `PostToolUse` check on writes under
   `.claude/todos/` that greps the body for cause-asserting shapes ("Cause:", "because", "is caused
   by", "The reason is") and, finding no `UNVERIFIED` token and no `:<digits>` receipt nearby, warns.
   Measure the false-positive rate on the existing backlog corpus BEFORE wiring it in, the way
   `tools/dead-probe-check.py` was measured against 143 commits - a noisy guard here would get ignored
   and teach nothing.

Do 1 first and see whether it holds for a few weeks. This is a discipline gap with a known trigger, not
a mechanism gap, so a doc fix may be enough.

## Acceptance

- [ ] `ai-todos-format.md` states the receipt-or-`UNVERIFIED` contract for any causal claim, with the
      2026-09-28 incident named as the why
- [ ] `/create-todo`, `/code-check` and `/close` Phase 3 all point at that contract rather than each
      restating it
- [ ] A spot-check of the next ~10 todos written across repos shows causes either receipted or labelled
- [ ] If a hook is added: its false-positive rate is measured against the existing backlog first, and
      recorded in this file
