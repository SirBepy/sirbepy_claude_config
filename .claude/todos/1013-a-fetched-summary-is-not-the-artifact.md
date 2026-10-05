<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=b90172d0 -->
# The UNVERIFIED rule does not cover an artifact being evaluated for adoption

**Type:** skill-improvement
**Origin:** ai

## Goal

Extend root `CLAUDE.md`'s Execution Discipline UNVERIFIED rule so it also covers a third-party
artifact Claude is asked to judge, not only code and systems. Today a summarised `WebFetch` of a
repo's README counts as grounds for an adopt/reject verdict, and it produced a wrong one.

## Context

2026-09-25. Joe pointed at `https://github.com/ayghri/i-have-adhd` and asked whether it was worth
using as an output style. Claude answered from a single `WebFetch` of the repo landing page, whose
prompt-answering model returned a 10-bullet paraphrase of the README, and concluded "take nothing
from it".

Joe pushed back with "did you actually look into how it works?" Reading
`skills/i-have-adhd/SKILL.md` verbatim (via `raw.githubusercontent.com`) reversed the verdict. The
summary had omitted, entirely:

- the Pre-send check, a 5-item delete list plus a first-line/last-line verification, which is the
  single most mechanically useful thing in the file and had no equivalent in
  `output-styles/silent.md`
- the "When to break the rules" section, six named escape hatches
- `hooks/always-on.{mjs,sh,ps1}` plus `hooks/hooks.json`, an actual SessionStart re-injection
  mechanism
- `evals/` with measured before/after scores, which is what finally justified keeping two rules and
  rejecting a third on evidence rather than taste

Two of those rules were adopted and committed (`03e79a5`). The wrong answer cost one correction
round and would have silently stood if Joe had not asked.

The existing rule in `CLAUDE.md` Execution Discipline covers "a system not read or run this
session" and "a function, endpoint, flag or pattern EXISTS in the code being worked in". Neither
clause reads as covering "what does this third-party repo actually contain", so nothing was
technically violated. That is the gap.

## Approach

1. Read the UNVERIFIED bullet in root `CLAUDE.md` under Execution Discipline.
2. Add one clause: a verdict on a third-party artifact (repo, skill, plugin, package, spec)
   requires reading the artifact's own load-bearing files, and a summarising fetch of a README or
   landing page is not a receipt for what the artifact does. Name the substitution that fails:
   `WebFetch` answers through a small fast model, so its output is a paraphrase, not the file.
3. Keep it one bullet. The rule already has a receipts definition to hang off, so do not restate
   it.

Rejected: making this a `supply-chain-audit` change. That skill is about safety, and this failure
was about accuracy - the fetch was harmless, it was just wrong about the contents.

Rejected: banning `WebFetch` for repos. It is the right tool for "what is this", it is only wrong
as the last step before a verdict. `curl` to `raw.githubusercontent.com` (or the trees API for a
file listing) is the cheap correct move and should be named in the bullet.

## Acceptance

- The UNVERIFIED bullet names the third-party-artifact case and names raw file access as the
  receipt that satisfies it.
- `python ci/run_all.py` passes, including the always-loaded instruction token budget check, which
  a `CLAUDE.md` addition can push over.
- The existing code/system clauses are unchanged; this adds a case rather than rewording them.

## Notes

Peer sweep at file time: `list_peers` showed one idle session in `~/.claude` (`83d15843`,
`awaiting: done`, pid 0) and `read_messages` held nothing about output styles, this repo's
`CLAUDE.md`, or third-party adoption. Nothing to fold in, and per the contract an empty sweep is
not proof of solitude.

Related, same session: the `reference_output_styles_mechanics` memory's restart claim was corrected
the same day, and `feedback_read_the_artifact_not_the_summary` records the behavioural half of this
finding. This todo is only the `CLAUDE.md` rule half.
