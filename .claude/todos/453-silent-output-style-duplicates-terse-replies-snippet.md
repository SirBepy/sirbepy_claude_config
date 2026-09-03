<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=5, reconfirm-count=3, content-hash=b65f9491 -->
<!-- duplicate-checked -->
# Silent output style and terse-replies.md now say the same thing in two places

**Type:** task
**Origin:** ai

## Goal

Decide which file owns Joe's chat-tone rules, and make that the only place they live, so the two
copies cannot drift apart.

## Context

Filed 2026-08-20, the session that wrote `output-styles/silent.md` (commit `a233b36`).

`output-styles/silent.md` and `snippets/terse-replies.md` now carry substantially the same rules:
default to a few lines, lead with the answer, drop filler and pleasantries, fragments are fine,
capitalize regardless, exempt security warnings and destructive-action confirmations, and the
"normal" escape word. Global `CLAUDE.md`'s Communication section still imports the snippet
("read once per session"), so both reach the model every session by different routes.

They are not identical, and the differences matter:

- `silent.md` adds the rule the snippet cannot express: write nothing outside tool calls, because
  Conductor never renders assistant text to Joe. It also names `send_message` explicitly.
- `terse-replies.md` carries the deliverable-exemption list in more detail (recap and
  reconciliation output, drafts for colleagues, task-status narration mid-task).
- `silent.md` folds in two rules that live elsewhere in `CLAUDE.md`: the em-dash ban and writing
  "Claude" as the subject. Those are now stated in two places as well.

The asymmetry that decides this: an output style is the system prompt, while `CLAUDE.md` and its
imports are appended context. Same words, stronger position. But a style only applies to the main
agent and only after a restart or `/clear`, whereas `CLAUDE.md` also reaches subagents.

This was raised with Joe during the 2026-08-20 session and explicitly deferred, not answered.
The question card was withdrawn as premature while he was still deciding whether to use a custom
style at all. It is now a real duplication rather than a hypothetical one.

## Approach

1. Read `snippets/terse-replies.md`, `output-styles/silent.md`, and the Communication section of
   `C:\Users\tecno\.claude-personal\CLAUDE.md` before proposing anything.
2. Read `435-prose-enforcement-is-one-hardcoded-character-ban.md` first. It states directly: "Do
   not fold this into `terse-replies.md`. That governs chat tone with Joe, which is a different
   surface with different rules." That constrains any merge, and 435 may itself be executed before
   this one, which would move the boundary again. Check its state before starting.
3. Ask Joe, do not pick silently. This is his voice and his global config, and the options carry
   real tradeoffs rather than one obvious winner:
   - Style owns chat tone. Delete the snippet and its `CLAUDE.md` import line. One home, stronger
     position, smaller `CLAUDE.md`. Cost: subagents lose the rules, and nothing applies before a
     restart.
   - Snippet keeps only what the style cannot cover, mainly the full deliverable-exemption list
     and the subagent-facing scope. Cost: two files to keep aligned, but each with a clear job.
   - Keep both as-is. Cost: drift, and this todo gets refiled later.
4. Whichever wins, leave a pointer in the loser so a future session finds the authority instead of
   editing the stale copy.

## Acceptance

- Exactly one file is the stated authority for chat-tone rules, and it says so in its own text.
- No rule silently disappears in the merge. Diff the two files rule by rule and account for every
  line that is dropped, especially the deliverable exemptions, which are what stop chat terseness
  leaking into commit messages, PR bodies, and drafts Joe sends as his own words.
- The em-dash ban still reaches the model by at least one route, and `hooks/em-dash-guard.py`
  still fires. Its test still passes.
- If `CLAUDE.md`'s import line is removed, confirm nothing else in the tree still references
  `snippets/terse-replies.md`.

## Notes

Do not execute this from inside a project session. It edits global `~/.claude` config, which
`CLAUDE.md` restricts to sessions Joe explicitly points at that work.

The failure mode is a tidy-looking merge that quietly drops the deliverable exemptions, which
would compress commit messages and outbound drafts. That is the one part of `terse-replies.md`
whose absence would not be obvious until it had already caused damage.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [TOOLING] `output-styles/silent.md` and `snippets/terse-replies.md` both carry near-identical chat-tone rules with no authority marker in either. Which one owns them going forward? Options: the style owns everything, delete the snippet and its import / the style is primary and the snippet keeps only what a style cannot express (deliverable exemptions, subagent scope) / keep both duplicated. Recommended: style primary with a reduced snippet, because a style does not reach subagents and dropping the snippet entirely would lose that coverage.
