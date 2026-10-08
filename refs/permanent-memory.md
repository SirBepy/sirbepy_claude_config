# Permanent memory for Claude - design

Decided with Joe on 2026-10-08 (todo 95's brainstorm session). This file is the design of record.
Phase 1 is built; later phases are designed here and filed as todos, not built.

## What already exists, and the gap

| Store | Holds | Loaded how |
| --- | --- | --- |
| Per-project Auto Memory (`projects/<slug>/memory/`) | project facts, rules for Claude (1,637 files across 86 dirs on 2026-10-08: 803 feedback, 466 project, 359 reference, 9 user) | `MEMORY.md` index, auto-loaded, cut at 24.4 KB |
| Obsidian vault | facts about Joe's world (people, preferences) | read on demand, `refs/global-knowledge-vault.md` |
| `CLAUDE.md`, `refs/`, `code-style/`, skills | global procedure | always / on demand. `CLAUDE.md` has 0 tokens of headroom (ci/check_instruction_budget.py, 2026-10-08) |
| `.claude/todos/` | intent, deferred work | read by the todo skills |

All of that is **facts and procedure**. What nothing held on 2026-10-08:

1. **Episodes.** What was done, discussed, decided, and when. Session transcripts were the only
   record, Claude Code deleted them after 30 days (`cleanupPeriodDays` default 30, read from the
   settings schema inside `claude.exe`), and nothing searched them: `/close` and `/context-left`
   only ever read their own session.
2. **Lessons that cross projects.** A feedback memory learned in zng-app never loads in fibo.
3. **Retrieval.** zng-app's `MEMORY.md` was 24,853 bytes, past the cut, so its bottom entries
   never loaded. Recall is a title skim of one project's index.
4. **Memory at the point of use.** Evidence: a Clockify run skipped the one memory file holding
   the meal-gap rule (todo 1017); Joe restated an overlap rule for the third time (448); a subagent
   hit a Playwright wall already solved in memory because nothing passed it along (53).
5. **Rejected options.** On 2026-08-01 the whole vault design was re-derived while the committed
   design sat in that session's own context (`feedback_context_loaded_is_not_applied`).
6. **Freshness.** Two todos were scored on recorded repros of bugs that were already fixed
   (`feedback_a_recorded_reproduction_goes_stale`, 2026-09-10). Nothing marks a fact as old or
   replaced.

Explicitly out of scope, by Joe's choice on 2026-10-08: live session awareness (old todo 206,
covered by Conductor's `list_peers`), commitments to other people, a memory-evaluation loop, and
off-machine backup. The last one is a known risk, not an oversight: transcripts, the recall
index, digests and all Auto Memory live only on this SSD, and `projects/` is gitignored. One dead
disk loses every layer below except the vault, which is pushed.

## Decisions

| # | Decision | Why |
| --- | --- | --- |
| D1 | Keep every transcript forever: `"cleanupPeriodDays": 36500` in `settings.json` (one file, `.claude-personal\settings.json` is a symlink to it) | Each day at 30 deleted one more day of the only raw record. About 2.7 GB a month raw. |
| D2 | Monthly compressor: on the 1st of month M, every transcript last written before month M-1 began is moved into `memory-archive/transcripts/<YYYY-MM>.zip` (month of its last write) | Joe's rule: in March, compress January, not February. ZIP_DEFLATED, so Explorer can open it by hand. |
| D3 | Compressed chats can no longer be reopened with `/resume`. Accepted. | Joe, 2026-10-08. They stay searchable through `/recall`. |
| D4 | Recall is plain-text search over an extracted index. No embeddings, no database, no daemon. | Measured 2026-10-08: 582 main sessions (2,769 MB raw, subagent files included) reduce to 18.8 MB of text, 0.68% of raw, full scan in 20 s. The July 2026 rate-it panel scored a vector memory server 2/10 at a far smaller scale, and a research agent found a May 2026 paper (arxiv.org/pdf/2605.15184, not read directly by Claude) reporting grep matching or beating vector retrieval on a conversational-memory benchmark. |
| D5 | The index extracts only: Joe's typed turns, Claude's chat text (`send_message` bubbles and plain assistant text), commit lines, session title, repo, timestamps. Hook-injected and skill-expansion turns (`isMeta`), tool output, `[daemon-meta]` peer relays and subagent transcripts are left out. | Those are what a person would remember from the chat; the rest is noise at roughly 99% of the bytes. |
| D6 | Secrets are redacted at extraction, using the shared `hooks/secret-patterns.txt` | The raw transcripts already hold whatever was pasted. The index is a second copy and must not spread it. |
| D7 | `/recall` searches every repo from any session. Each hit is tagged `client` or `personal` (via `hooks/_client_repo.py`) and names its repo. | Joe, 2026-10-08. Clockify needs all of them, and nothing leaves the machine either way. |
| D8 | Every recall hit cites session id, date and repo. Recalled text is printed inside a fence labelled as data. | A memory that can't be traced can't be corrected. A pasted web page in an old chat must never act as an instruction today (memory poisoning). |
| D9 | The index is derived and disposable: delete `memory-archive/index/` and the next run rebuilds it from raw and zipped transcripts. Digests (phase 2) are not derived and are the one precious output. | Keeps the index's format free to change. |
| D10 | Everything lives under `~/.claude/memory-archive/`, outside git (the repo's ignore-everything allowlist already excludes it) | Client chat content must never reach the pushed `~/.claude` repo. |
| D11 | The compressor runs from Windows Task Scheduler daily at 12:30, with "run as soon as possible after a missed start". It does real work only when a month has become due, and it is idempotent, so a missed run is caught up by the next. | Not tied to Claude sessions starting or to `/recall` being used. A SessionStart hook would race between 3+ concurrent sessions. Daily rather than monthly because PowerShell 5.1's `New-ScheduledTaskTrigger` has no monthly trigger, and a daily no-op costs nothing. |
| D12 | Every silent failure mode prints a `WARNING:` line on the next `/recall`: the compressor not having run for 7 days or its last run failing (`compress.log`), a zip failing its rolling re-verification, a raw transcript vanishing without reaching a zip (`index/missing.log`, which is how a future Claude Code release ignoring `cleanupPeriodDays` would show up), and a 50+ record transcript extracting to nothing (the transcript format changed). The compressor also skips a month whole when free disk is below its uncompressed size plus 1 GB. | The rate-it panel's confirmed flaws, 2026-10-08: each of these would otherwise degrade without a crash and be found only when a search came back empty. |

## Phase 1 (built 2026-10-08)

`skills/recall/` holds the skill, `recall.py` and its self-test `test_recall.py` (run by
`ci/run_all.py`). First full build on 2026-10-08: 583 sessions in 33 s, a 14 MB index; an
incremental update takes about 2 s. A rebuild at 10x the sessions should scale roughly linearly
(UNVERIFIED past today's size; re-measure with `recall.py update` after deleting `index/`).

- `recall.py update` brings the index up to date. One file per session in
  `memory-archive/index/sessions/<sessionId>.jsonl`: a header row (session id, repo, cwd, client
  or personal, title, first and last timestamp, human-turn timestamps) then one row per extracted
  turn. A source is re-extracted only when its size or mtime changed (`index/state.json`).
  Reads raw `.jsonl` files and members of the monthly zips alike.
- `recall.py search <terms...> [--repo] [--since] [--until] [--limit]` updates first, then prints
  hits grouped by session, newest first, each with its citation and a short snippet.
- `recall.py show <sessionId> [--grep]` prints one session's extracted conversation.
- `recall.py activity --since --until [--repo]` prints per-session human-turn timestamps. This is
  the evidence todo 95 originally wanted for Clockify: raw timestamps, never a precomputed
  duration, so the idle threshold stays a read-time choice. Overlapping concurrent sessions are
  expected and the consumer merges them.
- `recall.py compress [--dry-run]` is D2. Each file is added to the zip, read back and compared
  (size and CRC) before the original is deleted, and a file whose mtime moved during the run is
  left alone. It only touches `<slug>/<sessionId>.jsonl` and `<slug>/<sessionId>/**`, never
  `memory/` or anything else under `projects/`.
- `register-archive-task.ps1` registers D11's scheduled task.
- Each compress run appends one line to `compress.log` and re-verifies the archived zip checked
  longest ago (`verify-state.json`); see D12 for what surfaces where.

## Review (rate-it panel, 2026-10-08)

Three sonnet raters (scale, hidden cost, cheaper alternative) scored the design before phase 1
was built: 6, 6 and 4; the main agent 7; median 6/10, verdict REVISE. Every flaw went through
an independent refute pass. Confirmed and fixed in phase 1: silent extractor breakage on a format
change, invisible scheduled-task failure, no disk-space check, no re-verification of old zips
(all D12). Confirmed and answered below in phase 2: no size budget for the always-loaded memory
core, no latency budget for the trigger hook, no concurrency story for the lessons sweep.

Refuted, so do not re-raise them without new evidence:

- "Shard `index/sessions/` now": 5,800 files enumerate in about 0.015 s on this NTFS SSD
  (measured by a verifier), so the flat directory is not the bottleneck.
- "The compressor is unnecessary, keep raw forever": Joe chose compression explicitly, the
  original is deleted only after a fresh read-back matches size and CRC, and the write volume
  (about 2.7 GB a month) is negligible SSD wear.
- "`state.json` size/mtime diffing is excess, existence is enough": live sessions keep appending,
  so existence alone would freeze a session at its first extraction.
- "`cleanupPeriodDays` is an undocumented knob": the binary's own validation text tells users to
  set a large number for long retention. Drift is still detected (D12).

## Phase 2 and later (designed, filed as todos)

Filed 2026-10-08 in `.claude/todos/`: 1152 digests and decision ledger, 1153 trigger-keyed
memory, 1154 cross-project lessons, 1155 core/rest index split, 1156 freshness and supersession.
Only 1152 depends on phase 1; 1154 works best after 1153.

**Digests and the decision ledger.** The first time a session reads an old chat through
`recall.py show`, it writes a short digest of it: what was done, decisions taken, and options
rejected with the reason. No extra model call: the session already read the chat. `/close`
writes the same digest for its own session, since it already reads its own transcript.
`recall.py decisions <topic>` searches only the decisions sections. `/brainstorm` step 1 runs it
next to its existing todo grep, so a rejected option surfaces before it gets re-proposed.

**Trigger-keyed memory.** A memory file may carry `triggers:` in frontmatter: path globs, skill
names, a repo. A PreToolUse hook on Edit, Write, Read, Skill and Agent matches the tool input and
injects the matching memory once per session as additional context. On an Agent dispatch the
injected text tells the orchestrator to pass it into the dispatch prompt (todo 53's fix, made
mechanical). A memory with `once: true` is prospective memory, "next time X is touched, do Y",
and gets retired after it fires. Latency budget: the hook must not read memory files per call.
It reads one precompiled trigger table (rebuilt only when a memory file's mtime is newer than the
table), and stays under 50 ms per tool call measured against today's 1,637-file corpus before it
is wired.

**Cross-project lessons.** A periodic consolidation sweep reads feedback memories across every
project, finds the same lesson in two or more, and proposes promoting it to a global lessons
store. That store cannot be `CLAUDE.md` (0 headroom), so it is a tracked folder whose small,
byte-capped index a SessionStart hook injects, and whose individual lessons mostly load through
triggers. The sweep is an explicit command run by one session, never a hook, so concurrent
sessions never race on it; it proposes promotions and applies them through the same
ADD/UPDATE/DELETE/NONE gate as any memory write, re-reading each file right before editing it.

**Retrieval quality.** Each `MEMORY.md` splits into an always-loaded core (rules that apply every
turn) and the rest, which stays on disk and is found through `recall.py memory <terms>` across
all projects' memory files, or through triggers. The core is capped at 8 KB, a third of the
24.4 KB cut, and an entry earns a core slot only by passing `skills/cleanup-memory/SKILL.md`
Step 1.5's axiom test (Claude defaults wrong without it, the failure is silent, it applies every
session). Anything else, or anything that stopped passing, is demoted to the rest by
`/cleanup-memory`. That keeps the overflow from growing back one level up.

**Freshness and supersession.** Memory frontmatter gains `verified: <date>` and
`superseded_by: <name>`. A replaced fact is kept, marked superseded, and dropped from indexes and
triggers rather than deleted, so its history survives. `/cleanup-memory` flags facts about tool
versions or reproductions whose `verified` date is old.
