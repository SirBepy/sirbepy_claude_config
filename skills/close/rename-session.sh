#!/bin/sh
# Mac/Linux port of rename-session.ps1
# Usage: rename-session.sh --name "Session name" [--close]

NAME=""
CLOSE=0

while [ $# -gt 0 ]; do
    case "$1" in
        --name|-n) NAME="$2"; shift; shift ;;
        --close)   CLOSE=1; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

if [ -z "$NAME" ]; then
    echo "Usage: $0 --name <name> [--close]" >&2
    exit 1
fi

CLAUDE_ROOT="$HOME/.claude"
SESSIONS_DIR="$CLAUDE_ROOT/sessions"
PROJECTS_DIR="$CLAUDE_ROOT/projects"

if [ ! -d "$SESSIONS_DIR" ]; then
    echo "Sessions dir not found: $SESSIONS_DIR" >&2
    exit 1
fi

# Walk up the process tree from $$ to find the claude ancestor PID.
find_claude_pid() {
    p=$$
    count=0
    while [ "$count" -lt 8 ]; do
        name=$(ps -p "$p" -o comm= 2>/dev/null | tr -d ' ')
        case "$name" in
            *claude*) echo "$p"; return 0 ;;
        esac
        parent=$(ps -p "$p" -o ppid= 2>/dev/null | tr -d ' ')
        if [ -z "$parent" ] || [ "$parent" = "0" ] || [ "$parent" = "$p" ]; then
            break
        fi
        p="$parent"
        count=$((count + 1))
    done
    return 1
}

CLAUDE_PID=$(find_claude_pid)
if [ -z "$CLAUDE_PID" ]; then
    echo "Could not find claude ancestor process from PID $$" >&2
    exit 1
fi

# Find session JSON with matching PID; pick latest updatedAt if multiple.
SESSION_ID=$(python3 -c "
import json, os, sys

sessions_dir = sys.argv[1]
target_pid   = sys.argv[2]

best = None
for fname in os.listdir(sessions_dir):
    if not fname.endswith('.json'):
        continue
    path = os.path.join(sessions_dir, fname)
    try:
        with open(path) as fh:
            d = json.load(fh)
        if str(d.get('pid', '')) == target_pid:
            upd = d.get('updatedAt', '')
            if best is None or upd > best[0]:
                best = (upd, d.get('sessionId', ''))
    except Exception:
        pass

if best:
    print(best[1])
" "$SESSIONS_DIR" "$CLAUDE_PID")

if [ -z "$SESSION_ID" ]; then
    echo "No session found matching claude pid $CLAUDE_PID" >&2
    exit 1
fi

JSONL_PATH=$(find "$PROJECTS_DIR" -name "${SESSION_ID}.jsonl" 2>/dev/null | head -1)
if [ -z "$JSONL_PATH" ]; then
    echo "Session jsonl not found for sessionId '$SESSION_ID'" >&2
    exit 1
fi

# Append the two records the harness recognizes as a session rename.
python3 -c "
import json, sys

path, sid, name = sys.argv[1], sys.argv[2], sys.argv[3]
records = [
    json.dumps({'type': 'custom-title', 'customTitle': name, 'sessionId': sid}),
    json.dumps({'type': 'agent-name',   'agentName':   name, 'sessionId': sid}),
]
with open(path, 'a', encoding='utf-8') as f:
    for r in records:
        f.write(r + '\n')
" "$JSONL_PATH" "$SESSION_ID" "$NAME"

echo "Renamed session $SESSION_ID (claude pid $CLAUDE_PID) to '$NAME'"
echo "  jsonl: $JSONL_PATH"

if [ "$CLOSE" = "1" ]; then
    (sleep 0.8 && kill "$CLAUDE_PID" 2>/dev/null) &
    echo "Scheduled kill of claude pid $CLAUDE_PID in 800ms."
fi
