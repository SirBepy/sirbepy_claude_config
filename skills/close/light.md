# /close --light mode

> Read this only when `--light` was passed to /close. Otherwise ignore.

Use when context is already high (~65%+) and you want /close to complete without triggering /compact. Only the deltas from normal /close behavior are listed here. Phases 4-7 are unchanged.

## Phase 1

Same bullets as normal Phase 1, but cap every bullet to 1 sentence max. Skip sub-bullets and examples. Verdict still required.

## Phase 2

Delegate entirely to one `general-purpose` subagent instead of doing Steps 2a/2c inline. Prompt:

> You are a code-health reviewer. Do the following and return ONE merged JSON array of findings - no prose, no preamble.
>
> Changed files: `<list from git diff>`
>
> Step 1 - Size check: for each file, line-count it. If >400 lines AND has an obvious split seam (separate concerns, reusable unit), add finding: `{ "title": "...", "files": [...], "problem": "[file] is N lines, mixes [X] and [Y]", "fix": "split at [boundary] into [new file]" }`.
>
> Step 2 - Run TWO checks in parallel (dispatch as subagents if possible, else sequential):
>
> - DRY: for each new component/hook/function/util, grep the repo for equivalents. Finding: `{ "title", "files" [path:line both], "problem", "fix" }`.
> - Dead code: unused exports, unreachable branches, commented-out blocks, unread vars/imports. Finding: `{ "title", "files" [path:line], "problem", "fix" }`.
>
> Merge all findings into one JSON array. Empty array if none. Under 400 words total.

Wait for the subagent to return. Use its JSON array as the Phase 2 findings for Phase 3.

## Phase 3

Delegate all writes to a single write-subagent. Do not write files inline.

Build a compact payload object from Phase 1 output:

```
{
  "memory": [ { "file": "path", "frontmatter": "...", "body": "..." } ],  // only entries that qualify
  "comments": "string or null",
  "todos_to_delete": ["bullet text"],
  "ai_todos": [ { "slug": "...", "title": "...", "goal": "...", "context": "...", "approach": "...", "acceptance": "..." } ]
}
```

Then dispatch ONE `Agent` call with `subagent_type: "general-purpose"` and this prompt:

> You are a write-only subagent. Execute the following file writes exactly. No analysis, no extra output.
>
> Memory dir: `C:\Users\tecno\.claude\projects\C--Users-tecno--claude\memory\`
> For each entry in `memory`: write the file at `<memory dir>/<file>` with the given frontmatter + body. Then append a pointer line to `MEMORY.md` if not already present.
>
> `.for_bepy/COMMENTS.md`: if `comments` is non-null, append it.
> `.for_bepy/BEPY_TODOS.md`: delete any bullet matching `todos_to_delete` entries.
> `.for_bepy/ai_todos/`: for each entry in `ai_todos`, scan existing files for max numeric prefix, write `<id+1>-<slug>.md` with standard sections.
>
> Payload: `<JSON>`

Wait for the subagent to return before continuing to Phase 4.
