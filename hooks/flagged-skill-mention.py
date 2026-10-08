import sys, json, glob, os, re, datetime

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

# A subagent hand-back is also a relayed-text surface, not a real
# invocation - the capture showed real fires where the only new input was a
# builder's final report quoting a flagged skill by name. The envelope is
# `<agent-message from="...">` followed by a newline, then a line starting
# `[Subagent hand-back]`; one captured hand-back carried the harness's own
# neutralized form `<\agent-message` instead of the raw tag, so both are
# checked. The hand-back marker line is checked across the first 3 lines
# (not just line 2) so an envelope with extra leading blank/whitespace lines
# still matches.
_normalized = _ZERO_WIDTH_RE.sub('', prompt).lstrip()
_is_handback_envelope = (
    _normalized.startswith('<agent-message ')
    or _normalized.startswith('<\\agent-message')
    or any('[Subagent hand-back]' in line for line in _normalized.split('\n', 3)[:3])
)
if (
    _normalized.startswith('[SYSTEM NOTIFICATION')
    or _ENVELOPE_TAG_RE.match(_normalized)
    or _is_handback_envelope
):
    sys.exit(0)

# Conductor appends this block itself, quoting skill descriptions verbatim
# (e.g. "/autopilot" inside /iterate-it's own description text) - matching
# inside it means Joe's own words never need to mention a skill at all.
_CONDUCTOR_SLASH_CONTEXT_RE = re.compile(
    r'<conductor-slash-context>.*?</conductor-slash-context>', re.DOTALL
)
_match_text = _CONDUCTOR_SLASH_CONTEXT_RE.sub('', prompt)

# Instrumentation only (the backlog item tracking this is numbered 491),
# never a behavior change. Logs one line per fired skill so the next step
# can inspect what a REAL relayed-text firing (peer channel message or
# subagent hand-back) looks like on the wire - nobody has seen the raw
# payload for one yet. Directory overridable for tests; defaults to
# hooks/ itself, NOT hooks/.session-markers/ - write-session-marker.ps1's
# Remove-DeadSessionMarkers deletes any file in that directory with no
# live-session suffix in its name, which matched this capture file's plain
# name and wiped it on the next /commit in any session. hooks/ itself has
# no such pruning, and the dot-prefixed filename is covered by its own
# .gitignore line alongside this hook's other machine-state files
# (.commit-marker*, .push-ok/, etc.).
_CAPTURE_DIR = os.environ.get(
    'CLAUDE_FLAGGED_SKILL_CAPTURE_DIR',
    os.path.dirname(os.path.abspath(__file__)),
)
_CAPTURE_PATH = os.path.join(_CAPTURE_DIR, '.flagged-skill-capture.jsonl')
_CAPTURE_MAX_AGE = datetime.timedelta(days=7)


def _escape_zero_width(text):
    """Keeps an envelope's zero-width markers visible in a log line instead
    of invisible/stripped - the whole point of the capture is to see them."""
    return _ZERO_WIDTH_RE.sub(lambda m: '\\u%04x' % ord(m.group(0)), text)


def _capture_fire(raw_payload, raw_prompt, skill_name):
    """Best-effort instrumentation. Any failure here (bad permissions, a
    blocked path, a malformed existing line) is swallowed - this must never
    change the hook's output or exit code."""
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff = now - _CAPTURE_MAX_AGE

        kept = []
        if os.path.exists(_CAPTURE_PATH):
            with open(_CAPTURE_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ts = datetime.datetime.fromisoformat(json.loads(line)['timestamp_utc'])
                        if ts >= cutoff:
                            kept.append(line)
                    except Exception:
                        continue

        keys = sorted(raw_payload.keys())
        other_fields = {k: repr(raw_payload[k])[:120] for k in keys if k != 'prompt'}
        record = {
            'timestamp_utc': now.isoformat(),
            'payload_keys': keys,
            'other_fields': other_fields,
            'skill': skill_name,
            'prompt_excerpt': _escape_zero_width(raw_prompt[:200]),
        }
        kept.append(json.dumps(record))

        os.makedirs(_CAPTURE_DIR, exist_ok=True)
        with open(_CAPTURE_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(kept) + '\n')
    except Exception:
        pass


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
    # English and fired on ambient text, not real invocation intent. Position
    # in the prompt is not checked (todo 891): mid-line mentions on later
    # lines are real invocations too, e.g. "and then /close up".
    _name_pattern = r'(?<![\w/-])/' + re.escape(name) + r'(?![\w-])'
    if not re.search(_name_pattern, _match_text, re.IGNORECASE):
        continue

    contexts.append(
        'Skill "%s" (disable-model-invocation: true, NOT shown in your Skill tool listing) '
        'appears to have been invoked in this prompt. If this is a genuine request to run it, '
        'read its SKILL.md below and follow it - do not attempt a Skill tool call for it. If '
        'the prompt is quoting or relaying this name rather than asking for the skill (e.g. a '
        'relayed peer message), treat this as informational only.\n\n---\n%s\n---' % (name, content)
    )
    _capture_fire(payload, prompt, name)

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
