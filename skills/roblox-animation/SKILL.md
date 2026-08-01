---
name: roblox-animation
description: Two subcommands - `author <name>` generates a placeholder KeyframeSequence Luau module; `import <url-or-path>` converts a Roblox Marketplace URL or Mixamo BVH file into the same shape.
disable-model-invocation: true
argument-hint: "[author <name>] | [import <url-or-path>]"
---

# /roblox-animation

> Author or import Roblox animations as KeyframeSequence Luau modules the dev can visually tune in Studio.

## Triggers

`/roblox-animation` followed by a subcommand:

- `/roblox-animation author kick` - hand-authored placeholder from a name
- `/roblox-animation import https://create.roblox.com/store/asset/2515090838/Kick` - Marketplace URL passthrough
- `/roblox-animation import assets/animation-imports/kick.bvh` - parse a BVH file

Never auto-invoke. The dev picks the subcommand explicitly.

## Subcommand: author

Generates a placeholder KeyframeSequence module from scratch.

1. **Detect rig.** Read `game-packages/ball-sim/src/Config.luau` (or equivalent) for `playerHeight` and `playerRadius`. Default to R15 unless the dev's project clearly uses R6.

2. **Decide save location.** Look for existing animation files. Common locations: `src/ReplicatedStorage/Animations/`, `game-packages/animations/src/`, `src/Shared/Animations/`. If none, create `src/ReplicatedStorage/Animations/` - it auto-mounts via the project's existing `src/ReplicatedStorage` Rojo entry.

3. **Author the keyframes.** Build a 5-8 keyframe motion as a storyboard comment at the top of the file, then emit a Luau module with the canonical structure (see template under `## Output format` below). Include named marker events at the contact / climax moment so game code can listen via `track:GetMarkerReachedSignal(name)`.

