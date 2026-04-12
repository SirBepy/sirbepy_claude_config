---
name: jest-lua
description: Triggers on /jest-lua only. Manages jest-lua testing for Roblox/Luau projects - running tests, creating test files, scaffolding test suites, and interpreting output.
---

# /jest-lua

> Run, create, and manage jest-lua tests for Roblox/Luau projects.

## Commands

### `/jest-lua`
Show test status overview and available subcommands.

1. Detect the project's jest-lua setup (look for `test.project.json`, `tests/jest.config.luau`, `testing/wally.toml`).
2. List existing test files (`*.spec.luau`).
3. Show subcommand help.

### `/jest-lua run [filter]`
Run tests.

1. Build the test place: `rojo build test.project.json -o TestPlace.rbxl`
2. Run tests: `run-in-roblox --place TestPlace.rbxl --script scripts/run-tests.lua`
3. If `filter` provided, note that jest-lua CLI filtering must be configured in `jest.config.luau` or the run script - inform user if not set up.
4. Parse output, summarize pass/fail counts, show failing test details.
5. Clean up `TestPlace.rbxl` after run.

### `/jest-lua create <module-path>`
Create a test file for an existing module.

1. Read the target module to understand its exports and pure functions.
2. Determine which package it belongs to (check `test.project.json` Source mappings).
3. If the package isn't mapped in `test.project.json`, add it to `ReplicatedStorage.Source.<PackageName>`.
4. Create `tests/<package-name>/<ModuleName>.spec.luau` following the project test pattern (see Template below).
5. Generate meaningful test cases covering: happy path, edge cases, boundary values, error conditions.
6. Only test pure functions that don't depend on Roblox runtime services (no Instance creation, no game:GetService calls in the module under test).

### `/jest-lua scaffold <package-name>`
Set up testing infrastructure for a package that has no tests yet.

1. Check if `test.project.json` maps this package under `ReplicatedStorage.Source`. If not, add it.
2. Create `tests/<package-name>/` directory.
3. Scan the package's `src/` for modules with pure, testable functions.
4. For each testable module, run the `/jest-lua create` flow.
5. Report which modules were skipped (too coupled to Roblox runtime) and which got tests.

### `/jest-lua init`
Bootstrap jest-lua testing in a project that doesn't have it yet.

1. Check for existing setup. If found, report and stop.
2. Create required files:
   - `testing/wally.toml` with Jest 3.10.0 dev-dependencies
   - `tests/jest.config.luau` with `testMatch = { "**/*.spec" }`
   - `scripts/run-tests.lua` test runner script
   - `test.project.json` Rojo project mapping DevPackages, Source, and Tests
3. Instruct user to run `cd testing && wally install` to fetch packages.
4. Report setup complete.

---

## Test File Template

All test files follow this exact pattern:

```lua
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local JestGlobals = require(ReplicatedStorage.DevPackages.JestGlobals)
local describe = JestGlobals.describe
local it = JestGlobals.it
local expect = JestGlobals.expect

local ModuleName = require(ReplicatedStorage.Source.PackageName.ModuleName)

describe("ModuleName.functionName", function()
	it("describes expected behavior", function()
		expect(ModuleName.functionName(input)).toBe(expected)
	end)
end)
```

### Conventions

- File naming: `<ModuleName>.spec.luau` matching the source module name exactly.
- One `describe` block per exported function.
- Nested `describe` for sub-scenarios within a function.
- Use `toBe()` for primitives, `toBeDefined()` for existence, `toBeTruthy()`/`toBeFalsy()` for boolean-ish.
- Mock dependencies by passing functions as parameters (dependency injection), not by monkey-patching.
- Tests live in `tests/<package-name>/` mirroring the package structure.

### What to Test

- Pure utility functions (math, formatting, validation, data transformation).
- Functions that accept all dependencies as parameters.
- Stateless logic extracted from services.

### What NOT to Test (in jest-lua)

- Anything requiring live Roblox Instances (Parts, Players, Workspace).
- Functions that call `game:GetService()` internally.
- Event-driven flows (OnClientEvent, OnServerEvent).
- UI components.

---

## Infrastructure Files Reference

| File | Purpose |
|---|---|
| `test.project.json` | Rojo project that maps DevPackages, Source modules, and Tests into a test DataModel |
| `tests/jest.config.luau` | Jest config, `testMatch = { "**/*.spec" }` |
| `scripts/run-tests.lua` | Entry point script, runs `Jest.runCLI()` and exits with status code |
| `testing/wally.toml` | Wally manifest for test-only dependencies (Jest 3.10.0, JestGlobals 3.10.0) |
| `testing/DevPackages/` | Wally-installed test packages (gitignored, run `cd testing && wally install`) |

---

## Linting

After creating or modifying test files, run the project's linter and formatter if available:
- `selene src/` for linting
- `stylua src/` for formatting
- Also run on `tests/` directory: `selene tests/` and `stylua tests/`
