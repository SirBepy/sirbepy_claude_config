<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=9, reconfirm-count=1, content-hash=861465eb -->
# /commit needs a secret-scan prefilter, not just the comment-noise one

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a credential/secret scan to `/commit`'s pre-commit checks, in the same slot and with the same
"just fix it, don't ask" posture as the existing comment-noise prefilter, so a hardcoded password
cannot reach a commit unnoticed.

## Context

**Real incident, 2026-08-12, Fibo `frontend2`.** A `/mega-todos` run committed
`frontend2/e2e/auth.setup.ts` containing a live admin credential:

```
const EMAIL = 'admin@fibo.hr';
const PASSWORD = '<a real, working develop-stack password>';
```

Chain of events:

1. The orchestrator dispatched an e2e builder agent and put the real credentials **in the dispatch
   prompt**, so the agent could log in. It never told the agent to source them from the environment.
2. The agent, reasonably, hardcoded what it was given.
3. `/commit` ran its comment-noise prefilter, which came back clean, and the commit landed. **Nothing
   in the skill looks for secrets.**
4. It was caught only later, by a security-lens reviewer in an unrelated multi-agent code review, and
   required a `git filter-branch` rewrite plus a reflog expire and gc to scrub. That was only cheap
   because the branch had never been pushed. On a pushed branch it is unrecoverable.

`skills/commit/SKILL.md` step 5a already runs an awk prefilter over exactly the paths about to be
committed, including untracked ones. The mechanism, the timing and the "trim it now, don't ask"
convention all exist. This is the same shape of check against a different pattern, so it is a small
addition to a proven step rather than new machinery.

## Approach

1. Add a step 5b to `skills/commit/SKILL.md`, right after the comment-noise prefilter, reusing its
   exact "diff HEAD plus untracked files" plumbing so new files are covered - an untracked file is
   precisely how this incident happened.
2. Grep the added lines for high-signal assignment patterns rather than trying to be a full secret
   scanner. Something like a case-insensitive `(password|passwd|secret|token|api[_-]?key|bearer)`
   immediately followed by `=`/`:` and a quoted literal of non-trivial length. Aim for near-zero
   false positives: this fires on every commit, and a noisy check gets ignored.
3. Deliberately exclude the obvious benign shapes so it stays quiet: `process.env.X`,
   `import.meta.env.X`, an empty string, an obvious placeholder (`xxx`, `<...>`, `changeme`,
   `your-password-here`), and `.env.example` / `*.md` files.
4. On a hit: **STOP the commit** and surface it. This is the one place the comment-noise convention
   should NOT be copied - do not auto-fix. A secret needs a human decision about whether the value
   is real and whether it has already leaked elsewhere.
5. Mirror it into `/create-pr`'s equivalent range-mode check, the same way `comment-noise.md`
   documents both variants in one place.
6. Consider whether `refs/delegation-doctrine.md` should also carry a line in its builder-prompt
   requirements: never put a credential in a dispatch prompt, tell the agent to read named env vars
   and fail loudly if unset. That is the upstream cause; the commit prefilter is the safety net.

## Acceptance

- A test commit whose diff adds `const PASSWORD = 'hunter2hunter2';` is refused, and the reason is
  printed with the file and line.
- A commit adding `const PASSWORD = process.env.FIBO_LOGIN_PASSWORD;` passes without comment.
- A commit adding `PASSWORD=your-password-here` to a `.env.example` passes without comment.
- The check adds no perceptible time to a normal commit and produces no output when clean, matching
  how the comment-noise prefilter already behaves.

## Notes

- The comment-noise prefilter has a documented history of catching real problems on nearly every
  multi-agent run, which is the argument that this slot is the right one: it is the last point where
  every path about to enter history is enumerated and inspectable.
- Scope check: this is a change to the GLOBAL `~/.claude` tree, filed here rather than in the Fibo
  repo per CLAUDE.md's rule that findings about the global tree belong in this backlog. It was
  surfaced from a Fibo session but is not Fibo-specific.
