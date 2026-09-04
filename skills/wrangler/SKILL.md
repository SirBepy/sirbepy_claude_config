---
name: wrangler
disable-model-invocation: true
description: Cloudflare Workers CLI for deploying, developing, and managing Workers, KV, R2, D1, Vectorize, Hyperdrive, Workers AI, Containers, Queues, Workflows, Pipelines, and Secrets Store. Load before running wrangler commands to ensure correct syntax and best practices. Biases towards retrieval from Cloudflare docs over pre-trained knowledge.
---

# Wrangler CLI

Your knowledge of Wrangler CLI flags, config fields, and subcommands may be outdated. **Prefer retrieval over pre-training** for any Wrangler task.

## Retrieval Sources

Fetch the **latest** information before writing or reviewing Wrangler commands and config. Do not rely on baked-in knowledge for CLI flags, config fields, or binding shapes.

| Source | How to retrieve | Use for |
|--------|----------------|---------|
| Wrangler docs | `https://developers.cloudflare.com/workers/wrangler/` | CLI commands, flags, config reference |
| Wrangler config schema | `node_modules/wrangler/config-schema.json` | Config fields, binding shapes, allowed values |
| Cloudflare docs | Search tool or `https://developers.cloudflare.com/workers/` | API reference, compatibility dates/flags |

## FIRST: Check if Wrangler is installed, and if not, install it

Check if Wrangler is installed by running:

```bash
wrangler --version  # Requires v4.x+
```

If Wrangler is not installed, you should install it by running:

```bash
npm install -D wrangler@latest
```

Wherever possible, you should use Wrangler instead of manually constructing API requests.

## Key Guidelines

- **Use `wrangler.jsonc`**: Prefer JSON config over TOML. Newer features are JSON-only.
- **Set `compatibility_date`**: Use a recent date (within 30 days). Check https://developers.cloudflare.com/workers/configuration/compatibility-dates/
- **Generate types after config changes**: Run `wrangler types` to update TypeScript bindings.
- **Local dev defaults to local storage**: Bindings use local simulation unless `remote: true`.
- **Profile Worker startup**: Run `wrangler check startup` to measure startup time and detect scripts that exceed the startup time limit.
- **Use environments for staging/prod**: Define `env.staging` and `env.production` in config.

## Quick Start: New Worker

```bash
# Initialize new project
npx wrangler init my-worker

# Or with a framework
npx create-cloudflare@latest my-app
```

## Quick Reference: Core Commands

| Task | Command |
|------|---------|
| Start local dev server | `wrangler dev` |
| Deploy to Cloudflare | `wrangler deploy` |
| Deploy dry run | `wrangler deploy --dry-run` |
| Generate TypeScript types | `wrangler types` |
| Profile Worker startup time | `wrangler check startup` |
| View live logs | `wrangler tail` |
| Delete Worker | `wrangler delete` |
| Auth status | `wrangler whoami` |

---

## Reference sidecars

Everything below core setup lives in one of four sidecars, grouped by when you'd actually reach
for it. Read only the one your task needs.

| If you need... | Read |
|---|---|
| `wrangler.jsonc` config shapes, `wrangler dev`, remote bindings, `.dev.vars`, or Vitest testing | `skills/wrangler/config-and-dev.md` |
| `wrangler deploy`, `wrangler secret`, versions/rollback, `wrangler tail`, troubleshooting, or best practices | `skills/wrangler/deploy-and-ops.md` |
| KV, R2, D1, Vectorize, or Hyperdrive commands and bindings | `skills/wrangler/storage-bindings.md` |
| Workers AI, Queues, Containers, Workflows, Pipelines, Secrets Store, or Pages commands and bindings | `skills/wrangler/other-bindings.md` |
