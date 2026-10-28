<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 101 (rubric read gate), 1039 (reachability bracket parsing) and 1239 (no rule for block headings) are different; this is the verified: edit bumping mtime and two redaction shapes -->
# recall redaction edges (multi-word fence info, repeated label) and cleanup-memory's verified: edit bumping mtime

**Type:** task
**Origin:** ai
**Summary:** Recall's redaction never leaves a labelled password visible in two remaining shapes, and re-verifying a memory does not push it into the index's Recent block.

## Why

Found by the 2026-10-28 pre-push reviews: a multi-word fence info string and a repeated label both leak the password value.

## Goal
`recall.py redact()` never leaves a labelled password visible in the two remaining edge shapes, and `/cleanup-memory` re-verification does not push old memories into the index's Recent block.

## Context
Found by the 2026-10-28 pre-push reviews (8910486 fixed CRLF and a single-word spaced fence info string).
- `skills/recall/recall.py:92` `FENCE_OPEN_RE` accepts one optional token after the fence; a multi-word info string (`Password:\n``` python title\nhunter2xyz`) leaks the value. CommonMark allows any info string (no backticks for backtick fences).
- `recall.py:102-115`: `Password:\nPassword:\nfakeword1234` redacts the second label line as the value and leaves the real value visible.
- `skills/cleanup-memory/SKILL.md:71` (Step 1.6) sets `verified:` to today on a re-verified memory, which bumps its mtime; Step 4 (`:128`) forbids touching a memory just to mark it checked because Step 6.5 sorts the index by mtime and touched files become "Recent".
Redaction fixes need a `REDACTION_VERSION` bump so indexed sessions are re-cleaned (see 8910486).

## Approach
Accept any info string on a fence opener (or treat any fence-opener line as never-a-value); skip a line that itself matches the label pattern when looking for the value. For cleanup-memory, keep the verified date in the sidecar log or exempt `verified:`-only edits from Recent classification.

## Acceptance
`skills/recall/test_recall.py` gains both shapes (fail first, then pass); cleanup-memory's Step 1.6 and Step 4 no longer contradict.
