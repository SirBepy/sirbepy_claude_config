#!/usr/bin/env bash
# SessionStart-style hook (registration is a separate step; this file is not
# wired into settings.json yet). Warns when the Flutter repo in the current
# working dir is pinned behind the latest published stable release.
#
# Fast exit unless the cwd (or CLAUDE_PROJECT_DIR) is a Flutter repo pinning
# via a flutter.version file. Network is throttled to once per 24h via a
# cache file so this never adds latency to most session starts. Any failure
# (no network, bad JSON, missing python) is swallowed - this must never
# block a session start. Always exits 0.

repo_dir="${CLAUDE_PROJECT_DIR:-$PWD}"
version_file="$repo_dir/flutter.version"

[ -f "$version_file" ] || exit 0

pinned=$(cat "$version_file" 2>/dev/null)
[ -n "$pinned" ] || exit 0

CACHE_DIR="${HOME}/.claude/.cache"
CACHE_FILE="$CACHE_DIR/flutter-version-check.json"
RELEASES_URL="https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json"

mkdir -p "$CACHE_DIR" 2>/dev/null

# python.exe is a native Windows build and does not understand posix-style
# (/c/...) paths, so convert before handing paths to `python -c`. If cygpath
# is unavailable, caching is best-effort skipped rather than failing loudly.
CACHE_FILE_WIN=$(cygpath -w "$CACHE_FILE" 2>/dev/null)

now_epoch=$(date +%s)
cached_ts=0
cached_stable=""

if [ -n "$CACHE_FILE_WIN" ] && [ -f "$CACHE_FILE" ]; then
  cache_read=$(python -c "
import json
try:
    d = json.load(open(r'$CACHE_FILE_WIN', encoding='utf-8'))
    print(d.get('checked_at', 0))
    print(d.get('stable', ''))
except Exception:
    print(0)
    print('')
" 2>/dev/null)
  cached_ts=$(printf '%s\n' "$cache_read" | sed -n 1p)
  cached_stable=$(printf '%s\n' "$cache_read" | sed -n 2p)
fi

[ -n "$cached_ts" ] || cached_ts=0
age=$(( now_epoch - cached_ts ))

# Only hit the network if the cache is missing/stale (24h throttle).
if [ -z "$cached_stable" ] || [ "$age" -ge 86400 ]; then
  fetched=$(curl -s --connect-timeout 3 --max-time 6 "$RELEASES_URL" 2>/dev/null)
  if [ -n "$fetched" ]; then
    latest=$(printf '%s' "$fetched" | python -c "
import json, sys
try:
    d = json.load(sys.stdin)
    stable_hash = d['current_release']['stable']
    for r in d['releases']:
        if r.get('hash') == stable_hash:
            print(r['version'])
            break
except Exception:
    pass
" 2>/dev/null)
    if [ -n "$latest" ]; then
      cached_stable="$latest"
      if [ -n "$CACHE_FILE_WIN" ]; then
        python -c "
import json
json.dump({'checked_at': $now_epoch, 'stable': '$latest'}, open(r'$CACHE_FILE_WIN', 'w', encoding='utf-8'))
" 2>/dev/null
      fi
    fi
  fi
fi

[ -n "$cached_stable" ] || exit 0
[ "$cached_stable" = "$pinned" ] && exit 0

newer=$(python -c "
def parse(v):
    return tuple(int(x) for x in v.strip().split('.'))
try:
    print('yes' if parse('$cached_stable') > parse('$pinned') else 'no')
except Exception:
    print('no')
" 2>/dev/null)

[ "$newer" = "yes" ] || exit 0

echo "Flutter stable $cached_stable available (repo pinned at $pinned). Run /flutter-bump."
exit 0
