<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=f4970678 -->
<!-- duplicate-checked: hits 258/274/456/904/986 are all done and cover code moves, comment caps, generated files and binaries, not todo-id references -->
# Commit prefilter should flag "todo NN" references in added code comments

**Type:** skill-improvement
**Origin:** ai

## Goal

A code comment that cites a backlog todo number ("todo 44 fix: ...", "(fork feature, todo 01)") is
caught mechanically at commit time, instead of relying on every builder dispatch's prose
instruction.

## Context

Observed 2026-10-07 in the cueline `/auto-do-todos` run (session bb4ea5ee). Every builder dispatch
said "Code style: comments say why, not what, never reference todo numbers", yet at least five
separate builders still wrote them into source and test comments:

- `src/features/media/pickMediaFolder.ts` ("Shared directory-picker flow ... (todo 45)")
- `src/core/audio/nativeAudioPreviewController.ts` ("Todo 44 fix: ...", narrating history too)
- `src/features/music/musicSources.ts`, `src/store/settingsTypes.ts`,
  `src/features/memes/classifyMeme.ts` ("fork feature, todo 01")
- `src/components/editor/preview/adaptiveReadbackPolicy.ts` and its test ("todo 42: ...")

The orchestrator stripped them by hand each time before committing. The global CLAUDE.md rule
"Comments say why, not what ... never park design rationale in code" covers this in spirit, and
`skills/commit/prefilter-gate.sh` already runs a comment-tense check, but nothing flags a todo id.
That is the same "a flag is a fix, never a louder restatement of the rule" situation
`refs/delegation-doctrine.md` describes for em dashes (todo 290).

## Approach

1. Add a check to the prefilter family (`skills/commit/comment-tense.sh` or a new sibling wired
   into `skills/commit/prefilter-gate.sh`): on ADDED lines of code files (not `.md`), flag a comment
   matching roughly `(//|#|/\*|\*)\s.*\btodo[ -]?#?\d{1,4}\b` case-insensitively.
2. Treatment: fix-and-continue like comment-tense (rewrite the comment to state what IS), not a
   STOP like secret-scan.
3. Exempt `.claude/todos/**` and markdown; make sure a bare `TODO:` marker with no number does not
   match.
4. Add a self-test case alongside the prefilter's existing tests, and update
   `refs/builder-preamble.md`'s prefilter paragraph if the treatment list changes.

## Acceptance

- `bash ~/.claude/skills/commit/prefilter-gate.sh <file>` exits 1 on a file whose diff adds
  `// todo 44 fix: ...`, and exits 0 on `// TODO: handle null`.
- `python ci/run_all.py` passes.
