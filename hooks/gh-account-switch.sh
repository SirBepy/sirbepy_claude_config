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
remote=$(git remote get-url origin 2>/dev/null)
if [ -n "$remote" ]; then
  case "$remote" in
    *zirtue-corp/*) acct=JosipMuzicZirtue ;;
    *Fibo-Studio/*) acct=JosipMuzicFibo ;;
    *revaire*) acct=josipmuzic ;;
    *) acct=SirBepy ;;
  esac
else
  # No origin to resolve an owner from (todo 1069: `gh repo create` right after
  # `git init`, before any origin exists, used to fall through with no account
  # decision at all and inherit whatever work account happened to be active -
  # a personal repo was created under JosipMuzicZirtue). `gh repo create` is the
  # only no-origin command that still needs a decision: it names its own future
  # owner as an OWNER/NAME argument when one is given, so that is checked
  # against the same mapping before defaulting to the personal account.
  # Anything else with no origin has nothing to infer an owner from, so the
  # active account is left alone rather than guessed at.
  case "$cmd" in
    *"repo create"*)
      # A value-taking flag before OWNER/NAME (`--source .`) must skip its value
      # too, or the value is read as the name and the real owner is missed.
      owner=$(printf '%s' "$cmd" | python -c "import sys,shlex
value_flags = {'-d', '--description', '-h', '--homepage', '-t', '--team', '-l', '--license',
               '-g', '--gitignore', '-s', '--source', '-r', '--remote', '-p', '--template'}
toks = shlex.split(sys.stdin.read())
for i, t in enumerate(toks):
    if t == 'create' and i > 0 and toks[i-1] == 'repo':
        j = i + 1
        while j < len(toks) and toks[j].startswith('-'):
            j += 2 if toks[j] in value_flags else 1
        if j < len(toks) and '/' in toks[j]:
            print(toks[j].split('/', 1)[0])
        break
" 2>/dev/null)
      case "$owner" in
        zirtue-corp) acct=JosipMuzicZirtue ;;
        Fibo-Studio) acct=JosipMuzicFibo ;;
        revaire) acct=josipmuzic ;;
        *) acct=SirBepy ;;
      esac
      ;;
    *) exit 0 ;;
  esac
fi
active=$(gh auth status 2>/dev/null | awk '/Logged in to github.com account/{for(i=1;i<=NF;i++)if($i=="account")n=$(i+1)} /Active account: true/{print n; exit}')
[ "$active" = "$acct" ] && exit 0
gh auth switch --user "$acct" >/dev/null 2>&1
exit 0
