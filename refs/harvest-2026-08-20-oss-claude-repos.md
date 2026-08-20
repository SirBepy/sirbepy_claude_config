# Harvest: what 32 open-source `.claude` repos are doing that this setup is not

Run 2026-08-19/20. Method: 3 discovery scouts, a full baseline inventory of this repo, then a
9-group wide skim across 32 shallow clones. Every repo was covered; nothing was silently dropped.

Working notes and the raw per-group reports live in `C:\tmp\claude-harvest\` (disposable). This file
is the durable conclusion.

**Todos filed from it: 414-444.** 414-416 are defects in this repo found by the baseline pass.
417-430 are the first tier. 431-444 are the second tier, filed on request so nothing depends on being
remembered: declarative hook engine (431), local statusline (432), config layering (433), per-agent
hooks (434), voice profile (435), heal-skill (436), OS sandbox (437), permissions denylist (438),
config-default merge (439), config-protection guard (440), `/supervised-run` enforcement (441),
CLAUDE.md rules batch two (442), `/create-pr` anti-patterns (443), three smaller skill gaps (444).

Several carry an explicit "the honest answer may be no" instruction. That is deliberate: 431, 433,
437 and 444 in particular are evaluations, and closing them with a negative finding is a valid
outcome rather than a failure to deliver.

---

## The one thing that mattered most, and it was an accident

Cloning the corpus into `C:\tmp\claude-harvest\repos` **made 100+ third-party skills
model-invocable in the live session.** The available-skills listing filled with the corpus's own
skills mid-run; two subagents noticed the listing changing under them and misdiagnosed it as
cross-session bleed. Cause: the clone target sat inside a tree Claude Code scans for project skills.

Nothing was executed and no foreign skill was invoked. The exposure was still real: the corpus
contains a hook that emits "DO NOT skip this step. Invoke relevant skills NOW", and a script that
runs `amp --dangerously-allow-all` in an unattended loop.

Fix applied mid-run: all 269 `.claude/`, `.claude-plugin/` and `.agents/` directories in the corpus
renamed to `dot-*`, which stops discovery while leaving contents readable.

Worth stating plainly, because it generalizes past this session: **reading someone else's agent
config is not a read-only operation.** Filed as todo 417.

Reassuring counterweight: across all 32 repos, **zero files attempted to instruct the reading
agent.** The risk here was structural, not adversarial.

---

## Verdicts on the questions that were asked

### "Any skills I don't have that I should get?"

The single biggest gap is a whole category, not a skill: **engineering discipline.** There is no
TDD skill, no refactoring skill, no debugging methodology, no mutation testing, no
characterisation-tests skill. `citypaul/.dotfiles` has 47 skills covering exactly this, built over
360 commits. Top 5 worth taking: `tdd`, `refactoring`, `mutation-testing`, `debugging`,
`characterisation-tests`.

Second biggest: **a skill eval harness.** Anthropic's own `skill-creator` runs eval fixtures, an
independent grader agent, and version-lineage tracking to measure whether a skill edit actually
improved outcomes. `bepy-skill-creator` is a linter, not an evaluator. With 83 skills, there is
currently no way to know if a skill edit helped.

Third: `supply-chain-audit` (vsbuffalo), `prove-it-works` (ooloth), `heal-skill` (justcarlson),
cross-model delegation (ZacheryGlass's `gemini-agent`).

### "Any skills we have that are similar and could be improved?"

- **`/rate-it` and `/iterate-it` have a structural defect, and the corpus names it.**
  `citypaul`'s `panel-review` gives each sub-agent exactly ONE named skill as its review lens, then
  has an independent node adversarially re-verify findings before synthesis, and distinguishes
  `unverifiable` from `refuted` instead of averaging into a score. The current panel returns one
  numeric score with no lens isolation and no adversarial re-check. **That is exactly the shape that
  produces the known "flat score across rounds" failure** (already recorded in memory as
  diminishing returns): nothing forces a fresh independent verification pass, so there is no defense
  against reviewer groupthink. `solatis`'s `decision-critic` adds a second stealable piece: claim-level
  falsification answered **blind to the decision**, plus a STAND / REVISE / ESCALATE rubric.
- **`bepy-skill-creator`** - see eval harness above; also `plugin-builder` scaffolds commands,
  agents, hooks and MCP configs, not just skills, and ships a structural validator.
- **`create-pr`** - `ooloth`'s `write-pr-description` codifies named anti-patterns ("listing every
  file changed", "escaped inline code") and a hard rule that the validation checklist is manual e2e
  only, never citing automated tests since CI already shows those.
- **`mega-todos`** - `ZacheryGlass`'s `parallel-phases` keeps all state in files outside the repo,
  checks explicit hard-exit conditions every invocation, and survives `/clear`.

### "Good things to add to CLAUDE.md"

Ranked by how well they fit rules already here:

1. **The Timeless Present Rule** (`solatis/conventions/temporal.md`) - "Comments must be written from
   the perspective of a reader encountering the code for the first time... the code simply IS." Ships
   a 5-category detection heuristic and before/after tables: `// Added mutex to fix race condition`
   becomes `// Mutex serializes cache access from concurrent requests`. The existing comment rule
   caps length and noise but says nothing about tense or narrative leakage. Cleanest complement in
   the corpus.
