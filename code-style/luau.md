# Luau / Roblox Style Guide

Joe's coding preferences for Roblox projects using Luau.

## Principles

- **DRY** - Don't repeat yourself. Extract shared logic.
- **Self-descriptive code** - If a block of logic does a conceptual "thing," extract it into a named function, even if it's only called once. The function name is documentation.
- **Spread/varargs forwarding** - Prefer `function(...) inner(...) end` over manually listing parameters when wrapping or forwarding calls.

## Function Extraction

Bad - inline logic blob:
```lua
if self._categoryRules and self._categoryRules.DISPLAY_NAME then
    local sufgui = leaderboard.scoreBlock:FindFirstChild("Leaderboard")
    if sufgui then
        local titleLabel = sufgui:FindFirstChild("Title")
        if titleLabel and titleLabel:IsA("TextLabel") then
            titleLabel.Text = self._categoryRules.DISPLAY_NAME
        end
    end
end
```

Good - extracted with a descriptive name:
```lua
self:_applyDisplayName(leaderboard)
```

The function name tells you what's happening. Details live in the function body.

## Varargs Forwarding

Bad - manually listing params:
```lua
someEvent:Connect(function(player, data)
    handler(player, data)
end)
```

Good - spread when signature matches:
```lua
someEvent:Connect(function(...)
    handler(...)
end)
```

Only use spread when the wrapper doesn't need to inspect or modify the arguments.

<!-- Add more preferences below as they come up -->

## Shared Libraries (sirbepy_roblox)

SirBepy's reusable Roblox libraries live in a standalone monorepo:
- GitHub: https://github.com/SirBepy/sirbepy_roblox (private)
- Local convention: cloned as a sibling of any Roblox project (e.g., if working in `~/Desktop/Projects/foo/`, expect `~/Desktop/Projects/sirbepy_roblox/`).
- If missing locally on a fresh machine: `gh repo clone SirBepy/sirbepy_roblox` into the parent dir.

Wally registry: packages live under `sirbepy/<name>` in `https://github.com/UpliftGames/wally-index`.

### Detecting consumer status

To check whether the current Roblox project consumes shared libs: grep root `wally.toml` for `sirbepy/` deps.

### Import convention in consumers

```lua
local EventManager = require(ReplicatedStorage.Packages.Core.EventManager)
local HighlightManager = require(ReplicatedStorage.Packages.HighlightManager.HighlightManager)
```

### Active iteration on a shared lib (path-dep two-state pattern)

Consumer's `wally.toml` has two states:

**Default (committed, registry-pinned):**
```toml
Core = "sirbepy/core@^0.2.0"
```

**Active dev (uncommitted, path dep):**
```toml
Core = { path = "../sirbepy_roblox/packages/core" }
```

To iterate: swap to path dep, run `wally install`, edit lib code in `../sirbepy_roblox/`. Edits hot-propagate via Rojo serve. Never commit the path-dep state.

To ship: in `sirbepy_roblox` bump version + `wally publish`. In consumer revert wally.toml to new registry pin + `wally install` + commit.

### Windows case-collision gotcha

On Windows (case-insensitive filesystem), wally's output `Packages/` collides with any in-repo `packages/` source folder. If a project has both, rename wally's output to `WallyPackages/` after `wally install` and mount it as `ReplicatedStorage.Packages` via Rojo. See tycoon_or_die's `default.project.json` for the pattern.

## Testing Roblox / Luau Code

Use jest-lua + run-in-roblox for unit and integration tests.

- Tests live under `tests/` with `tests/<package>/<Module>.spec.luau` mirroring source layout.
- Spec files use `describe()/it()/expect()` from `JestGlobals` (NOT TestEZ's `.to.equal()` syntax).
- Build: `rojo build test.project.json -o build/test.rbxl`.
- Execute: `run-in-roblox --place build/test.rbxl --script tests/run.server.luau` (sahur uses `scripts/run-tests.lua`).
- Studio MUST be running once to populate the registry pointer; otherwise run-in-roblox panics with `os error 2`.
- Cosmetic Studio popup "Parent property of ReplicatedStorage is locked, current parent: Game, new parent NULL" can appear during run-in-roblox cleanup - dismiss; tests still return results.

Always write tests for new code and re-run the full suite after any change. Do not claim "done" without seeing a `Suites: N passed, 0 failed | Tests: M passed, 0 failed, 0 skipped` line.
