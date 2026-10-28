<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=3, content-hash=fb136fdb -->
<!-- duplicate-checked -->
# permissions has an allow list, no Read denylist, and no way to grant a skill family

**Type:** task
**Origin:** ai

## Goal

Add a curated `permissions.deny` list for reads that should never happen, and evaluate namespacing
skills so a whole family can be granted in one entry instead of one entry per skill.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). Two related
permissions gaps, grouped because both are edits to the same config block.

**1. No `Read()` denylist.** Current `settings.json` permissions are allow-only. Nothing declares
files that should never be read, so a credential file or a service-account key is readable by default
and only a hook (which fails open on a pattern miss) stands in the way.

Reference: `repos/serpro69_claude-toolbox/.claude/settings.json` carries a curated `Read()` denylist:
`.env`, `service-account-key.json`, `*.csv`, `*.log`, `*.pyc`, lockfiles, `.git/`, `.idea/`, `.vscode/`,
`.next/`, `.terraform/`, `.ansible/`, `build/`, `dist/`, `out/`, `node_modules/`, `venv/`,
`__pycache__/`. `repos/IvanKuzyshyn_dotfiles` has a similar dotfiles-and-secrets deny set.
`repos/TheoBrigitte_claude-config` uses broad substring `ask` rules instead, like
`"Bash(* *secret*)"` and `"Read(**/*credentials*)"`, which catch any command or path containing the
word.

Note the two purposes mixed in that list, which need separating rather than copying wholesale:
security (`.env`, keys, credentials) and **noise reduction** (`node_modules`, `build`, `*.log`,
lockfiles). The second is arguably the bigger daily win, since it stops a search or a read wandering
into generated output, but it is not a security control and should not be justified as one.

**2. No skill namespacing.** All 83 skills are bare-named, so a permission entry can only name one
skill at a time. `repos/serpro69_claude-toolbox` invokes its plugin skills as `/kk:design`,
`/kk:implement`, `/kk:review-code` and permission-scopes the whole set as one `Skill(kk:*)` entry.

Be honest about the cost here: renaming skills is a breaking change across a large surface. Every
reference in CLAUDE.md, `refs/`, other skills, hooks that match skill names, and Joe's own muscle
memory would need updating, and memory records that flagged skills are excluded from the listing
entirely, so the naming interacts with discoverability. The benefit is one permission entry per family.
That trade looks bad at 83 skills unless permission prompts for skills are actually a live annoyance,
which should be checked before proposing it.

Related existing surface: `/fewer-permission-prompts` exists as a skill and scans transcripts to
propose an allowlist. Todo 426 covers the `PermissionRequest` hook, which is a third mechanism aimed at
the same problem. **Three overlapping mechanisms is the real risk here** - read both before adding a
fourth.

## Approach

1. Read the current `permissions` block in `settings.json` and `settings.local.json` in full. Note
   that `settings.local.json` is untracked (todo 415), so some permission state may not be versioned.
2. Read `/fewer-permission-prompts` and todo 426 first, and state how this todo divides
   responsibility with them. If it does not divide cleanly, fold this into one of them instead of
   shipping a third mechanism.
3. Build the deny list in two clearly labelled groups, not one: **security denies** (`.env`, `*.pem`,
   `*.key`, `id_rsa`, `credentials.json`, service-account keys) and **noise denies**
   (`node_modules/`, `build/`, `dist/`, `__pycache__/`, `*.log`, lockfiles). Keeping them separate
   matters because the noise group will need tuning and the security group must not be loosened while
   tuning it.
4. Check for collisions with real work before applying. Reading a lockfile is legitimate during a
   dependency audit, and `.git/` reads happen during commit work. A deny that blocks a real workflow
   gets removed wholesale, taking the security entries with it. Prefer `ask` over `deny` for anything
   with a legitimate use.
5. For namespacing, do the cheap check first: is a skill permission prompt actually a recurring
   annoyance? If not, recommend against it and close that half. Do not rename 83 skills to solve a
   hypothetical.
6. Verify by attempting a denied read and confirming a clear refusal, then running a normal session
   and confirming nothing legitimate broke.

## Acceptance

- Security denies and noise denies are separate, labelled groups.
- Anything with a legitimate use is `ask`, not `deny`, and the reasoning is recorded.
- A denied read is proven to fail; a normal session is proven unaffected.
- An explicit division of responsibility against `/fewer-permission-prompts` and todo 426, or a
  decision to fold into one of them.
- A stated recommendation on namespacing, including "not worth it" if the prompt-annoyance check does
  not support it.

## Notes

The noise-reduction half is the part likely to pay off daily. Do not let it ride on the security
framing, and do not let a tuning change to it quietly loosen the security entries.

Namespacing is probably a no. 83 renames against one permission-entry saving is a bad trade unless
prompts are a real recurring cost.
- Completed in wave 2, commit b48a4b1: settings.json and settings.local.json now carry labelled security-deny and noise-deny groups alongside the existing allow list.
