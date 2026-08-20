import sys, json, glob, os, re

try:
    payload = json.load(sys.stdin)
    prompt = payload.get('prompt', '') or ''
except Exception:
    prompt = ''

if not prompt:
    sys.exit(0)

# Machine-injected turns (system/task notifications, peer/daemon channel
# messages) aren't real user invocations and can quote old skill mentions in
# their body. Detected by envelope SHAPE, a leading run of bracketed `[tag]`
# markers, not a per-channel prefix list, so a new channel needs no update.
_ZERO_WIDTH_RE = re.compile('[​‌‍﻿]')
_ENVELOPE_TAG_RE = re.compile(r'^(\[[^\[\]\n]+\]\s*)+')

_normalized = _ZERO_WIDTH_RE.sub('', prompt).lstrip()
if _normalized.startswith('[SYSTEM NOTIFICATION') or _ENVELOPE_TAG_RE.match(_normalized):
    sys.exit(0)

# Real slash-command usage is typed as the first thing in the message, OR as
# its own line further down (todo 342: measured against 509 real prompts on
# this machine, see flagged-skill-mention.md - first_line-only missed 193 of
# them). A mention buried mid-sentence still doesn't count as an invocation.
first_line = prompt.split('\n', 1)[0]
line_starts = [ln.strip() for ln in prompt.split('\n')]

# Resolve relative to this file first: the hook lives next to skills/ in the
# same config tree, and $HOME/~ has no ".claude" in CI or a fresh clone.
skills_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'skills')
if not os.path.isdir(skills_dir):
    skills_dir = os.path.expanduser('~/.claude/skills')
contexts = []

for path in sorted(glob.glob(os.path.join(skills_dir, '*', 'SKILL.md'))):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        continue

    if not re.search(r'^disable-model-invocation:\s*true', content, re.MULTILINE):
        continue

    m = re.search(r'^name:\s*"?([^"\n]+?)"?\s*$', content, re.MULTILINE)
    if not m:
        continue
    name = m.group(1).strip()
    if not name:
        continue

    # Slash required: bare-word names (close, review, pickup) collide with plain
    # English and fired on ambient text, not real invocation intent.
    _name_pattern = r'(?<![\w/-])/' + re.escape(name) + r'(?![\w-])'
    mentioned = re.search(_name_pattern, first_line, re.IGNORECASE) or any(
        re.match(_name_pattern, ls, re.IGNORECASE) for ls in line_starts
    )
    if not mentioned:
        continue

    contexts.append(
        'Skill "%s" (disable-model-invocation: true, NOT shown in your Skill tool listing) '
        'was named in this prompt. Read its SKILL.md below and execute its phases directly '
        'now - do not attempt a Skill tool call for it, and never report it as unavailable, '
        'missing, or a listing hiccup.\n\n---\n%s\n---' % (name, content)
    )

if not contexts:
    sys.exit(0)

output = {
    'hookSpecificOutput': {
        'hookEventName': 'UserPromptSubmit',
        'additionalContext': '\n\n'.join(contexts),
    }
}
print(json.dumps(output))
sys.exit(0)
