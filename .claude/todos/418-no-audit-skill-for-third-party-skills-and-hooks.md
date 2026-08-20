<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# No audit skill exists for third-party skills, hooks, or agent configs

**Type:** task
**Origin:** ai

## Goal

A skill that audits an untrusted `.claude` tree (or any vendored diff) and returns a
FAIL / WARN / PASS verdict per item, so adopting a foreign skill or hook is a checked decision
instead of a read-and-hope.

## Context

CLAUDE.md's Packages section mandates a typosquat plus resolved-tree advisory check before adding
any package. Skills, hooks, agents and plugin manifests get **no such check at all**, despite being
strictly more dangerous: they are instructions, so they do not need to be called to take effect.

Todo 417 covers the loading hazard. This covers the content hazard.

Two working implementations were found in the 2026-08-19 harvest (see
`refs/harvest-2026-08-20-oss-claude-repos.md`):

**1. `vsbuffalo/dotfiles` `supply-chain-audit`** - the better design, and the model to copy. A
prompt-only skill using `context: fork` with tools restricted to Read/Glob/Grep/`git diff`/`git log`,
so the auditor structurally cannot write anything. Invoked on demand. Its rubric:

- **FAIL** - obfuscation, base64, eval of constructed strings; exfiltration via curl or reads of
  `~/.ssh`, `~/.aws`, credential files; persistence via crontab, rc-files, launch agents;
  prompt-injection strings or hidden unicode.
- **WARN** - scope creep unrelated to stated purpose; shell-injection surface; ANY new network
  access even if benign; env probing; new binaries, `.so`, `.dylib` or wasm that cannot be
  source-reviewed.
- **PASS** - bug fixes, in-scope features, docs/tests/CI, metadata version bumps.

Decision rule: any FAIL blocks outright; any WARN requires manual line-level review; "when in doubt,
WARN." Critically, **it audits removed lines too, on the grounds that a removed security check is
itself an attack.** Output is a markdown table per dependency plus line-referenced detail.

**2. `alirezarezvani/claude-skills` `skill-security-auditor`** - a Python static scanner
(`skill_security_auditor.py`) producing PASS/WARN/FAIL, wired into CI
(`.github/workflows/skill-security-audit.yml`) that scans only changed skill directories on PR, plus
a VirusTotal workflow. Weaker rubric, but proves the CI-time shape.

The gap `supply-chain-audit` leaves: it is generic to "vendored diff" and knows nothing about
Claude-specific danger surfaces. Adapting it means adding checks for: a `SKILL.md` whose
`description` is written to trigger on unrelated prompts, `allowed-tools` requesting more than the
stated purpose needs, hooks wired to `PreToolUse` on `Bash`, anything invoking another agent CLI
with a dangerous-permissions flag, and `settings.json` fragments that widen `permissions.allow`.

## Approach

1. Read `repos/vsbuffalo_dotfiles/dot-claude/skills/supply-chain-audit/SKILL.md` in the harvest
   corpus if it still exists, or re-fetch it. Take its rubric and its `context: fork` plus
   tool-restriction structure as the base.
2. Author the skill. Use `context: fork` and an explicit read-only tool list, so it cannot modify
   what it audits. That property is the whole point; do not build an inline version.
3. Extend the rubric with the Claude-specific surfaces listed above. Each addition needs a concrete
   detection method, not a category name.
4. Give it two input modes: a directory (an unadopted third-party tree) and a diff (an update to
   something already vendored). The diff mode inherits the removed-lines check.
5. Decide where it plugs into existing flow, and state the decision in the skill: at minimum it
   should be named by the todo-417 procedure. Whether it also becomes a CI gate is todo 423's call,
   not this one's.
6. Test it against real material with a known answer. The harvest corpus is the obvious fixture:
   `judigot_ai/scripts/ralph/ralph.sh` (runs `amp --dangerously-allow-all` unattended) must not come
   back PASS. If it does, the rubric is not working.

## Acceptance

- The skill exists, uses `context: fork`, and its tool list cannot write.
- Run against `ralph.sh` it returns FAIL or WARN with a line reference, not PASS.
- Run against a benign skill (any of Anthropic's own examples) it returns PASS without noise.
- Both directory mode and diff mode work, and diff mode flags a deliberately removed guard line in
  a test fixture.
- The todo-417 procedure references it by name.

## Notes

Do not build this as a hook. An always-on scanner over every file read would be noise; the value is
an explicit gate at adoption time, which is exactly when a human is deciding anyway.

Do not reimplement `skill_security_auditor.py` in Python first. The prompt-only version is cheaper
to write, easier to extend, and the harvest showed the rubric matters far more than the parser.
