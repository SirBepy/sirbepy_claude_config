#!/usr/bin/env python3
"""
Convert a BVH (BioVision Hierarchy) animation file into a Roblox R15
KeyframeSequence Luau module.

BVH format: text. Two sections.
  HIERARCHY: joint tree with offsets + channel definitions (rotation order).
  MOTION: per-frame channel values, one row per frame.

This script:
  - parses the joint hierarchy
  - reads per-frame Euler angles in each joint's declared channel order
  - converts to CFrame.Angles(rx, ry, rz) per Roblox convention
  - remaps common BVH joint names (Mixamo / Maya / DAZ) to Roblox R15 bone names
  - samples evenly to a target keyframe count (default 30) to keep file size sane
  - emits a Luau module matching the /roblox-animation skill's output shape

Usage:
    python bvh_to_keyframes.py <input.bvh> <output.luau>
        [--name NAME] [--priority Action] [--keyframes 30] [--loop]

Joint name remapping is best-effort. Joints with no Roblox equivalent (fingers,
toes, multi-segment spines) get dropped with a warning.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Common BVH joint name -> Roblox R15 bone name. Case-insensitive match.
# Mixamo prefixes joints with "mixamorig:" - the parser strips that.
JOINT_REMAP: Dict[str, str] = {
    "hips": "LowerTorso",
    "hip": "LowerTorso",
    "spine": "UpperTorso",       # First spine segment becomes UpperTorso
    "spine1": "UpperTorso",      # Mixamo often has spine + spine1; drop one
    "spine2": None,              # discard - Roblox has no spine2
    "chest": "UpperTorso",
    "neck": None,                # Roblox attaches Head directly to UpperTorso
    "head": "Head",

    "leftshoulder": None,        # Roblox arms attach to UpperTorso directly
    "leftarm": "LeftUpperArm",
    "leftforearm": "LeftLowerArm",
    "lefthand": "LeftHand",

    "rightshoulder": None,
    "rightarm": "RightUpperArm",
    "rightforearm": "RightLowerArm",
    "righthand": "RightHand",

    "leftupleg": "LeftUpperLeg",
    "leftleg": "LeftLowerLeg",
    "leftfoot": "LeftFoot",
    "lefttoebase": None,

    "rightupleg": "RightUpperLeg",
    "rightleg": "RightLowerLeg",
    "rightfoot": "RightFoot",
    "righttoebase": None,
}


@dataclass
class Joint:
    name: str
    roblox_name: Optional[str]
    parent: Optional["Joint"] = None
    children: List["Joint"] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)  # e.g. ['Zrotation','Xrotation','Yrotation']
    channel_offset: int = 0  # index into per-frame motion row


def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"^mixamorig[:_]", "", name)
    name = re.sub(r"[_\s]", "", name)
    return name


def remap(name: str) -> Optional[str]:
    return JOINT_REMAP.get(normalize_name(name))


def parse_bvh(path: Path) -> Tuple[Joint, int, float, List[List[float]]]:
    text = path.read_text()
    lines = [line.strip() for line in text.splitlines()]

    i = 0
    if lines[i].upper() != "HIERARCHY":
        raise ValueError("expected HIERARCHY at line 1")
    i += 1

    root: Optional[Joint] = None
    stack: List[Joint] = []
    channel_cursor = 0

    while i < len(lines):
        line = lines[i]
        upper = line.upper()
        if upper.startswith("ROOT") or upper.startswith("JOINT"):
            parts = line.split(maxsplit=1)
            raw_name = parts[1] if len(parts) > 1 else "<unnamed>"
            joint = Joint(name=raw_name, roblox_name=remap(raw_name))
            if root is None:
                root = joint
            else:
                stack[-1].children.append(joint)
                joint.parent = stack[-1]
            stack.append(joint)
            i += 1
        elif upper.startswith("END SITE"):
            # skip the End Site block
            depth = 0
            while i < len(lines):
                if lines[i] == "{":
                    depth += 1
                elif lines[i] == "}":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
        elif line == "{":
            i += 1
        elif line == "}":
            stack.pop()
            i += 1
        elif upper.startswith("OFFSET"):
            i += 1  # offsets ignored - we only care about rotations for R15
        elif upper.startswith("CHANNELS"):
            parts = line.split()
            n = int(parts[1])
            chans = parts[2:2 + n]
            stack[-1].channels = chans
            stack[-1].channel_offset = channel_cursor
            channel_cursor += n
            i += 1
        elif upper.startswith("MOTION"):
            i += 1
            break
        else:
            i += 1

    if root is None:
        raise ValueError("no ROOT joint in HIERARCHY")

    # MOTION section
    frame_count = 0
    frame_time = 1.0 / 60.0
    frames: List[List[float]] = []
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue
        upper = line.upper()
        if upper.startswith("FRAMES:"):
            frame_count = int(line.split(":")[1].strip())
        elif upper.startswith("FRAME TIME:"):
            frame_time = float(line.split(":")[1].strip())
        else:
            values = [float(v) for v in line.split()]
            if values:
                frames.append(values)
        i += 1

    if frame_count == 0:
        frame_count = len(frames)

    return root, frame_count, frame_time, frames


def collect_joints(root: Joint) -> List[Joint]:
    out: List[Joint] = []

    def walk(j: Joint) -> None:
        out.append(j)
        for c in j.children:
            walk(c)
    walk(root)
    return out


def euler_to_cframe_lua(joint: Joint, motion_row: List[float]) -> str:
    """Read joint's channel values from the motion row, return a Luau CFrame.Angles expression."""
    rx_deg = ry_deg = rz_deg = 0.0
    for idx, chan in enumerate(joint.channels):
        val = motion_row[joint.channel_offset + idx]
        if chan == "Xrotation":
            rx_deg = val
        elif chan == "Yrotation":
            ry_deg = val
        elif chan == "Zrotation":
            rz_deg = val
        # position channels (Xposition/Yposition/Zposition) ignored for R15

    if rx_deg == 0 and ry_deg == 0 and rz_deg == 0:
        return "CFrame.identity"

    parts = []
    if rx_deg != 0:
        parts.append(f"math.rad({rx_deg:.3f})")
    else:
        parts.append("0")
    if ry_deg != 0:
        parts.append(f"math.rad({ry_deg:.3f})")
    else:
        parts.append("0")
    if rz_deg != 0:
        parts.append(f"math.rad({rz_deg:.3f})")
    else:
        parts.append("0")
    return f"CFrame.Angles({parts[0]}, {parts[1]}, {parts[2]})"


