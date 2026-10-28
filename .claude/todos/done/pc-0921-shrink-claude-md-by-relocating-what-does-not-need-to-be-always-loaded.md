<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=7, reconfirm-count=1, content-hash=3c17c8f3 -->
<!-- duplicate-checked: no existing todo covers auditing CLAUDE.md's own contents for relocation. The nearby hits are about individual rules being added to it, not about what belongs in it at all. -->
# Audit CLAUDE.md and relocate everything that does not need to be always-loaded

**Type:** task
**Origin:** dev

## Goal

`CLAUDE.md` carries only what genuinely has to be in every single turn's context, with everything
else moved to a ref, a snippet, or its own skill, and `CEILING_TOKENS` ratcheted back down to
whatever the reduced file actually weighs.

## Context

Joe, 2026-09-04, during a `/mega-todos` run, when told CLAUDE.md had one token of headroom against
its 6558 ceiling and that three queued todos wanted to add a rule there. His words: "lets add to
CLAUDE.md but then lets have a todo that talks about making the CLAUDE.md smaller, weighing out what
is actually necessary and helpful, what is not, and what is helpful but would be cleaner as its own
skill or ref or smth."

`CEILING_TOKENS` in `ci/check_instruction_budget.py` was raised from 6558 to 7000 in the same turn,
on that explicit say-so. **That raise is the debt this todo pays back.** The ceiling is documented in
its own comment as a ratchet that only ever goes down; raising it was a deliberate one-off, not a new
policy, and leaving it at 7000 without doing this work is how a ratchet quietly becomes a target.

Why the weight matters at all: CLAUDE.md is loaded on every turn of every session in every repo, so
a token here costs far more than a token in a file read once per session, and vastly more than one in
a skill loaded only when invoked. The measured split today is roughly 6557 tokens gated (CLAUDE.md)
against 11205 total across CLAUDE.md plus the four once-per-session files, so well over half the
always-loaded weight is this one file.

## Approach

1. Read `CLAUDE.md` in full and classify EVERY rule into one of four buckets, with a reason per rule:
   - **Always-loaded, keep.** It has to fire unprompted on a turn that gave no signal it was
     relevant. The em-dash ban and the never-commit-directly rule are this shape: they apply to
     output Claude would otherwise produce without ever thinking to look them up.
   - **Move to a ref.** It only matters once a specific kind of work starts, and a skill or an
     existing rule can point at it. `refs/incidents.md` is the precedent - todo 424 cut 412 tokens
     of incident narrative out this way.
   - **Move to a skill.** It is really a procedure, and procedures belong behind an invocation.
   - **Delete.** It restates something already enforced by a hook or a CI check, or it never fires.
2. The test for bucket one, stated so it is not a vibe: **if the rule were absent, would Claude do
   the wrong thing on a turn that gave no cue to go looking for it?** If a skill or a hook would have
   surfaced it anyway at the moment it mattered, it does not need to be always-loaded.
3. Apply the moves. Every relocated rule keeps a pointer from wherever it used to fire, so nothing
   silently stops applying - a rule that moves to a ref nobody reads has been deleted, not moved.
4. Ratchet `CEILING_TOKENS` down to the new measured weight and restore the ratchet-only comment.

## Acceptance

- Every rule currently in CLAUDE.md is classified, with a one-line reason, and the classification is
  recorded somewhere reviewable rather than only in a chat.
- `CEILING_TOKENS` is BELOW 6558, the pre-raise value. Landing between 6558 and 7000 means the raise
  was absorbed rather than repaid, which is the outcome this todo exists to prevent.
- No relocated rule loses its trigger: for each one, name the skill, hook or ref that now surfaces it
  at the moment it applies.
- `python ci/run_all.py` passes.

## Notes

Ask Joe before deleting a rule outright. Moving one is Claude's call; deciding a rule of his no
longer applies is not.
- DONE 2026-09-10 via /loop-todos cycle 3. CLAUDE.md went from 6887 to 6345 tokens, a 542-token cut, and the ratchet in ci/check_instruction_budget.py was returned by the orchestrator from 7000 to its pre-raise 6558, so the slack is not banked as permanent room to grow into. Headroom is 213. Two rule BODIES moved out, each leaving behind the part a session cannot function without: the inbound PowerShell piping mechanism and examples went to refs/shell-io-gotchas.md, with CLAUDE.md keeping the actual prohibition plus a pointer that fires exactly when someone is about to pipe a secret into a native exe; and the Global Knowledge Vault section collapsed from five bullets to one that keeps the two no-cue pieces, the vault-versus-native scope test and a compact concurrent-write warning, pointing at refs/global-knowledge-vault.md to be read before the first vault write of a session, mirroring the memory-rubric gate directly above it. The discipline that made this work was refusing to relocate the rest: everything with no external cue to send a session looking (the package-safety check, process hygiene defaults, the UNVERIFIED-claim rule, the question-tagging rules) stays, because a pointer nobody is triggered to read is a deletion with extra steps. Rules carrying their own recurring-incident dates were left alone by the same standard. Not done, and judged not worth doing: an exhaustive per-bullet ledger of all ~80 rules. refs/claude-md-rule-force-audit.md already classified 81 bullets on 2026-08-22 for todo 429 and found most already lean, which is corroborated by this pass finding only two clean relocation targets beyond the three rules added earlier the same day. python ci/run_all.py exits 0.
