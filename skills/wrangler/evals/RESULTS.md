# Wrangler eval results - bounded pass, 2026-10-08

One bounded eval pass per todo 920: one fixture per sidecar, one intact run plus one `--cut-file`/
`--cut-section` run per fixture, no reruns (no fixture crashed, so the one allowed retry was never
needed). Approved spend: Joe, 2026-10-07 (see todo 920's Notes).

## Fixture list

| Sidecar | Fixture id | Fixture label |
|---|---|---|
| `config-and-dev.md` | 1 | `config-and-dev-remote-bindings-and-vitest` |
| `deploy-and-ops.md` | 2 | `deploy-and-ops-secret-and-rollback` |
| `storage-bindings.md` | 3 | `storage-bindings-vectorize-preset-and-d1-remote-migrations` |
| `other-bindings.md` | 4 | `other-bindings-queues-consumer-and-workflows-params` |

## Before / after scores

| Fixture | Intact | Cut | Verdict |
|---|---|---|---|
| 1 config-and-dev | 5/5 (100%) | 3/5 (60%) | **degrades** |
| 2 deploy-and-ops | 4/4 (100%) | 4/4 (100%) | **does not degrade** (flagged, not rerun) |
| 3 storage-bindings | 3/3 (100%) | 2/3 (67%) | **degrades** |
| 4 other-bindings | 3/3 (100%) | 1/3 (33%) | **degrades** |

## Per-fixture detail

### Fixture 1 - config-and-dev.md

- Cut: `--cut-file skills/wrangler/config-and-dev.md --cut-section "### Remote Bindings for Local Dev" --cut-section "### Local Testing with Vitest"`
- Intact: 5/5 PASS.
- Cut: 3/5 PASS. Both failures are the Vitest-package expectations: the cut run named
  `@cloudflare/vitest-plugin` (with `cloudflareTest`/`defineConfig` from `vitest/config`) instead of
  the sidecar's `@cloudflare/vitest-pool-workers` + `defineWorkersConfig`, i.e. the model, deprived
  of the sidecar, retrieved or recalled a different (newer-sounding, unverified) package shape.
  The remote-bindings expectations (1-3) still passed intact from general Wrangler knowledge.
- **Degrades materially.**

### Fixture 2 - deploy-and-ops.md

- Cut: `--cut-file skills/wrangler/deploy-and-ops.md --cut-section "### Manage Secrets" --cut-section "### Versions and Rollback"`
- Intact: 4/4 PASS. Cut: 4/4 PASS. Tied.
- **Does not degrade - flagged, not rerun.** `wrangler secret put`/`wrangler rollback <VERSION_ID>`
  are common enough Wrangler knowledge (and Cloudflare's docs are public) that the model answers
  correctly with or without this sidecar's excerpt. This fixture is not currently proving the
  routing is load-bearing; it is accepted as-is per the task's instruction not to spend a second
  run rewriting it.

### Fixture 3 - storage-bindings.md

- Cut: `--cut-file skills/wrangler/storage-bindings.md --cut-section "### Manage Indexes" --cut-section "### Migrations"`
- Intact: 3/3 PASS. Cut: 2/3 PASS. The failure: the cut run gave only the `--remote` migrations
  command and never mentioned the `--local` form or contrasted the two, failing the
  remote-vs-local-distinction expectation.
- **Degrades materially.**

### Fixture 4 - other-bindings.md

- Cut: `--cut-file skills/wrangler/other-bindings.md --cut-section "### Manage Queues" --cut-section "### Manage Workflows"`
- Intact: 3/3 PASS. Cut: 1/3 PASS. Both failures: the cut run invented a non-existent
  `queues consumer worker add` subcommand (instead of `queues consumer add`), and passed the
  Workflow's JSON payload as a bare positional argument instead of the `--params` flag.
- **Degrades materially** (largest drop of the four).

## Cost

Per `tools/skill_eval.py`'s own docstring, each fixture run spends real money and network: an
executor `claude -p` call plus a denied-tools grader `claude -p` call, each `~$0.20` per the
docstring's estimate. Actual costs printed by the harness (`total_cost_usd` from each run, summed
across executor + grader):

| Run | Cost |
|---|---|
| f1-intact | $0.30 |
| f1-cut | $0.40 |
| f2-intact | $0.33 |
| f2-cut | $0.39 |
| f3-intact | $0.29 |
| f3-cut | $0.48 |
| f4-intact | $0.28 |
| f4-cut | $0.37 |
| **Total** | **$2.84** |

No fixture crashed (no executor/grader error on any of the 8 runs), so the one allowed
crash-retry was never used, and nothing was rerun beyond the bounded 1 intact + 1 cut per fixture.

## Byte-identical restore proof

After every cut run, `mutated_files()`'s own `RESTORED ... ok` line confirmed the in-process
restore, and a `git diff --quiet HEAD -- skills/wrangler/` check after each cut (and again after
the full pass) exited 0 with only `skills/wrangler/evals/` (new, untracked) showing in
`git status --porcelain -- skills/wrangler/` - all four sidecar `.md` files are byte-identical to
`HEAD` after the pass.

## A tooling finding, fixed under todo 1130 (workaround no longer needed)

`skill_eval.py`'s `locate_section()`/`HEADING_RE` (`^(#{1,6})\s`) did not know about fenced code
blocks: a `# comment` line inside a ```bash``` block (very common in these sidecars) was matched as
a markdown ATX heading. For most real sections this made a `--cut-section` on the section's own
heading stop at the *first* bash comment it contains, deleting only a few dozen characters (the
heading and any intro prose) and leaving the actual commands untouched - confirmed empirically
while preparing this pass. Fixture 1's two cut targets (`### Remote Bindings for Local Dev`,
`### Local Testing with Vitest`) happen to contain no `#`-led lines, so a normal heading cut worked
there regardless. Fixtures 2-4's needed facts sit inside bash blocks, so at the time this pass was
written the cut-section arguments instead targeted the bash *comment line itself* as the heading
(e.g. `"# Set secret - interactive prompt (preferred, wrangler will ask for the value securely)"`),
exploiting the same bug deliberately to reach the actual command line.

Todo 1130 made `locate_section()` fence-aware: a line whose stripped start is a backtick fence
(three or more backticks) or `~~~` toggles fence state, and a heading match inside an open fence
is now ignored. The old bash-comment
targets no longer match at all (`locate_section` now returns `None` for them, proven in todo 1130's
dispatch), so the cut-section arguments above have been re-pointed at the real section headings
(`### Manage Secrets` / `### Versions and Rollback` for fixture 2, `### Manage Indexes` /
`### Migrations` for fixture 3, `### Manage Queues` / `### Manage Workflows` for fixture 4). The
workaround is no longer needed for any fixture in this file.
