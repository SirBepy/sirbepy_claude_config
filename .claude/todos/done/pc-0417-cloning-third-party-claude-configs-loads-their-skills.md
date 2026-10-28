<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=5, reconfirm-count=4, content-hash=00c04501 -->
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
- Advanced in /mega-todos wave 2, commit `7f108ee`, NOT finished. The scan-behaviour experiment ran with nested `claude -p` sessions from throwaway cwds and its result is recorded here so it is not re-derived: a skill under **cwd's own** `.claude/skills` is discovered; a skill under an **ancestor** directory's `.claude/skills` is ALSO discovered (verified 1 and 2 levels up); a skill under a **sibling** directory, or nested several levels **below** cwd with no `.claude` of cwd's own, is NOT discovered. So the scan walks cwd plus its ancestors. A short rule went into CLAUDE.md's Packages section. Remaining: decide the hook (step 4). Given the finding, a PreToolUse guard matching `git clone` / `Expand-Archive` / `tar -x` destinations against cwd-or-ancestor is buildable - either build it with a test proving it fires on an unsafe destination and stays quiet on a safe one, or record here that it was decided against and why.

**Step 4 DECLINED 2026-09-10, do not build.** Measured against the same 695-transcript,
32766-Bash-call corpus used to close todo 948: `git clone` appears exactly 3 times, ever, across
every project this machine has run. Two of the three ARE the 2026-08-19 harvest itself (the incident
this todo exists to prevent, already mitigated and now covered by the CLAUDE.md rule plus the
supply-chain-audit procedure); the third is `git clone --local` of the current repo into
`/c/tmp/hubbub-ci` for a CI dry-run - entirely benign, and its destination is NOT within cwd's
ancestor chain, so a naive "destination outside cwd/ancestor" trigger would have fired on it too
(a false positive on 1 of the only 3 clones ever run), and more importantly would be testing the
wrong variable.

The scan behaviour established above is the reason why: cwd's own `.claude/skills` plus ancestors
are scanned; siblings and deep descendants are not. A `git clone` destination is essentially never
itself in the scanned zone - a clone always creates a NEW subdirectory, i.e. a descendant, which is
the one case confirmed NOT scanned. The actual exposure step in the harvest incident was the session
LATER `cd`-ing into the cloned repo to read it, at which point that repo's own `.claude/skills`
becomes "cwd's own" and gets scanned - the same drift mechanism todo 948 just declined to
hard-block, for the same reason: it is the dominant, necessary way this environment reads any
freshly-fetched content, not a distinguishing signal. A guard on the `git clone` command itself also
cannot inspect the clone's contents (PreToolUse fires before the clone runs, so `.claude/skills`
does not exist yet to check), so at best it could only fire a blanket reminder on a command that ran
3 times in this machine's entire transcript history - negligible marginal safety for another hook to
maintain.

**Conclusion: the CLAUDE.md rule (Packages section) plus `skills/supply-chain-audit/SKILL.md`'s
"Reading an untrusted tree safely" procedure are the right layer, same reasoning as todo 948's
consequence guards. Not building a `git clone` PreToolUse guard. This closes the "Consider
mechanical enforcement" question in step 4; do not re-open without a new incident these two didn't
cover.**
- CLOSED 2026-09-10 via /loop-todos cycle 4. Steps 1 to 3 were already shipped and were re-verified present this session: the CLAUDE.md Packages rule against cloning a third-party .claude tree into a scanned directory, and skills/supply-chain-audit/SKILL.md Reading an untrusted tree safely section. Step 4, the optional mechanical git clone guard, is DECLINED on measurement. Across every project transcript on this machine, git clone appears exactly THREE times ever. Two are the 2026-08-19 harvest that prompted this todo, already mitigated; the third is a benign --local clone of the current repo into a CI scratch path whose destination sits outside the cwd ancestor chain, so a naive location-based trigger would have false-positived on one of only three real occurrences. The deeper reason is structural: the established scan behaviour covers cwd and its ANCESTORS, not descendants, so a clone destination is essentially never in the scanned zone by itself. The actual exposure step is a later cd into the clone, which is the same mechanism todo 948 declined to hard-block in the same run, and a PreToolUse guard cannot inspect clone contents anyway since it fires before the clone runs. A blanket reminder on a three-in-all-history command is noise.
