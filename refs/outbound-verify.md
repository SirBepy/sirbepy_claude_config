# Outbound verify: 3 subagents check the exact text before Claude posts it

> Enforced by `hooks/outbound-verify-guard.py`. Authorized by Joe on 2026-10-05 in a zng-app
> session, built the same day. Settled forks: unanimous 3/3, auto-fix then re-verify on a FAIL,
> exact match after whitespace normalization, tickets and GitHub PRs only.

Covers everything Claude itself posts to a tracker or a PR:

- **Tickets** (Shortcut and Linear, MCP or REST/GraphQL): creation, title or description rewrites,
  comments. A state move or self-assign carries no prose and passes untouched.
- **GitHub PRs** (`gh pr create`, `gh pr edit` with a title/body, `gh pr comment`, `gh pr review`
  with a body, `gh api` writes to `pulls`/`issues/<n>/comments`, the GitHub MCP equivalents).
  `gh api .../issues/<n>/comments` is the PR conversation endpoint too, so a plain issue comment
  through it is gated as well; `gh issue ...` is not.

Out of reach: anything Joe sends himself (Slack, the Drafts panel). The `CLAUDE.md` receipts rule
still governs those, with nothing to enforce it.

This is a second gate, not a replacement for `refs/outbound-ground-check.md`. The ground check asks
"is this work already done?"; this one asks "is every claim in this text true right now?". A ticket
create or claim-bearing update needs both.

## What the hook actually checks

It reads the session transcript, so there is no marker to write and nothing Claude can fake:

1. Every prose field the call sends (title, body, description, comment text) of at least 25
   characters must appear, whitespace-normalized and otherwise **exact**, inside one verified
   draft. Shorter values (label names, a `WIP` title) are skipped.
2. A draft is verified when **3** Agent dispatches from this session carried it between
   `<<<OUTBOUND-DRAFT` and `OUTBOUND-DRAFT>>>` lines, each returned a report whose last verdict
   line is `OUTBOUND-VERDICT: PASS`, and **none** returned `FAIL`.
3. `subagent_type: "fork"` never counts: a fork inherits this session's context, so it is not an
   independent check.

Consequences worth knowing before starting:

- **Any edit after verification needs a new round**, a typo fix included. Finalize the wording,
  run the em dash check, apply Joe's edits, THEN verify.
- **A FAIL poisons that exact text for good.** Dispatching more verifiers until three agree never
  clears it; the text has to change.
- **One draft can cover a batch.** Put the title, body and every comment of one posting into one
  draft and verify once; each field only has to sit somewhere inside it.
- **The text must be visible in the call**: literal in the command, in a `--body-file`/`-d @file`/
  `-InFile`/`--input` file, or in the MCP tool's input. A shell variable defined in an earlier
  call, `gh pr create --fill`, an editor, or stdin is blocked, since the hook cannot match what it
  cannot see.
- **The main session must dispatch the verifiers.** The hook reads the main transcript; verifiers
  a subagent dispatches never show up there.

## Procedure

### 1. Freeze the text

Write out the exact final text: for a ticket, the title plus description, or the comment; for a
PR, the title plus the body file's content; for a review, every comment. Joe sees and approves
this text where the calling skill asks him to; if he edits it, the round below runs again.

### 2. Dispatch 3 identical verifiers

Three `Agent` calls in one message, the **same prompt** for all three (per the zng-app finding that
varied lenses made the verdict flip every round), `model: "sonnet"`, `subagent_type:
"general-purpose"`. Background is fine; the hook reads hand-backs too. Give them the draft and
pointers only, never the conclusions or reasoning that produced it - the point is a check that
does not share the drafting context's assumptions.

Step 3 of the template below (ship review) exists because a plain fact-check round passed 3/3 on
text that still looked sloppy: zng-admin, 2026-10-05/06, a batch of 5 writes had a wrong team
field and an inconsistent batch, caught only when Joe asked for a second round framed as "a
skeptical teammate, don't let me look like an idiot". The causal-claim line in steps 1-2 is the
same fix for a different miss, zng-app 2026-10-06/07 (sc-56167): a "so X is happening because Y"
line passed as "a deduction, not an independent claim" and the conclusion turned out unproven.

```
READ-ONLY DISPATCH

Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.

`run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
before ending your turn.

You are verifying text that is about to be posted to <a Shortcut ticket / a Linear issue / a
GitHub PR>. You did not write it. Check it against the current state of the code and systems, not
against what seems plausible.

Repo: <absolute path>. Tracked branch: origin/<branch> (run `git fetch --quiet` first and read
files with `git show origin/<branch>:<path>`, not the working tree). Pointers: <files, ticket ids,
PR numbers, endpoints the text talks about>. Provenance: <who asked for this posting, and what it
descends from - a todo id, a ticket, a PR>.

<<<OUTBOUND-DRAFT
<the exact text, verbatim>
OUTBOUND-DRAFT>>>

1. List every factual claim in the draft: what code does, what exists or is missing, numbers,
   names, states, who did what. Skip opinions and proposals. A causal or "so X" / "X is happening
   because Y" conclusion is itself a factual claim about the system, not a deduction exempt from
   receipts - list it too.
2. For each claim, one line: CONFIRMED (receipt: file:line at the tracked branch, command output,
   or API response), WRONG (receipt, plus the corrected wording), or UNVERIFIABLE (what you would
   need to check it). A causal claim whose only support is the other claims above is UNVERIFIABLE,
   not CONFIRMED - confirming the inputs does not confirm the conclusion drawn from them.
3. Ship review, beyond the prose: judge the planned non-text fields of the call (team/group, epic,
   owner, custom fields, state moves, links) against the tracker's real values and the nearest
   precedent ticket; for a batch, check the items are consistent with each other; flag wording a
   teammate could misread even when it is factually true. Any finding here is a FAIL, the same as
   a WRONG claim.
4. Verdict: PASS only if every factual claim is CONFIRMED and step 3 found nothing. Any WRONG,
   UNVERIFIABLE, or ship-review finding is a FAIL. End your report with exactly one of these
   lines, alone on its own line:
OUTBOUND-VERDICT: PASS
OUTBOUND-VERDICT: FAIL
```

### 3. Act on the vote

- **3 PASS:** post the exact verified text. For a ticket write, write the ground-check marker
  now (it expires after 120 seconds), then post.
- **Any FAIL, round 1:** fix it without asking. Before rewriting, check the dissenting verifier's
  key receipt yourself when it contradicts the others or what is already known; a verifier can be
  wrong too. Then correct or cut each WRONG claim, hedge or cut each UNVERIFIABLE one, and run
  step 2 again on the new text with 3 fresh verifiers.
- **Any FAIL, round 2:** stop. Do not post and do not start a round 3. Tell Joe in one message
  which claims are disputed, what each verifier's receipt says, and the text as it stands.

## When the hook itself is broken

Set `CLAUDE_OUTBOUND_VERIFY_BYPASS=1` in the session environment (`settings.json` `env`, or
exported before launching). An inline `VAR=1 cmd` prefix never reaches a PreToolUse hook. A hook
crash fails open on its own; a missing `transcript_path` in the payload fails open too.