4. **Emit a smoke test.** REQUIRED. Place at `tests/animations/<Name>.spec.luau`. Must assert: module shape (NAME / PRIORITY / LOOPED / build), `build()` returns a `KeyframeSequence` (catches Plugin-capability + invalid-enum errors at jest time, not playtest time), at least 2 keyframes emitted, each Keyframe has a HumanoidRootPart root Pose, Time values monotonically increasing. Reference: `tests/animations/Kick.spec.luau`. Without this test, the dev only hits errors at Studio playtest - shipped 2026-05-17 after exactly that bit twice (AuthoredHipHeight Plugin-gate, Enum.PoseEasingStyle.Quad doesn't exist).

5. **Verify build + tests.** Run `bash scripts/check.sh` (or `rojo build` if no check script). Must report green before commit.

6. **Report.** Path, bones touched, marker events with timestamps, integration snippet, visual-tune instructions.

## Subcommand: import

Two input forms:

### Form A - Roblox Marketplace URL

URL pattern: `https://create.roblox.com/store/asset/<ID>/<slug>` or `https://www.roblox.com/library/<ID>/<slug>`.

1. **Extract the asset ID** from the URL (the numeric segment after `/asset/` or `/library/`).
2. **Verify** the asset exists by fetching the Marketplace page. Confirm it is an Animation (not a model or audio). If unclear, ask the dev.
3. **Emit a Luau stub** under the save-location convention from the author flow:
   ```lua
   --!strict

   -- Marketplace import. Source: https://create.roblox.com/store/asset/<ID>/<slug>
   -- Imported on YYYY-MM-DD by /roblox-animation import.

   local Animation = {}

   Animation.NAME = "<slug>"
   Animation.ASSET_ID = "rbxassetid://<ID>"
   Animation.PRIORITY = Enum.AnimationPriority.Action
   Animation.LOOPED = false

   function Animation.create(): Animation
       local anim = Instance.new("Animation")
       anim.AnimationId = Animation.ASSET_ID
       return anim
   end

   return Animation
   ```
4. **Report.** Asset ID, source URL, save path, integration snippet (`local Anim = require(...); local track = humanoid.Animator:LoadAnimation(Anim.create()); track:Play()`).

Marketplace assets are NOT visually editable - they are published bytes. If the dev wants to tune, suggest exporting via the Animation Editor's "Open Existing Animation" + their `rbxassetid`, modifying, and re-publishing as a new asset.

### Form B - BVH file path

BVH is plain text. The dev grabs it from Mixamo (Export -> Format: "Without Skin" -> BVH) or any BVH library and drops it in a known folder (default: `assets/animation-imports/<name>.bvh`).

1. **Confirm Python is available** via `python --version` or `python3 --version`. If neither, tell the dev to install Python 3.10+ and stop.
2. **Run the helper script** `bvh_to_keyframes.py` (sidecar in this skill folder):
   ```bash
   python ~/.claude/skills/roblox-animation/bvh_to_keyframes.py <input.bvh> <output.luau> [--name <NAME>] [--priority Action|Movement|Idle|Core|Action2|Action3|Action4]
   ```
   The script parses joint hierarchy + per-frame rotations, remaps Mixamo / standard BVH joint names to Roblox R15 bone names, samples to ~30 keyframes evenly (or fewer if the animation is short), and emits the same KeyframeSequence Luau shape as the author subcommand.
3. **Verify build.** `rojo build default.project.json -o build/<placefile>`.
4. **Report.** Frame count, keyframe count, duration, bones touched, save path, integration snippet.

If a BVH joint has no Roblox equivalent (Mixamo has fingers, Roblox R15 stops at hands), the script logs a warning and drops it.

## Output format

All paths emit the same Luau shape: a module exporting `Animation.build(): KeyframeSequence` (author + BVH import) or `Animation.create(): Animation` (Marketplace import). This consistency lets game code consume both paths identically.

Template for the build-side (author + BVH):

```lua
--!strict

-- <Source description: AUTHORED-PLACEHOLDER or Marketplace URL or BVH import>
-- Storyboard or import metadata here.

local Animation = {}

Animation.NAME = "<Name>"
Animation.PRIORITY = Enum.AnimationPriority.Action
Animation.LOOPED = false

local function pose(parent, boneName, cf, easing, dir) ... end
local function keyframe(seq, time, name?) ... end
local function buildPoseTree(kf, poses, easing, dir) ... end

function Animation.build(): KeyframeSequence
    local seq = Instance.new("KeyframeSequence")
    seq.Name = Animation.NAME
    -- keyframes here
    return seq
end

return Animation
```

Existing reference: `src/ReplicatedStorage/Animations/Kick.luau` in socka_heads.

## Visual editing round-trip in Studio

For build-side modules (author + BVH import): instantiate via `local seq = require(...).build()` in Studio's command bar, parent to workspace, right-click in Explorer, "Edit in Animation Editor", drag bones / retime / tweak easing, then "..." menu -> Export -> Publish to Roblox. Drop the returned `rbxassetid://N` into your `Animation` instance.

For Marketplace imports: the asset is already published. To tune, the Animation Editor's "Open Existing Animation" accepts an `rbxassetid` and re-published versions get new IDs.

`KeyframeSequenceProvider:RegisterKeyframeSequence` is dev-mode-only. Shipped games must use a real published asset ID.

**Plugin-capability gated properties (do NOT write from runtime scripts):**

`KeyframeSequence.AuthoredHipHeight`, `KeyframeSequence.Priority`, and `KeyframeSequence.Loop` can only be written from a Plugin context. Runtime scripts get "lacking capability Plugin" errors. In emitted modules, skip these writes in `build()` and have the caller set the equivalents on the `AnimationTrack` after loading:

```lua
local track = animator:LoadAnimation(anim)
track.Priority = Animation.PRIORITY     -- AnimationTrack.Priority IS runtime-writable
track.Looped = Animation.LOOPED         -- AnimationTrack.Looped IS runtime-writable
```

`AuthoredHipHeight` has no runtime equivalent — Roblox uses the rig's default hip height. Don't emit a write for it.

**Valid `Enum.PoseEasingStyle` values are limited:** `Linear`, `Constant`, `Elastic`, `Cubic`, `Bounce`. Do NOT use `Quad`, `Sine`, `Back`, `Exponential` etc. — those are `Enum.EasingStyle` (for tweens), not `Enum.PoseEasingStyle`. Skill output should use `Cubic` as the default smooth ease, `Linear` for sharp transitions.

