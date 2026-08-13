#!/usr/bin/env bash
# UserPromptSubmit hook: when a disable-model-invocation skill (close, create-pr,
# autopilot, pickup, etc.) is named in prose rather than typed as its own literal
# /command, that flag removes it from the model-facing Skill tool listing by design
# (safety: no spontaneous /close, /create-pr, /autopilot firing on its own). Without
# this hook, Claude has to remember a written rule to fall back to reading the
# skill's SKILL.md directly - unreliable. This hook makes that fallback deterministic:
# it scans every flagged skill's frontmatter name against the submitted prompt text
# and, on a match, inlines the full SKILL.md as additionalContext so Claude executes
# it directly instead of reporting it "unavailable". Always exits 0, never blocks.
input=$(cat)
hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
printf '%s' "$input" | python "$hook_dir/flagged-skill-mention.py"
exit 0
