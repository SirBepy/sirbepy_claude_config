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

## Project Structure (Single-Main Pattern)

Every Roblox project Joe works on uses **one server entry + one client entry**, period. No scattering of `*.server.luau` and `*.client.luau` scripts across `ServerScriptService` / `StarterPlayerScripts`.

- `src/ServerScriptService/Main.server.luau` — single server entry. Initializes config, then calls each package's `start(deps)` in deterministic dependency order.
- `src/StarterPlayer/StarterPlayerScripts/Main.client.luau` — single client entry. Hydrates service `_events` tables (via `EventManager.getServiceEvents("Service")`), then mounts each UI package with its deps.

**Why:** running everything from one file guarantees deterministic init order, prevents drift between scripts, and gives one obvious place to read the boot sequence.

### Per-package entry

Inside each package, the public entry is the package init module (`init.luau` if the project uses Rojo's folder-as-module convention; `Main.luau` in sirbepy_roblox-style projects where the package is required as `require(Modules.x.Main)`).

The entry exposes:
- `Service.start(deps?)` for services. Optional `deps` table wires runtime dependencies (e.g., `start({ mapService = MapService, teamService = TeamService })`). Internally `start` calls existing `_injectXxx(svc)` setters so tests keep working unchanged.
- `Service.stop()` for shutdown / hot-reload.
- `Service._injectXxx(mock)` setters — kept as the test-flavored API for fine-grained mock swaps. Never call `_injectXxx` from production code; pass deps through `start({...})` instead.
- UI packages: `Package.mount(playerGui, deps)` and `Package.unmount()`.

### sirbepy_roblox per-package entry convention

Shared libs in `sirbepy_roblox/packages/<name>/src/` use `Main.luau` (not `init.luau`) as the package entry, with helper modules as siblings (`Events.luau`, `LeaderDetection.luau`, etc.). Consumers in those projects require packages as `require(Modules.x.Main)`. Tycoon-or-die-style projects keep `init.luau` to avoid churn on every cross-package require site - both styles are acceptable, but stay consistent within one project.

## Real Roblox API Footguns

These caused real outages in tycoon_or_die's first end-to-end Studio Run. Worth checking on every Luau project that wraps Roblox primitives behind a service abstraction.

### BindableEvent: connect through `.Event`, not the instance

Real `BindableEvent`: `bindable:Fire(...)` works, but you must connect via `bindable.Event:Connect(fn)`. Reading `.Connect` as a property on the Instance throws `Connect is not a valid member of BindableEvent`.

```lua
-- WRONG (works against table mocks, throws against real BindableEvent):
if signal.Connect then signal:Connect(handler) end

-- RIGHT:
local resolved = (typeof(signal) == "Instance" and signal:IsA("BindableEvent")) and signal.Event or signal
resolved:Connect(handler)
```

If the project has a test mock for events, give it `mock.Event = mock` so `mock.Event:Connect` resolves the same as `mock:Connect`. Same trick for `FakeSignal` helpers and inline `makeBindable()` factories in spec files. Without it, production code using `.Event:Connect` works against real Roblox but fails the suite.

Don't write defensive guards like `if X.Connect then` to gate connection — reading `.Connect` on an Instance is itself the throw site. Either resolve via the typeof check above, or wrap in pcall.

### TextChatService: `DefaultChannel` is the legacy API

Newer experiences use `TextChatService.TextChannels.RBXGeneral` (a child instance). Older ones use the deprecated `TextChatService.DefaultChannel` property. Direct property access on the Instance throws if the field isn't present, so resolve through `pcall(function() return tcs.DefaultChannel end)` for the legacy path and `tcs:FindFirstChild("TextChannels"):FindFirstChild("RBXGeneral")` for the modern one.

### sirbepy ConfigLoader: pre-create stubs to avoid 5s WaitForChild stalls per service

`ConfigLoader.getPrivate(name, defaults)` (in `sirbepy_core`) does `ServerStorage.Configs:WaitForChild(name, 5)` before falling back to defaults. With ~15 services each calling getConfig once at boot, missing stubs add up to a 50+ second delay before the server finishes publishing event folders — clients give up on `getServiceEvents` (10s WaitForChild) long before that.

Mitigation: drop a `return {}` stub at `src/ServerStorage/Configs/<ServiceName>.luau` for every service. Each lookup resolves instantly.

`ConfigLoader.getPrivate` reads from `ServerStorage` which the client cannot see. If the same service module starts on both sides (e.g. `LobbyService.start` mounts a view client-side), pcall the getConfig call and fall back to defaults rather than letting the client crash on `Configs is not a valid member of ServerStorage`.

## Testing Roblox / Luau Code

Use jest-lua + run-in-roblox for unit and integration tests.

- Tests live under `tests/` with `tests/<package>/<Module>.spec.luau` mirroring source layout.
- Spec files use `describe()/it()/expect()` from `JestGlobals` (NOT TestEZ's `.to.equal()` syntax).
- Build: `rojo build test.project.json -o build/test.rbxl`.
- Execute: `run-in-roblox --place build/test.rbxl --script tests/run.server.luau` (sahur uses `scripts/run-tests.lua`).
- Studio MUST be running once to populate the registry pointer; otherwise run-in-roblox panics with `os error 2`.
- Cosmetic Studio popup "Parent property of ReplicatedStorage is locked, current parent: Game, new parent NULL" can appear during run-in-roblox cleanup - dismiss; tests still return results.

Always write tests for new code and re-run the full suite after any change. Do not claim "done" without seeing a `Suites: N passed, 0 failed | Tests: M passed, 0 failed, 0 skipped` line.