2. **Strength-tagged bullets** (ALWAYS / PREFER / NEVER / AVOID), from `astral-sh/uv`'s 25-line
   AGENTS.md. Makes enforcement level part of the syntax instead of prose weight. The current
   CLAUDE.md writes full sentences of similar-sounding weight.
3. **"Document deferred work explicitly"** (`serpro69`) - "A 'we'll fix it later' note that lives
   only in chat is lost the moment the session ends. Explicit partial > silent postpone", with a
   required durable-location list. The todos backlog exists but nothing forces writing it down at
   the moment of deferring.
4. **Mutation-evidence N/A discipline** (`citypaul`) - "for unreachable, configuration, contract,
   integration, or operational changes, record proportionate alternate evidence and N/A instead of
   fabricating RED or structural mutants." An anti-theater rule the testing floor lacks.
5. **A scoped "Ask First" allowlist** (Prisma) naming exactly which changes need confirmation,
   instead of a general front-load rule. Reduces false-positive interruptions.
6. **Numeric ratchets** (`openai/codex`) - "changed lines should not exceed 800 (500 for complex
   logic changes)", "no context item larger than 10K tokens". Concrete beats "keep it small".
7. **Stash-first destructive-command pre-flight** (`judigot`) - `git stash push -u` before any
   `git reset --hard`, recording the HEAD SHA for reflog recovery.
8. **The Evidence Rule** (`biomejs/biome`) - never assert a function or pattern exists without a
   file path and line number, or say the claim is unverified. This already exists here for outbound
   messages; Biome applies it to the agent's claims about its **own codebase**, which is the half
   that is missing.

Counter-finding worth respecting: an unverified community report says a CLAUDE.md that grew 45 to
190 lines saw compliance **drop**, because mechanical rules were mixed into a behavioral-guidance
file. This CLAUDE.md is far past 190 lines. Adding rules is not free, which is why path-scoped rules
(below) matter more than more prose.

### "Anything else I should not gitignore? Anything else the repo should contain?"

The deny-all-then-allowlist `.gitignore` is already the strong pattern. Gaps are additive:

- **`settings.local.json` is versioned nowhere**, yet carries the impeccable design-detector hook
  wiring and extra permission allows. One disk failure from gone, silently. (Todo 415.)
- **No README and no CONTRIBUTING for the config tree itself.** `zircote/.claude` has both: a
  top-level README describing the layout and a documented skill-authoring template plus PR process.
  With 83 skills, 41 hooks, 10 refs and 6 snippets, there is no document explaining the structure.
- **No CI at all.** The corpus's best repos run: per-hook JSON fixture tests on an ubuntu+macos
  matrix (`poshan0126`), skill frontmatter validation (`citypaul`), a **hard 1200-token budget on
  always-loaded instructions that fails the build when exceeded** (`poshan0126`), and PR-triggered
  security scanning of changed skill dirs (`alirezarezvani`). There are 13 hook self-tests here and
  nothing runs them automatically.
- **No schema validation** over skill frontmatter or any config file. `citypaul`'s
  `test/skills-frontmatter.sh` guards a **real bug**: an unquoted `": "` or `" #"` inside a `name:`
  or `description:` silently drops a skill from installation. It cost them a skill once.
- **No skills index.** `hesreallyhim/awesome-claude-code` uses CSV-as-source-of-truth with CI
  regenerating the README, which is a working template for a self-auditing index.

