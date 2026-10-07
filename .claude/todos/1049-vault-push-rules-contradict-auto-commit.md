<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=6, reconfirm-count=3, content-hash=61745638 -->
<!-- duplicate-checked: 229 is the /obsidian skill's arg parsing and 467 is read-once enforcement; this is a contradiction between three push rules -->
# Three rules disagree on whether Claude may push the Obsidian vault

**Type:** skill-improvement
**Origin:** ai

## Goal

One consistent answer to "may Claude push the vault without being asked", stated the same way in every place that governs it.

## Context

Hit on 2026-09-30 during a /close run from a session rooted in `C:\Users\tecno\Documents\ObsidianVault`. After committing vault notes, three sources gave different answers:

- The vault's own `CLAUDE.md` (Git Workflow): "Every commit is always followed immediately by a push. Never leave commits unpushed."
- `refs/global-knowledge-vault.md` ("Writing and backup"): Claude never runs git in the vault, EXCEPT the fallback when obsidian-git is dead, where "a manual backup commit+push is allowed".
- `snippets/auto-commit.md` line 3: "a push always needs the dev's explicit ask in the current session, regardless of any 'per project policy' wording elsewhere."

`hooks/push-read-gate.py` forced a read of auto-commit.md before the push, which is the only reason the conflict surfaced. Claude followed auto-commit.md and left 3 vault commits unpushed. The obsidian-git plugin has been dead since 2026-08-25, so the fallback clause is the one that actually applies day to day.

## Approach

Decide with Joe which rule wins for the vault specifically. If the vault is meant to be an exception, add an explicit carve-out to auto-commit.md ("except the Obsidian vault, per refs/global-knowledge-vault.md") so the "regardless of per project policy" line stops overriding it. If not, drop the push wording from the vault CLAUDE.md and the fallback clause. Either way, also fix the vault CLAUDE.md's `git add .` instruction, which /commit forbids.

## Acceptance

The three documents give the same answer, and a vault commit made from a vault session either pushes or doesn't without any rule contradicting it.

## Notes

- Phase 0 answer (Joe): vault exception, Claude pushes vault commits straight away; auto-commit.md gets a named carve-out pointing at refs/global-knowledge-vault.md. (2026-10-07, /loop-todos Phase 0)
