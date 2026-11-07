# /close: Transcript grounding (long sessions only)

Read on demand from `skills/close/SKILL.md` Phase 1. Also cited by `/commit`'s Pre-push transcript check and `skills/zng-kickoff/SKILL.md` as the recipe for resolving this session's transcript.

"The full session" means the raw transcript on disk, not just what's still in context. Claude Code auto-compacts as it approaches the context limit, so on a long session the early material is already summarized away by the time /close runs - exactly the window where corrections and hard-won facts live. Recalling from a compacted view systematically under-reports them.

Resolve this session's transcript:

1. Read `~/.claude/sessions/*.json` (one per session: `pid`, `sessionId`, `cwd`, `startedAt`). Pick the entry whose `cwd` matches this session's cwd with the newest `startedAt`. That gives `sessionId`.
2. The transcript is `~/.claude/projects/<sanitized-cwd>/<sessionId>.jsonl`, where the folder name is the absolute cwd with `\`, `/`, `:` and spaces replaced by `-` (e.g. `C:\Users\tecno\Desktop\Projects\fibo` -> `C--Users-tecno-Desktop-Projects-fibo`).
3. Fallback if step 1 finds no match: in that project folder, take the most recently modified top-level `*.jsonl`. Ignore `<sessionId>/subagents/agent-*.jsonl` - that's commissioned subagent work, not the dev's own turns.

**Skip this entirely if the transcript is under ~500 lines** - the session was short, nothing compacted, in-context history is already complete and re-reading is wasted tokens.

When it does run: `Grep` the file, never `Read` it whole (transcripts embed full tool payloads and run to megabytes). Target the dev's own turns - lines with `"type":"user"` whose content is text rather than a `tool_result` - since Phase 1 bullets 2 and 5 (in `SKILL.md` "What to compute") are about what Joe said. Pull only enough surrounding context to judge each hit.