### "Tips and tricks I'm not using"

**Config surfaces sitting unused:**

| surface | what it does | why it matters here |
|---|---|---|
| Path-scoped `.claude/rules/*.md` with `paths:` frontmatter | rules auto-load only when Claude touches matching globs, zero token cost otherwise | everything in CLAUDE.md, refs and snippets is always-loaded or hand-imported. This is the native answer to CLAUDE.md bloat |
| `sandbox.*` settings namespace | OS-level bash sandboxing: `filesystem.allowWrite`/`denyWrite`/`denyRead`, `network.allowedDomains`/`strictAllowlist`, `credentials.files[].mode: "mask"` | moves secret and file-write risk to OS enforcement instead of regex PreToolUse guards alone |
| `permissions.deny` for `Read()` | curated denylist (`.env`, service-account keys, lockfiles, `node_modules`, `.terraform`) | current settings has an allow list only |
| Per-agent `hooks:` and `permissionMode:` in subagent frontmatter | a hook that fires only while that subagent is active | all 41 hooks are global |
| `output-styles/` | global communication-style override, a first-class config surface | not used at all. Note: `terse-replies.md` plus the em-dash Stop hook already enforce this content **harder** than an output-style would, so this is a mechanism to know about, not necessarily adopt |
| `lspServers` | native LSP wiring | unused |
| Skill namespacing (`/kk:design`) | enables one wildcard permission grant per skill family (`Skill(kk:*)`) | all skills are bare-named, so family-level grants are impossible |

**Hook events never wired** (6 of ~30 are in use). Highest value first:

- `PreCompact` - back up the transcript before compaction. Cheap insurance that does not exist.
- `PermissionRequest` - fires at the permission dialog, **before** PreToolUse guards run; can
  auto-allow whitelisted read-only ops. Directly serves the fewer-prompts goal.
- `PostToolUse` (generic) - the only current use is the impeccable detector. A linter-after-Edit hook
  is a real gap.
- `PostToolUseFailure`, `Setup`, `SubagentStop`, `SubagentStart` - lower value.

**Hook JSON control fields never used** (all 41 hooks use exit codes and prints only):

- `hookSpecificOutput.additionalContext` - inject context without a print convention.
- `decision.behavior` plus `updatedInput` - **rewrite tool args before approval**, not just allow/deny.
- PostToolUse `"decision": "block"` - re-prompt with a reason *after* a tool ran, so results get
  validated rather than merely prevented.
- Stop `"decision": "block"` plus `reason` - force continuation ("tests failing, keep going").
- Global `"continue": false` / `"stopReason"` - highest-priority override, beats exit code 2.

**Other techniques:**

- **A Stop hook is the only way to *guarantee* something runs before a turn ends.** `brain-bootstrap`
  uses one to block turn-end while tests, lint or typecheck fail, capped at 25 iterations and gated
  on a flag file written only when source (not config) files changed. The testing floor here is a
  CLAUDE.md rule Claude must remember; this makes it mechanically unbypassable.
- **`/goal`** - a natural-language completion condition a small model re-checks after every turn.
  Distinct from `/loop` (time-based) and Stop hooks (settings-scoped).
- **`context: fork` in skill frontmatter** - runs a skill body as a subagent prompt. `supply-chain-audit`
  uses exactly this, plus tool restriction, to make an audit skill that cannot write anything.
- **Writer/Reviewer two-session pattern** - one session implements, a second with fresh context
  reviews the diff. Anthropic documents it as beating self-review.
- **gitleaks via `core.hooksPath`** - a real git hook catches secrets that never pass through Claude
  at all (manually-staged files, non-Claude edits). Different layer from every guard here.
- **`.sample` deep-merge bootstrap** (`IvanKuzyshyn`) - deploy globs `*.sample.*`; if the target
  exists and both are JSON and `jq` is present, deep-merges with the **existing user file winning**
  on conflicts and arrays unioned. The mechanism for shipping config defaults without clobbering.
- **`ccs` layering** (`DazzleML`) - shared config copied in, personal files seeded **only if absent**,
  shared CLAUDE.md importing personal `@`-files so upstream pulls never conflict. Answers the
  one-global-config-across-many-client-repos problem.

### Marketplace question: skip it

