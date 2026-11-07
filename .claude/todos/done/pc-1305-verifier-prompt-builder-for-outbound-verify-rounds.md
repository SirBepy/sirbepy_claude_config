<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1302 (guard blocks a GET loop) and pc-1304 (fetch before round 1) are different gaps; no builder for the verifier prompt exists in skills/ticket/scripts. -->
# A prompt builder for outbound-verify rounds, so the 3 identical dispatches are generated, not retyped

**Type:** skill-improvement
**Origin:** ai
**Summary:** Each outbound-verify round needs 3 identical Agent prompts of about 5k characters (template, repo, pointers, requirement-to-source list, planned fields, the draft); on 2026-11-03 one session typed them by hand 22 times across 7 rounds for 3 tickets, and every re-round re-pasted the whole thing with small edits.

## Why

zng-app "Biller Groups ticket decision" chat, 2026-11-03: 3 tickets, rounds of 3 verifiers each (2 + 2 + 3 rounds), 22 dispatches. The ref already says "Fill the template once into a file and reuse that text for all 3 dispatches and later rounds", but the Agent tool takes the prompt inline, so "reuse" still means pasting it, and a draft edit means re-pasting 3 prompts with the new text and remembering to bump the pointer notes (new shas, newly filed sibling ids). The pointers drifted once across rounds (stale file paths in the zng-app prompts, see pc-1304 Notes).

## Goal

One file per ticket holds the prompt's variable parts (repo, branch, pointers, requirement-to-source list, planned non-text fields, draft path). One command prints the finished prompt. A re-round is: edit the draft file, run the command, paste the output into 3 Agent calls.

## Approach

1. `skills/ticket/scripts/verify_prompt.py <spec.md>`: the spec is a small markdown file with headed sections (Repo, Pointers, Provenance, Sources, Fields, Draft path). The script inlines the draft file between the `<<<OUTBOUND-DRAFT` lines and the fixed template text from `refs/outbound-verify.md`, and prints the prompt to stdout.
2. Keep the template text in one place: read it from the ref at run time (between the fenced block markers) so the script never drifts from the ref.
3. In `refs/outbound-verify.md` "Keeping the verify loop short", replace the "fill the template once into a file" bullet with the command.
4. Scratch spec files live under `C:\tmp\<topic>\` like the drafts do today.

## Acceptance

- Running the script on a spec and a draft prints a prompt that ends with the two literal verdict lines and contains the draft verbatim.
- A round can be re-run after a draft edit with no manual prompt editing.

## Verify

- [ ] `python ~/.claude/skills/ticket/scripts/verify_prompt.py <spec>` prints the template's step 5 text unchanged from the ref
- [ ] A diff of two generated prompts for the same spec is empty

## Notes

- Filed by `/close` of the zng-app chat on 2026-11-03. The hook reads the Agent prompt from the transcript, so generating the text changes nothing about how the hook matches it: the pasted prompt still carries the draft between the marker lines.
- Built: skills/ticket/scripts/verify_prompt.py <spec.md> prints the filled verifier prompt (template read from refs/outbound-verify.md at run time, one-pass placeholder fill, draft inlined between the OUTBOUND-DRAFT lines the hook's DRAFT_RE matches, stops if the ref loses a placeholder). refs/outbound-verify.md 'Keeping the verify loop short' now names it. Tests: skills/ticket/scripts/test_verify_prompt.py (new file, no pre-fix version to red-check).
