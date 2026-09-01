<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=3, content-hash=00c04501 -->
<!-- duplicate-checked -->
# Cloning a third-party .claude tree silently makes its skills model-invocable

**Type:** task
**Origin:** ai

## Goal

Make "read someone else's agent config" a safe operation, with a documented procedure, so a clone
can never again load foreign skills into a live session without anyone noticing.

## Context

Happened for real on 2026-08-19 during the open-source `.claude` harvest (see
`refs/harvest-2026-08-20-oss-claude-repos.md`).

32 repos were shallow-cloned into `C:\tmp\claude-harvest\repos`. Many contain their own
`.claude/skills/` trees. Because the clone target sat inside a directory tree Claude Code scans for
project skills, **100+ third-party skills became model-invocable in the live session.** The
available-skills listing visibly filled with the corpus's own skills (citypaul's `tdd`,
`hexagonal-architecture`, `panel-review`, alirezarezvani's business-persona set, and more).

Two independent subagents noticed the listing changing under them mid-task and reported it as
suspected "cross-session bleed", which is the wrong diagnosis: nothing bled between sessions, the
clone location did it.

Nothing was executed and no foreign skill was invoked, but the exposure was real. The corpus
contains:
- `ChrisWiles_claude-code-showcase/.claude/hooks/skill-eval.js`, which generates text instructing
  the model "DO NOT skip this step. Invoke relevant skills NOW"
- `judigot_ai/scripts/ralph/ralph.sh`, which runs `amp --dangerously-allow-all` in an unattended loop

Mitigation applied mid-run, and it worked: all 269 `.claude/`, `.claude-plugin/` and `.agents/`
directories in the corpus were renamed to `dot-claude/`, `dot-claude-plugin/`, `dot-agents/`. That
stops discovery while leaving every file readable. That rename is the seed of the procedure this
todo should codify, not a one-off cleanup.

The general lesson, which is the reason this is worth a rule and not just a note: **reading another
agent's config is not a read-only operation.** The existing package-safety rule in CLAUDE.md covers
npm/cargo dependencies but says nothing about skills, hooks, agents or plugin manifests, which are
strictly more dangerous because they are instructions rather than code that has to be called.

## Approach

1. Verify the mechanism before writing the rule rather than assuming it. Determine empirically what
   Claude Code actually scans: cwd only, cwd plus ancestors, or every configured working directory.
   A throwaway dir with one dummy skill under `.claude/skills/` plus a `/context` or skill-listing
   check answers this. Record the finding with the evidence, since the rule's scope depends on it.
2. Write the rule. It belongs in global `CLAUDE.md` near the Packages section, since it is the same
   supply-chain concern one level up. Keep it short; the procedure goes in a ref, not in CLAUDE.md.
   The rule states: never clone or unpack a third-party agent-config tree into a scanned directory;
   neutralize it first.
3. ~~Write the procedure as a ref (or fold it into the new skill from todo 418, if that lands first,
   to avoid two homes for one idea).~~ **DONE 2026-08-20 by todo 418.** The procedure lives in
   `skills/supply-chain-audit/SKILL.md`, section "Reading an untrusted tree safely", which is the
   fold-in this step sanctioned. It carries the outside-a-scanned-tree option, the `dot-*` rename,
   the deepest-first ordering with the 222-directory miss, and the re-check-the-listing step. Do not
   write a second copy as a ref. What is left of this todo is steps 1, 2 and 4.
4. Consider mechanical enforcement, and be honest about whether it is reachable. A `PreToolUse` hook
   on `Bash` matching `git clone` could warn when the destination is inside a scanned tree. Do NOT
   build this until step 1 establishes what "scanned tree" means concretely, or the guard will be
   wrong in one direction or the other.

## Acceptance

- The scanning behavior is established by an actual experiment, with the result written down, not
  inferred.
- A rule exists in `CLAUDE.md` and a concrete procedure exists in a ref or skill.
- The procedure names the deepest-first rename ordering and why (the 222-directory miss).
- If a hook is built, it has a test proving it fires on an unsafe clone destination and stays quiet
  on a safe one.

## Notes

Do not over-rotate into "never read other people's configs". The harvest was worth doing and found
real gaps. The fix is a safe procedure, not avoidance.

Counterweight worth keeping in the record: across all 32 repos, **zero files attempted to instruct
the reading agent.** The one instruction-shaped artifact was `skill-eval.js`'s own generated output,
aimed at whoever runs that hook. The risk here was structural, not adversarial, and the rule should
say so rather than implying the ecosystem is hostile.