Marketplaces solve distribution **to other people**: versioned installs, discoverability, `renames`
for deprecation. This is one git repo, edited directly, with instant effect. Both real marketplaces
inspected carry overhead a solo repo does not need. The pattern actually worth taking is the
canonical-source-plus-mirror layout, and `markky21` shows the honest version of it is **a plain
symlink**, mechanically identical to the existing `.claude-personal` and `.claude-fibo` junctions.
No `marketplace.json` required.

### CI-runs-Claude question: narrow yes

`anthropics/claude-code-action` costs an API key billed **separately from any subscription**, plus
Actions minutes, plus prompt-injection exposure on untrusted PR content. It earns its keep only
where no interactive session already reviews changes: **teammate-authored PRs on client repos**, not
solo personal repos. The one solo exception with real value is a scheduled supply-chain content scan
on skill and hook changes.

---

## What the good production repos do that a personal setup usually does not

From 10 verified `CLAUDE.md`/`AGENTS.md` files (next.js, biome, oxc, ghostty, temporal, prisma, uv,
codex, deno, sst):

1. **CLAUDE.md is a pointer, not a duplicate.** Almost all of them keep content in one `AGENTS.md`
   and make `CLAUDE.md` a symlink or a one-line `@AGENTS.md` import. Per-tool files that drift are
   the anti-pattern they actively avoid.
2. Evidence rules stated as hard, checkable requirements rather than etiquette.
3. Strength-tagged bullets so priority is legible without prose.
4. Numeric ratchets and explicit decision trees instead of "use judgment".
5. One canonical location per artifact type, everything else declared a generated mirror.
6. Blunt consequence framing on safety-critical rules (ghostty's hard no-PR boundary, oxc's ban
   policy for repeat low-quality AI PRs).
7. A scoped "Ask First" allowlist rather than a blanket "ask when unsure".

A good file can be 25 lines (uv) or 558 (next.js). Length is not the variable; **whether rules are
mechanically checkable** is.

---

## Repos worth keeping as reference

| repo | why |
|---|---|
| `anthropics/skills` | official skill idiom. Only `name`, `description`, `license` in frontmatter across all 18 examples. Progressive disclosure done properly: mcp-builder's `reference/` is 2537 lines against a 236-line SKILL.md |
| `citypaul/.dotfiles` | 47 engineering-discipline skills, changesets releases, CI, frontmatter tests, install-path test suite |
| `poshan0126/dotclaude` | the security-hook set, hook fixture tests, and the 1200-token CI budget gate |
| `disler/claude-code-hooks-mastery` | 13 wired hook events and the full JSON-control-field catalog |
| `solatis/claude-config` | skills as thin stubs over a shared Python workflow engine; the conventions REGISTRY with CI-checked coupling; the Timeless Present rule |
| `vsbuffalo/dotfiles` | `supply-chain-audit`, the most on-point find given this session's own incident |
| `ChrisWiles/claude-code-showcase` | `skill-eval.js` + `skill-rules.json`: deterministic weighted skill-trigger scoring with a JSON schema |
| `DazzleML/dazzle-claude-code-config` | `ccs` layering, per-agent-scoped hooks |
| `ZacheryGlass/.claude` | compiled Go statusline, cross-model Gemini delegation, file-backed resumable orchestrator |

Content farms, verified and rejected: `rohitg00/awesome-claude-code-toolkit` (120 plugins of generic
persona boilerplate), `alirezarezvani/claude-skills` (346 skills, mostly business personas; only its
`engineering/` folder and repo tooling are worth anything).

---

## Corrections to earlier claims in this run

- Scout B listed `allowed-tools`, `context: fork`, `agent:`, `paths:`, `model:` as underexploited
  SKILL.md frontmatter. True of the docs, but **Anthropic's own 18 example skills use none of them** -
  only `name`, `description`, `license`. Treat those fields as available, not as best practice.
- Scout C's Prisma finding (canonical source plus `prepare`-script-generated mirrors) is the heavy
  variant. `markky21` shows the common real-world version is a plain symlink.
- `elizabethfuentes12`'s README documents a `rules/` folder that does not exist in the repo.
- `shanraisshan`'s `reports/llm-day-to-day-degradation.md` is speculative synthesis of others'
  Twitter claims, not original measurement. No repo in the corpus contained real benchmarks.
