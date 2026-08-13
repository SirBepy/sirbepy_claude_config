#!/usr/bin/env bash
# PreToolUse hook: keep gh's active account in sync with the repo being operated on.
# Fires on every Bash/PowerShell tool call, but only acts when the command invokes
# `gh`. Resolves the right account from the origin remote owner and switches if the
# active gh account does not already match. Always exits 0 so it never blocks a tool.
# Mapping: zirtue-corp -> JosipMuzicZirtue, Fibo-Studio -> JosipMuzicFibo,
#          revaire -> josipmuzic, everything else -> SirBepy.
input=$(cat)
cmd=$(printf '%s' "$input" | python -c "import sys,json;
try: print(json.load(sys.stdin).get('tool_input',{}).get('command',''))
except Exception: print('')" 2>/dev/null)
# Only act when 'gh' appears as a standalone token in the command.
printf '%s' "$cmd" | grep -Eq '(^|[^[:alnum:]])gh([[:space:]]|$)' || exit 0
remote=$(git remote get-url origin 2>/dev/null) || exit 0
case "$remote" in
  *zirtue-corp/*) acct=JosipMuzicZirtue ;;
  *Fibo-Studio/*) acct=JosipMuzicFibo ;;
  *revaire*) acct=josipmuzic ;;
  *) acct=SirBepy ;;
esac
active=$(gh auth status 2>/dev/null | awk '/Logged in to github.com account/{for(i=1;i<=NF;i++)if($i=="account")n=$(i+1)} /Active account: true/{print n; exit}')
[ "$active" = "$acct" ] && exit 0
gh auth switch --user "$acct" >/dev/null 2>&1
exit 0
