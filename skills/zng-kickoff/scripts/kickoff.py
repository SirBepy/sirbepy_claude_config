"""State + fetch helper for /zng-kickoff. Run with `python -I`, set PYTHONIOENCODING=utf-8.

Subcommands:
  leftovers                         unpushed commits, dirty files and todo claims per ZNG repo
  feed [--days N]                   fetch Shortcut activity newer than the last run, print tickets
                                    with activity after their handled mark
  handle <story_id>... [--note T]   mark tickets handled; they resurface only on newer activity
  todos                             per-repo counts, plus todos that are new or changed since triage
  todo-verdict <repo> <file> <urgent|not-urgent> [--reason T]
  tickets                           pickable unstarted FE tickets, minus dismissed-and-unchanged ones
  ticket-dismiss <story_id>... --reason T

State lives in ~/.claude/state/zng-kickoff/ (gitignored, machine-local).
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

PROJECTS = 'C:/Users/tecno/Desktop/Projects'
REPOS = ['zng-app', 'zng-admin', 'zng-api', 'zng-biller']
STATE_DIR = os.path.expanduser('~/.claude/state/zng-kickoff')
ENV_PATH = os.path.expanduser('~/.claude/.env')
# Identity and state ids: ~/.claude/refs/shortcut-api.md
DEV_UUID = '699c76fe-9076-4424-ba22-2bb3534f417e'
DEV_MENTION = 'josipmui'
PICKUP_OWNERS = [DEV_MENTION, 'peter']
UNSTARTED_STATES = {'Backlog', 'To Do'}
OFF_PLATE_STATES = {'Complete', "Won't do", 'Ready for deploy'}
TICKET_MAX_AGE_DAYS = 90
FEED_KEEP_DAYS = 30
API = 'https://api.app.shortcut.com/api/v3'


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def iso(t):
    return t.strftime('%Y-%m-%dT%H:%M:%S.000Z')


def load(name, default):
    path = os.path.join(STATE_DIR, name)
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save(name, data):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = os.path.join(STATE_DIR, name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, os.path.join(STATE_DIR, name))


def env():
    vals = {}
    with open(ENV_PATH, 'rb') as f:
        for line in f.read().decode('utf-8-sig').splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                vals[k.strip().lstrip('\ufeff')] = v.strip()
    return vals


def api_get(path_or_url, token):
    url = path_or_url if path_or_url.startswith('http') else API + path_or_url
    req = urllib.request.Request(url, headers={'Shortcut-Token': token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def state_names(token):
    names = {}
    for w in api_get('/workflows', token):
        for s in w['states']:
            names[s['id']] = s['name'].strip()
    return names


def member_names(token):
    return {m['id']: m['profile'].get('mention_name') for m in api_get('/members', token)}


def git(repo, *args):
    r = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout.strip() if r.returncode == 0 else f'(git error: {r.stderr.strip()[:200]})'


# ---------------------------------------------------------------- leftovers

def cmd_leftovers(_):
    for name in REPOS:
        repo = f'{PROJECTS}/{name}'
        if not os.path.isdir(repo):
            print(f'== {name}: missing')
            continue
        git(repo, 'fetch', '--quiet')
        branch = git(repo, 'rev-parse', '--abbrev-ref', 'HEAD')
        unpushed = git(repo, 'log', '--oneline', '@{u}..HEAD')
        dirty = [l for l in git(repo, 'status', '--porcelain').splitlines() if l.strip()]
        claims = sorted(os.listdir(f'{repo}/.claude/todos/.claims')) if os.path.isdir(f'{repo}/.claude/todos/.claims') else []
        print(f'== {name} ({branch}): {len(dirty)} dirty, {len(claims)} claims')
        for line in unpushed.splitlines():
            print(f'   unpushed {line}')
        for c in claims:
            print(f'   claim {c}')


# ---------------------------------------------------------------- feed

def fetch_page(before, cookie, org, ws):
    req = urllib.request.Request(
        'https://app.shortcut.com/backend/api/private/permission/activity',
        data=json.dumps({'before': before}).encode(),
        headers={'accept': '*/*', 'content-type': 'application/json; charset=UTF-8',
                 'tenant-organization2': org, 'tenant-workspace2': ws,
                 'x-requested-with': 'XMLHttpRequest', 'cookie': cookie},
        method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def story_of(e):
    for a in e.get('actions', []):
        if a.get('entity_type') == 'story':
            return a.get('id'), a.get('name')
    for r in e.get('references', []):
        if r.get('entity_type') == 'story':
            return r.get('id'), r.get('name')
    if isinstance(e.get('primary_id'), int):
        return e['primary_id'], None
    return None, None


def cmd_feed(args):
    vals = env()
    sid = vals.get('SHORTCUT_SID', '')
    cookie = sid if sid.startswith('sid=') else 'sid=' + sid
    org, ws = vals.get('SHORTCUT_TENANT_ORG'), vals.get('SHORTCUT_TENANT_WS')
    feed = load('feed.json', {'high_water': None, 'events': {}, 'handled': {}})
    stop_at = feed['high_water'] or iso(now_utc() - dt.timedelta(days=args.days))
    # The endpoint 400s on a future `before`, so seed a few minutes in the past.
    before = iso(now_utc() - dt.timedelta(minutes=5))
    fetched = 0
    for _ in range(60):
        try:
            page = fetch_page(before, cookie, org, ws)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors='replace')[:300]
            if e.code in (401, 403):
                print('SHORTCUT_SID is dead. Refresh it per /shortcut-priorities "Auth" (DevTools > activity request > Copy as cURL > sid=).')
            else:
                print(f'HTTP {e.code}: {body}')
            sys.exit(1)
        data = page.get('data', [])
        for e in data:
            feed['events'][e['id']] = e
        fetched += len(data)
        start = page.get('start')
        if not start or start <= stop_at:
            break
        before = start
    newest = max((e.get('changed_at') or '' for e in feed['events'].values()), default=feed['high_water'])
    feed['high_water'] = newest
    keep_after = iso(now_utc() - dt.timedelta(days=FEED_KEEP_DAYS))
    feed['events'] = {k: e for k, e in feed['events'].items() if (e.get('changed_at') or '') >= keep_after}
    save('feed.json', feed)

    tickets = {}
    for e in feed['events'].values():
        sid_, name = story_of(e)
        if sid_ is None:
            continue
        t = tickets.setdefault(str(sid_), {'name': name, 'reasons': set(), 'last': '', 'comments': [], 'states': []})
        t['name'] = t['name'] or name
        t['reasons'].update(r.get('reason') for r in (e.get('reasons') or []))
        if e.get('member_id') != DEV_UUID:
            t['last'] = max(t['last'], e.get('changed_at') or '')
        for a in e.get('actions', []):
            if a.get('entity_type') == 'story-comment' and a.get('action') == 'create' and e.get('member_id') != DEV_UUID:
                t['comments'].append((e.get('changed_at'), e.get('actor_name'), DEV_UUID in (a.get('mention_ids') or []),
                                      (a.get('text') or '')[:200].replace('\n', ' ')))
            ws_change = (a.get('changes') or {}).get('workflow_state_id')
            if a.get('entity_type') == 'story' and ws_change:
                t['states'].append((e.get('changed_at'), e.get('actor_name'), ws_change.get('new')))
    print(f'fetched {fetched} events, cache holds {len(feed["events"])}, high water {feed["high_water"]}')
    open_count = 0
    for sid_, t in sorted(tickets.items(), key=lambda x: x[1]['last'], reverse=True):
        if not t['last']:
            continue
        mark = feed['handled'].get(sid_)
        if mark and mark['at'] >= t['last']:
            continue
        noise_only = not t['comments'] and t['reasons'] <= {'follower', 'group-assignment-added', 'group-assignment-removed'}
        if noise_only:
            continue
        open_count += 1
        since = f" (handled {mark['at'][:10]}, new activity since)" if mark else ''
        print(f"\n#{sid_} {t['name']} | reasons={sorted(r for r in t['reasons'] if r)} | last={t['last']}{since}")
        for c in sorted(t['comments'])[-4:]:
            print(f"   C {c[0][:16]} {c[1]}{' @dev' if c[2] else ''}: {c[3]}")
        for s in t['states'][-2:]:
            print(f'   S {s[0][:16]} {s[1]} -> state {s[2]}')
    print(f'\n{open_count} tickets with unhandled activity')


def cmd_handle(args):
    feed = load('feed.json', {'high_water': None, 'events': {}, 'handled': {}})
    for sid_ in args.story_ids:
        feed['handled'][str(sid_)] = {'at': iso(now_utc()), 'note': args.note or ''}
    save('feed.json', feed)
    print(f'handled: {", ".join(args.story_ids)}')


# ---------------------------------------------------------------- todos

def todo_files():
    for name in REPOS:
        for path in sorted(glob.glob(f'{PROJECTS}/{name}/.claude/todos/*.md')):
            base = os.path.basename(path)
            if base == 'PLAN.md':
                continue
            yield name, base, path


def title_of(text):
    for line in text.splitlines():
        if line.startswith('# '):
            return line[2:].strip()
    return '(no title)'


def cmd_todos(_):
    cache = load('todos.json', {})
    counts, fresh, urgent = {}, [], []
    present = set()
    for repo, base, path in todo_files():
        with open(path, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        key = f'{repo}/{base}'
        present.add(key)
        digest = hashlib.sha1(raw).hexdigest()[:12]
        c = counts.setdefault(repo, {'total': 0, 'not-urgent': 0, 'urgent': 0, 'to-triage': 0})
        c['total'] += 1
        hit = cache.get(key)
        if hit and hit['hash'] == digest:
            c[hit['verdict']] += 1
            if hit['verdict'] == 'urgent':
                urgent.append((key, title_of(text), hit.get('reason', '')))
        else:
            c['to-triage'] += 1
            fresh.append((key, title_of(text), path, 'changed' if hit else 'new'))
    # Only a repo whose todos dir is on disk can prove an entry archived; a repo moved or
    # unmounted for a moment keeps its verdicts instead of being re-triaged from scratch.
    readable = {name for name in REPOS if os.path.isdir(f'{PROJECTS}/{name}/.claude/todos')}
    for gone in set(cache) - present:
        if gone.split('/', 1)[0] in readable:
            del cache[gone]
    save('todos.json', cache)
    for repo, c in counts.items():
        print(f"{repo}: {c['total']} todos | {c['not-urgent']} not urgent | {c['urgent']} urgent | {c['to-triage']} to triage")
    for key, title, reason in urgent:
        print(f'URGENT {key}: {title} ({reason})')
    for key, title, path, why in fresh:
        print(f'TRIAGE ({why}) {key}: {title}\n   {path}')


def cmd_todo_verdict(args):
    path = f'{PROJECTS}/{args.repo}/.claude/todos/{args.file}'
    if not os.path.exists(path):
        matches = glob.glob(f'{PROJECTS}/{args.repo}/.claude/todos/{args.file}-*.md')
        if len(matches) != 1:
            print(f'no unique todo for {args.repo}/{args.file}: {matches}')
            sys.exit(1)
        path = matches[0]
    with open(path, 'rb') as f:
        digest = hashlib.sha1(f.read()).hexdigest()[:12]
    cache = load('todos.json', {})
    key = f'{args.repo}/{os.path.basename(path)}'
    cache[key] = {'hash': digest, 'verdict': args.verdict, 'reason': args.reason or '', 'at': iso(now_utc())}
    save('todos.json', cache)
    print(f'{key} -> {args.verdict}')


# ---------------------------------------------------------------- tickets

def search(token, query, cap=100):
    url = f'{API}/search/stories?' + urllib.parse.urlencode({'query': query, 'page_size': 25})
    out = []
    while url and len(out) < cap:
        r = api_get(url, token)
        out += r['data']
        url = ('https://api.app.shortcut.com' + r['next']) if r.get('next') else None
    return out


def cmd_tickets(_):
    token = env()['SHORTCUT_API_TOKEN']
    states, members = state_names(token), member_names(token)
    cutoff = (now_utc() - dt.timedelta(days=TICKET_MAX_AGE_DAYS)).strftime('%Y-%m-%d')
    queries = [f'owner:{o} !is:archived is:unstarted' for o in PICKUP_OWNERS]
    queries += [f'title:{t} !is:archived is:unstarted created:{cutoff}..*' for t in ('FE', '"Web App"', 'Frontend')]
    seen = {}
    for q in queries:
        try:
            for s in search(token, q):
                seen[s['id']] = s
        except urllib.error.HTTPError as e:
            print(f'query failed ({e.code}): {q}')
    dismissed = load('tickets.json', {})
    shown = hidden = 0
    for s in sorted(seen.values(), key=lambda s: s['created_at'], reverse=True):
        if states.get(s['workflow_state_id']) not in UNSTARTED_STATES or s['created_at'][:10] < cutoff:
            continue
        owners = [members.get(o) for o in s['owner_ids']]
        name = s['name']
        if 'Implement BE' in name or name.startswith('BE:'):
            continue
        d = dismissed.get(str(s['id']))
        if d and s['updated_at'] <= d['updated_at']:
            hidden += 1
            continue
        shown += 1
        flag = ' (updated since dismissed)' if d else ''
        print(f"{s['created_at'][:10]} #{s['id']} {states.get(s['workflow_state_id'])} owners={','.join(o or '?' for o in owners) or '-'} est={s.get('estimate')} | {name}{flag}")
    print(f'{shown} to review, {hidden} hidden as dismissed and unchanged')


def cmd_ticket_dismiss(args):
    token = env()['SHORTCUT_API_TOKEN']
    dismissed = load('tickets.json', {})
    for sid_ in args.story_ids:
        s = api_get(f'/stories/{sid_}', token)
        dismissed[str(sid_)] = {'updated_at': s['updated_at'], 'reason': args.reason, 'at': iso(now_utc())}
    save('tickets.json', dismissed)
    print(f'dismissed: {", ".join(args.story_ids)} ({args.reason})')


def utf8_stdout(stream):
    # `python -I` ignores PYTHONIOENCODING, and a piped Windows stdout is cp1250 here, so one
    # arrow or emoji in a comment or ticket title would crash the whole run mid-print.
    stream.reconfigure(encoding='utf-8', errors='replace')


def main():
    utf8_stdout(sys.stdout)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('leftovers').set_defaults(fn=cmd_leftovers)
    f = sub.add_parser('feed')
    f.add_argument('--days', type=int, default=3, help='first-run lookback only')
    f.set_defaults(fn=cmd_feed)
    h = sub.add_parser('handle')
    h.add_argument('story_ids', nargs='+')
    h.add_argument('--note')
    h.set_defaults(fn=cmd_handle)
    sub.add_parser('todos').set_defaults(fn=cmd_todos)
    v = sub.add_parser('todo-verdict')
    v.add_argument('repo', choices=REPOS)
    v.add_argument('file', help='todo filename, or its numeric id')
    v.add_argument('verdict', choices=['urgent', 'not-urgent'])
    v.add_argument('--reason')
    v.set_defaults(fn=cmd_todo_verdict)
    sub.add_parser('tickets').set_defaults(fn=cmd_tickets)
    d = sub.add_parser('ticket-dismiss')
    d.add_argument('story_ids', nargs='+')
    d.add_argument('--reason', required=True)
    d.set_defaults(fn=cmd_ticket_dismiss)
    args = p.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
