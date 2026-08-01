# /close --light mode

> Read this only when `--light` was passed to /close. Otherwise ignore.

Use when context is already high (~65%+) and you want /close to complete without triggering /compact. Only the deltas from normal /close behavior are listed here. Phases 4-7 are unchanged.

## Phase 1

Same bullets as normal Phase 1, but cap every bullet to 1 sentence max. Skip sub-bullets and examples. Verdict still required. Same print rule applies: only surface it if 1-4 have a real entry.

## Phase 2

Invoke `/code-check` with scope arg `unpushed` (if commits were made this session) or `uncommitted`, via the Skill tool - same as the main path. It handles the analysis and writes the todos directly. Read its summary line for the Phase 4 counter.

## Phase 3

Delegate all writes to a single write-subagent. Do not write files inline.

Build a compact payload object from Phase 1 output:

```
{
  "memory": [ { "file": "path", "frontmatter": "...", "body": "..." } ],  // only entries that qualify
  "ai_todos": [ { "slug": "...", "title": "...", "type": "task | skill-improvement", "goal": "...", "context": "...", "approach": "...", "acceptance": "..." } ]
}
```

Memory writes go through `~/.claude/refs/memory-rubric.md`'s ADD/UPDATE/DELETE/NONE gate before anything is added to the payload, same as the main path's Phase 3 step 1.

Then dispatch ONE `Agent` call with `subagent_type: "general-purpose"`, `model: 'sonnet'`, and this prompt:

> You are a write-only subagent. Execute the following file writes exactly. No analysis, no extra output.
>
> Memory dir: derive from the current project per the Global Knowledge Vault section of CLAUDE.md (vault for cross-project facts and people, native per-project Auto Memory under `~/.claude/projects/<sanitized-cwd>/memory/` for project-local ones) - never hardcode a project path.
> For each entry in `memory`: write the file at `<memory dir>/<file>` with the given frontmatter + body. Then append a pointer line to `MEMORY.md` if not already present.
>
> `.claude/todos/`: for each entry in `ai_todos`, follow `C:\Users\tecno\.claude\skills\close\ai-todos-format.md` - scan existing files (and done/) for max numeric prefix, write `<id+1>-<slug>.md` with standard sections including a `**Type:**` line, and self-heal the `.git/info/exclude` entries per that doc's Git policy.
>
> Payload: `<JSON>`

Wait for the subagent to return before continuing to Phase 4.