def sample_indices(total_frames: int, target_keyframes: int) -> List[int]:
    if target_keyframes >= total_frames:
        return list(range(total_frames))
    step = (total_frames - 1) / (target_keyframes - 1)
    return [round(i * step) for i in range(target_keyframes)]


def emit_luau(
    root: Joint,
    frame_time: float,
    frames: List[List[float]],
    sampled: List[int],
    name: str,
    priority: str,
    loop: bool,
    src_path: Path,
) -> str:
    all_joints = collect_joints(root)
    mapped = [j for j in all_joints if j.roblox_name]
    dropped = [j.name for j in all_joints if not j.roblox_name and j is not root]

    header = [
        "--!strict",
        "",
        f"-- BVH import.  Source: {src_path.name}",
        f"-- Total source frames: {len(frames)}  Frame time: {frame_time:.4f}s  Duration: {len(frames) * frame_time:.2f}s",
        f"-- Sampled keyframes: {len(sampled)}",
        f"-- Joints mapped: {', '.join(j.roblox_name for j in mapped)}",
    ]
    if dropped:
        header.append(f"-- Joints dropped (no R15 equivalent): {', '.join(dropped)}")
    header.extend([
        "-- ",
        "-- Tune visually: parent the build() result to workspace in Studio,",
        "-- right-click -> Edit in Animation Editor, then Export to publish.",
        "",
        "local Animation = {}",
        "",
        f"Animation.NAME = {name!r}",
        f"Animation.PRIORITY = Enum.AnimationPriority.{priority}",
        f"Animation.LOOPED = {str(loop).lower()}",
        "",
        "local function pose(parent: Instance, boneName: string, cf: CFrame): Pose",
        "    local p = Instance.new(\"Pose\")",
        "    p.Name = boneName",
        "    p.CFrame = cf",
        "    p.Weight = 1",
        "    p.EasingStyle = Enum.PoseEasingStyle.Linear",
        "    p.EasingDirection = Enum.PoseEasingDirection.Out",
        "    p.Parent = parent",
        "    return p",
        "end",
        "",
        "local function keyframe(seq: KeyframeSequence, time: number): Keyframe",
        "    local kf = Instance.new(\"Keyframe\")",
        "    kf.Time = time",
        "    kf.Parent = seq",
        "    return kf",
        "end",
        "",
        "function Animation.build(): KeyframeSequence",
        "    local seq = Instance.new(\"KeyframeSequence\")",
        "    seq.Name = Animation.NAME",
        "    seq.AuthoredHipHeight = 2",
        "    seq.Priority = Animation.PRIORITY",
        "    seq.Loop = Animation.LOOPED",
        "",
    ])

    body: List[str] = []
    for kf_index, frame_index in enumerate(sampled):
        t = frame_index * frame_time
        motion_row = frames[frame_index]
        body.append(f"    -- keyframe {kf_index} (source frame {frame_index}, t={t:.4f})")
        body.append(f"    do")
        body.append(f"        local kf = keyframe(seq, {t:.4f})")
        # Walk the joints in tree order so parent poses exist before children.
        # We build a flat list of (joint, parent_var_name) tuples.
        var_for: Dict[int, str] = {}
        var_counter = [0]

        def walk(joint: Joint, parent_var: str) -> None:
            if not joint.roblox_name:
                # Skip: pass parent through to children
                for child in joint.children:
                    walk(child, parent_var)
                return
            var = f"p{var_counter[0]}"
            var_counter[0] += 1
            cf_expr = euler_to_cframe_lua(joint, motion_row)
            body.append(
                f"        local {var} = pose({parent_var}, {joint.roblox_name!r}, {cf_expr})"
            )
            var_for[id(joint)] = var
            for child in joint.children:
                walk(child, var)

        # Root pose attaches to the Keyframe directly.
        root_var = f"p{var_counter[0]}"
        var_counter[0] += 1
        if root.roblox_name:
            cf_expr = euler_to_cframe_lua(root, motion_row)
            body.append(
                f"        local {root_var} = pose(kf, {root.roblox_name!r}, {cf_expr})"
            )
            for child in root.children:
                walk(child, root_var)
        else:
            # Root unmapped (rare) - attach the (forced) HumanoidRootPart and walk children under it
            body.append(
                f"        local {root_var} = pose(kf, \"HumanoidRootPart\", CFrame.identity)"
            )
            for child in root.children:
                walk(child, root_var)
        body.append(f"    end")
        body.append("")

    footer = [
        "    return seq",
        "end",
        "",
        "return Animation",
        "",
    ]

    return "\n".join(header + body + footer)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--name", default=None, help="Animation name (defaults to filename)")
    parser.add_argument(
        "--priority",
        default="Action",
        choices=["Action", "Movement", "Idle", "Core", "Action2", "Action3", "Action4"],
    )
    parser.add_argument("--keyframes", type=int, default=30)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    root, frame_count, frame_time, frames = parse_bvh(args.input)
    sampled = sample_indices(len(frames), args.keyframes)
    name = args.name or args.input.stem.title().replace("_", "")

    luau = emit_luau(
        root=root,
        frame_time=frame_time,
        frames=frames,
        sampled=sampled,
        name=name,
        priority=args.priority,
        loop=args.loop,
        src_path=args.input,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(luau)

    duration = len(frames) * frame_time
    mapped = [j for j in collect_joints(root) if j.roblox_name]
    dropped = [j.name for j in collect_joints(root) if not j.roblox_name and j is not root]

    print(f"OK: wrote {args.output}")
    print(f"    source frames: {len(frames)}  duration: {duration:.2f}s")
    print(f"    sampled keyframes: {len(sampled)}")
    print(f"    bones mapped: {', '.join(j.roblox_name for j in mapped)}")
    if dropped:
        print(f"    bones dropped: {', '.join(dropped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
