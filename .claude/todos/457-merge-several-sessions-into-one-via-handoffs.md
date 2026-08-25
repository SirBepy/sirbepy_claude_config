<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Merge several concurrent sessions into one: many handoffs in, one pickup out

**Type:** skill-improvement
**Origin:** dev

## Goal

Give the dev a supported way to collapse N concurrent chats into one. Each session writes a
handoff, then a single pickup reads **all** outstanding handoffs together, merges them into one
working context, and clears them once consumed. Today the write side works and the read side
does not: `/pickup` claims and executes exactly one id.

## Context

Asked for on zng-app, 2026-08-20. Two Conductor sessions were working the same feature area
(`lib/ui/loan_request_v2/`) at once, both running low on context, with genuinely entangled work:
their edits sat inside each other's files and their commits had a two-way compile dependency.
Wrapping both and continuing in one fresh chat is the natural move, and nothing supports it.

What exists now:

- `/handoff` and bare `/create-todo` both write ONE handoff todo and prepend one PLAN.md line
  (`~/.claude/skills/close/ai-todos-format.md`, "Handoff mode" section - the single source of
  truth both read from).
- `/pickup` (`~/.claude/skills/pickup/SKILL.md`) selects the first unclaimed PLAN.md line, claims
  that one id, briefs it, executes it. There is no notion of "consume several related handoffs
  as one brief".

The concrete failure this prevents, observed directly in that session: the two sessions
negotiated a shared protocol over roughly six peer-channel messages - who owned which files, the
commit ordering that kept every commit compiling, which of each other's lines rode along in whose
commit. Two independently-written handoffs would each describe that protocol from one side, and a
fresh chat reading both gets two partial, partly-contradictory accounts of the same agreement
with no signal about which is authoritative.

Related prior art, both read in full before filing this:

- `done/48-handoff-skill-two-file-merge-mode.md` - the WRITE side of the same motivation
  (`/handoff --split` producing a short PLAN.md-mergeable file plus a long companion). Dropped
  via `/cleanup-todos` 2026-08-11 as a one-off, dev-confirmed, because the hand workaround was
  fine. This todo is the READ side and is dev-asked rather than ai-noticed; the "one-off" decline
  reason is also weaker now that the same need has recurred.
- `done/271-close-phase2-scope-multisession.md` - `/close`'s review scope on a shared branch.
  Same underlying reality (several sessions, one repo, one branch), already fixed there. Worth
  reading for how it identified "this session's" work, since a merge pickup needs the inverse.

## Approach

Sketch, not settled:

1. Decide the entry point. Either a new skill (`/merge-sessions`, `/pickup --merge`) or a mode on
   `/pickup` that triggers when more than one handoff todo is outstanding. A mode is cheaper and
   keeps one picker; a separate skill is more discoverable for a deliberate act.
2. Identify the set to merge. Handoff todos are ordinary todos today with nothing marking them as
   handoffs - the Type is always `task` and Origin always `dev`. Merging needs them
   distinguishable, so either add an explicit marker in Handoff mode's template or derive the set
   from PLAN.md ordering plus a "handoff" heuristic. The marker is the honest fix.
3. Read all of them, then produce ONE brief rather than N summaries in sequence. The valuable part
   is reconciliation: what both agree on, what only one knows, and where they contradict. A
   contradiction is surfaced to the dev, never silently resolved.
4. Clear them once consumed - see the open question in Notes about what "clear" means here.
5. Claim protocol: the contract's mutex is per-id. Merging N todos means claiming N ids, and a
   partial claim (some ids already held by a live session) needs a defined behavior - most likely
   abort and report rather than merge a subset.

## Acceptance

- With two or more handoff todos outstanding, one invocation produces a single reconciled brief
  covering all of them, with contradictions between them called out explicitly.
- Handoffs consumed by that run are cleared, and their PLAN.md lines pruned.
- A single outstanding handoff behaves exactly as `/pickup` does today - no new ceremony.
- Merging aborts with a clear message when any target id is held by a live claim, rather than
  silently merging the rest.

## Notes

- **Open question the dev owes an answer on: what "delete" means.** He asked for the handoffs to
  be deleted after they're read. `close/ai-todos-format.md` currently says the opposite for every
  executor: "Done tasks: move the file to `done/` ... never plain-delete a completed todo." Either
  a merged handoff moves to `done/` like everything else (contract-compliant, keeps the history a
  later session may want) or merge mode is a sanctioned exception that genuinely removes them.
  Do not pick this silently - it edits a rule the whole todo system depends on.
- Open: whether the merged result is itself written as a new todo (so the merge survives the
  merging session dying) or lives only in the session's context.
- Origin is `dev` - asked for directly on 2026-08-20, mid-session, while deciding how to wrap two
  chats at once.
