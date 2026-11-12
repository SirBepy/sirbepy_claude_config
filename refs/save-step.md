# Save step

> Save what this chat learned at the moment the work reaches a checkpoint. Nothing lasting may
> depend on a chat being closed: a Conductor main chat is compacted in place and never closes, a
> sub ends with `finish_subchat`, and any chat can be closed from the app with no model turn.

Read once per session, at the first checkpoint that calls for it.

## When it runs

- After every `/commit` (the commit skill's last step).
- Before a Conductor sub calls `finish_subchat`. Its `learned` rows are the receipt.
- In `/respawn` and `/handoff`, before the handoff is written.
- Before an ordinary chat ends itself (`CLAUDE.md`, Process Hygiene).
- In a Conductor main chat: at the end of each piece of work, and whenever the app asks for it
  before a compaction.

Writing as things happen comes first: a memory at the moment Joe confirms a fact, a todo at the
moment work is deferred. The save step is the net under those two rules. It catches what live
capture missed and never re-extracts what live capture already got.

## Scope

Everything since this chat's last save step, or since the chat started. A chat with nothing new
since then skips the step silently: no output, no subagent, no file.

If the chat was compacted since the last save step, the early material is a summary, and that is
where corrections go missing. Ground on the transcript first, per `refs/transcript-grounding.md`
(Grep the dev's own turns, never Read the file whole).

## Steps

1. **Memory.** Candidates: each place Joe pushed back, rejected or rewrote something, and each
   non-obvious fact confirmed against the live system. Route every candidate through
   `refs/memory-rubric.md` (ADD / UPDATE / DELETE / NONE) and write it to the store `CLAUDE.md`'s
   Global Knowledge Vault section names. A candidate already written live in this chat is NONE.
   NONE is the normal outcome; never write a memory to look productive.
2. **Todos.** File each item through `skills/create-todo/SKILL.md` (duplicate guard, id
   reservation, cross-repo filing), one file per item, per `refs/ai-todos-format.md`:
   - Work Joe asked for that is not done and will not be finished in this chat: `task`, origin
     `dev`.
   - An offer Claude made that was not taken up, was not declined, and that a cold session could
     execute from the file alone: `task`, origin `ai`.
   - A manual step done twice or more that a skill should own, or an active skill's rule that got
     broken: `skill-improvement`, origin `ai`, with the skill file named in Approach. This records
     an enforcement gap, never a "be more careful" note.

   Before filing a `task` todo, call `list_peers` once. With a live peer whose name or messages
   point at the same ticket, file or feature, ask it with `post_message` and put the answer (or
   "asked, no reply yet") in the todo's Notes. Zero peers is a weak signal, so never word the todo
   as "confirmed unstarted".
3. **Decisions.** If a decision was made or an option was rejected since the last save step, add
   it to this session's digest, which feeds `recall.py decisions`:

   ```
   python ~/.claude/skills/recall/recall.py digest-save <sessionId> --merge
   ```

   Pipe `## Done`, `## Decided`, `## Rejected` (the option plus the reason it lost) and `## Open`
   on stdin, with `none` under an empty section. `--merge` adds the new rows to an existing
   digest instead of refusing. `<sessionId>` is `$CLAUDE_CODE_SESSION_ID`; when that is unset,
   resolve it with `refs/transcript-grounding.md` step 1. Skip this step in a Conductor sub (its
   `decided` and `ruled_out` rows become its digest) and in a Conductor main chat (the app writes
   that digest from the decisions log).
4. **Report.** A clean save prints nothing and sends nothing. Send one line only for a real miss:
   a write that failed. A sub lists what it saved in `finish_subchat`'s `learned` rows, each row
   naming where the fact went (a memory file, a todo id), or `["nothing"]`.

## Boundaries

- The save step is not a code review. Review runs at the push gate (`skills/commit/push.md`) and,
  for a Conductor sub, in its fresh reviewer before `finish_subchat`.
- It never blocks or delays a commit: it runs after the commit landed.
- Todo files it writes in a repo that tracks its backlog are committed as their own commit under
  the auto-commit policy. That commit carries nothing new to learn from, so its own save step is
  a skip.
- It never ends a chat and never calls `close_session`.
