#!/bin/sh
# Mac/Linux port of rename-session.ps1
# Usage: rename-session.sh --name "Session name" [--close]
#        rename-session.sh --get-id

NAME=""
CLOSE=0
GET_ID=0

while [ $# -gt 0 ]; do
    case "$1" in
        --name|-n) NAME="$2"; shift; shift ;;
        --close)   CLOSE=1; shift ;;
        --get-id)  GET_ID=1; shift ;;
        *) echo "Unknown arg: $1" >&2; exit 1 ;;
    esac
done

CLAUDE_ROOT="$HOME/.claude"
SESSIONS_DIR="$CLAUDE_ROOT/sessions"
PROJECTS_DIR="$CLAUDE_ROOT/projects"

if [ ! -d "$SESSIONS_DIR" ]; then
    echo "Sessions dir not found: $SESSIONS_DIR" >&2
    exit 1
fi

# Walk up the process tree from $$ to find the claude ancestor PID.
# Fallback only, best-effort/unstable (todo 60) - used when CLAUDE_CODE_SESSION_ID is unset.
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

# Resolves this session's record as "pid<TAB>sessionId<TAB>procStart". sessionId match against
# $CLAUDE_CODE_SESSION_ID is authoritative and stable; the pid-walk only runs when it's unset.
resolve_session_record() {
    python3 -c "
import json, os, sys

sessions_dir, sid, fallback_pid = sys.argv[1], sys.argv[2], sys.argv[3]

def emit(d):
    print(f\"{d.get('pid','')}\t{d.get('sessionId','')}\t{d.get('procStart','')}\")

if sid:
    for fname in os.listdir(sessions_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(sessions_dir, fname)) as fh:
                d = json.load(fh)
            if d.get('sessionId') == sid:
                emit(d)
                sys.exit(0)
        except Exception:
            pass

if fallback_pid:
    best = None
    for fname in os.listdir(sessions_dir):
        if not fname.endswith('.json'):
            continue
        try:
            with open(os.path.join(sessions_dir, fname)) as fh:
                d = json.load(fh)
            if str(d.get('pid', '')) == fallback_pid:
                upd = d.get('updatedAt', '')
                if best is None or upd > best[0]:
                    best = (upd, d)
        except Exception:
            pass
    if best:
        emit(best[1])
" "$SESSIONS_DIR" "${CLAUDE_CODE_SESSION_ID:-}" "$1"
}

FALLBACK_PID=""
if [ -z "$CLAUDE_CODE_SESSION_ID" ]; then
    FALLBACK_PID=$(find_claude_pid)
fi

RECORD=$(resolve_session_record "$FALLBACK_PID")
if [ -z "$RECORD" ]; then
    echo "Could not resolve this session's own record (sessionId env var unset and pid-walk fallback failed)." >&2
    exit 1
fi

SESSION_PID=$(printf '%s' "$RECORD" | cut -f1)
SESSION_ID=$(printf '%s' "$RECORD" | cut -f2)
PROC_START=$(printf '%s' "$RECORD" | cut -f3)

if [ "$GET_ID" = "1" ]; then
    if [ -z "$PROC_START" ]; then
        # Older session json with no procStart - derive it from the already-known pid, no walk needed.
        PROC_START=$(ps -p "$SESSION_PID" -o lstart= 2>/dev/null | tr -s ' ' | tr ' ' '_')
    fi
    echo "$SESSION_PID-$PROC_START"
    exit 0
fi

if [ -n "$NAME" ]; then
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

    echo "Renamed session $SESSION_ID (pid $SESSION_PID) to '$NAME'"
    echo "  jsonl: $JSONL_PATH"
fi

if [ "$CLOSE" = "1" ]; then
    (sleep 0.8 && kill "$SESSION_PID" 2>/dev/null) &
    echo "Scheduled kill of claude pid $SESSION_PID in 800ms."
fi
