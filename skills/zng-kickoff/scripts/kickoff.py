"""State + fetch helper for /zng-kickoff. Run with `python -I`; it sets its own UTF-8 stdout.

Subcommands:
  leftovers                         unpushed commits, dirty files and todo claims per ZNG repo, then
                                    the unsent drafts every chat in the project left
  drafts                            just the unsent-drafts part of leftovers
  feed [--days N]                   fetch Shortcut activity newer than the last run, print tickets
                                    with activity after their handled mark
  handle <story_id>... [--note T]   mark tickets handled; they resurface only on newer activity
  todos                             per-repo counts, plus todos that are new or changed since triage
  todo-verdict <repo> <file> <urgent|not-urgent> [--reason T]
  tickets                           pickable unstarted FE tickets, minus dismissed-and-unchanged ones
  ticket-dismiss <story_id>... --reason T
  story <story_id>...               read-only: print each ticket with named state, owners, requester,
                                    epic, links, description and every comment with author and date

State lives in ~/.claude/state/zng-kickoff/ (gitignored, machine-local).
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
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
FEED_MAX_PAGES = 60
DIRTY_LIST_CAP = 20
# `title:FE` is a fuzzy substring match (it also hits "feedback"), so names are re-checked locally.
DRAFTS_MAX_LISTED = 25
# Shortcut ids are 5 digits; a 4-digit run in a topic is far more likely a year or a count.
TICKET_ID = re.compile(r'(?<![\w-])(?:sc-?)?(\d{5,})(?!\w)', re.I)
ZNG_DRAFT = re.compile(r'\bsc-?\d{5,}\b|zng', re.I)
FE_TITLE = re.compile(r'\bFE\b|(?i:\bWeb App\b|\bFrontend\b)')
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


def unquote(v):
    # A quoted .env value (SHORTCUT_API_TOKEN="...") would otherwise be sent with the quotes and 401.
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
        return v[1:-1]
    return v


def env():
    vals = {}
    with open(ENV_PATH, 'rb') as f:
        for line in f.read().decode('utf-8-sig').splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                vals[k.strip().lstrip('\ufeff')] = unquote(v.strip())
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


def git_try(repo, *args):
    """(ok, text): text is stdout on success and trimmed stderr on failure."""
    r = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return (True, r.stdout.strip()) if r.returncode == 0 else (False, r.stderr.strip()[:200])


# ---------------------------------------------------------------- leftovers

def cmd_leftovers(_):
    for name in REPOS:
        repo = f'{PROJECTS}/{name}'
        if not os.path.isdir(repo):
            print(f'== {name}: missing')
            continue
        fetched, fetch_err = git_try(repo, 'fetch', '--quiet')
        _, branch = git_try(repo, 'rev-parse', '--abbrev-ref', 'HEAD')
        has_upstream, _ = git_try(repo, 'rev-parse', '--verify', '--quiet', '@{u}')
        ok, status = git_try(repo, 'status', '--porcelain')
        dirty = [l for l in status.splitlines() if l.strip()] if ok else []
        claims = sorted(os.listdir(f'{repo}/.claude/todos/.claims')) if os.path.isdir(f'{repo}/.claude/todos/.claims') else []
        print(f'== {name} ({branch}): {len(dirty)} dirty, {len(claims)} claims')
        if not fetched:
            print(f'   fetch failed, remote state may be stale: {fetch_err}')
        if not ok:
            print(f'   status failed: {status}')
        for line in dirty[:DIRTY_LIST_CAP]:
            print(f'   dirty {line}')
        if len(dirty) > DIRTY_LIST_CAP:
            print(f'   ... {len(dirty) - DIRTY_LIST_CAP} more dirty')
        if has_upstream:
            ok, unpushed = git_try(repo, 'log', '--oneline', '@{u}..HEAD')
            if not ok:
                print(f'   unpushed check failed: {unpushed}')
            for line in unpushed.splitlines() if ok else []:
                print(f'   unpushed {line}')
        else:
            # Without an upstream, "not on any remote" is the closest honest meaning of unpushed.
            ok, count = git_try(repo, 'rev-list', '--count', 'HEAD', '--not', '--remotes')
            print(f'   no upstream, {count} local commits not on any remote' if ok else '   no upstream')
        for c in claims:
            print(f'   claim {c}')
    print()
    cmd_drafts(_)


# ---------------------------------------------------------------- drafts

def drafts_dir():
    # Conductor's own rule (settings/paths.rs): a non-empty CC_DATA_DIR replaces %APPDATA%\claude-conductor.
    base = os.environ.get('CC_DATA_DIR') or os.path.join(os.environ.get('APPDATA', ''), 'claude-conductor')
    return os.path.join(base, 'message-drafts')


def draft_ticket_ids(text):
    return set(TICKET_ID.findall(text))


def is_open_draft(d):
    # Copied and archived are the app's "dealt with" states; a card whose every variant Claude posted is done too.
    if d.get('state', 'needs-you') != 'needs-you':
        return False
    variants = [v for v in d.get('variants', []) if isinstance(v, dict)]
    return not (variants and all(v.get('sent') for v in variants))


def open_zng_drafts():
    """(drafts, note). One store file per Conductor project and the file name is an opaque id, so a
    store counts as ZNG's when any of its drafts names an sc-id or zng. Never reads draft bodies."""
    path = drafts_dir()
    if not os.path.isdir(path):
        return [], f'no drafts store at {path}'
    found, skipped = [], 0
    for name in sorted(os.listdir(path)):
        if not name.endswith('.json'):
            continue
        try:
            with open(os.path.join(path, name), encoding='utf-8') as f:
                store = json.load(f)
            raw = [d for d in store['drafts'] if isinstance(d, dict) and isinstance(d.get('topic'), str)]
        except (OSError, ValueError, KeyError, TypeError):
            skipped += 1
            continue
        if not any(ZNG_DRAFT.search(d['topic'] + str(d.get('brief', ''))) for d in raw):
            continue
        for d in raw:
            if is_open_draft(d):
                found.append({'topic': d['topic'], 'origin': ' '.join(str(d.get('origin_label', '')).split())[:60],
                              'updated': str(d.get('updated_at', ''))})
    found.sort(key=lambda d: d['updated'], reverse=True)
    return found, (f'{skipped} store file(s) unreadable or in an unknown format' if skipped else '')


def when(updated):
    return updated[:16].replace('T', ' ')


def cmd_drafts(_):
    found, note = open_zng_drafts()
    print(f'== unsent drafts (all chats in the project): {len(found)}')
    if note:
        print(f'   {note}')
    for d in found[:DRAFTS_MAX_LISTED]:
        print(f"   draft {when(d['updated'])} | {d['topic']} | from: {d['origin']}")
    if len(found) > DRAFTS_MAX_LISTED:
        print(f'   ... {len(found) - DRAFTS_MAX_LISTED} older drafts')


# ---------------------------------------------------------------- feed

# The trimmed header set can get `401 profile_invalid` for a valid cookie; the full browser set
# (same shape as /shortcut-priorities Step 1) is the fallback before the cookie is called dead.
BROWSER_HEADERS = {
    'origin': 'https://app.shortcut.com',
    'referer': 'https://app.shortcut.com/zirtue/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'clubhouse-page': 'stories', 'shortcut-action-context': 'stories',
}


def fetch_page(before, cookie, org, ws, full=False):
    headers = {'accept': '*/*', 'content-type': 'application/json; charset=UTF-8',
               'tenant-organization2': org, 'tenant-workspace2': ws,
               'x-requested-with': 'XMLHttpRequest', 'cookie': cookie}
    if full:
        headers.update(BROWSER_HEADERS)
    req = urllib.request.Request(
        'https://app.shortcut.com/backend/api/private/permission/activity',
        data=json.dumps({'before': before}).encode(), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_page_auth(before, cookie, org, ws, mode):
    """Trimmed headers first; the first 401/403 retries once with the full set, and a success
    keeps the full set (mode['full']) for the remaining pages."""
    try:
        return fetch_page(before, cookie, org, ws, mode['full'])
    except urllib.error.HTTPError as e:
        if e.code not in (401, 403) or mode['full']:
            raise
    mode['full'] = True
    return fetch_page(before, cookie, org, ws, True)


def collect_events(fetch, events, stop_at, before, max_pages=FEED_MAX_PAGES):
    """Pages backwards from `before` into `events`. Returns (fetched, reached): reached is False
    when the page cap ended the walk before it got down to `stop_at`, so older events remain."""
    fetched = 0
    for _ in range(max_pages):
        page = fetch(before)
        data = page.get('data', [])
        for e in data:
            events[e['id']] = e
        fetched += len(data)
        start = page.get('start')
        if not start or start <= stop_at:
            return fetched, True
        before = start
    return fetched, False


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


def aggregate_tickets(events):
    """Per-ticket activity from feed events. Dev-authored events never count as activity."""
    tickets = {}
    for e in events:
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
    return tickets


def is_noise_only(t):
    return not t['comments'] and t['reasons'] <= {'follower', 'group-assignment-added', 'group-assignment-removed'}


def cmd_feed(args):
    vals = env()
    sid = vals.get('SHORTCUT_SID', '')
    cookie = sid if sid.startswith('sid=') else 'sid=' + sid
    org, ws = vals.get('SHORTCUT_TENANT_ORG'), vals.get('SHORTCUT_TENANT_WS')
    feed = load('feed.json', {'high_water': None, 'events': {}, 'handled': {}})
    stop_at = feed['high_water'] or iso(now_utc() - dt.timedelta(days=args.days))
    # The endpoint 400s on a future `before`, so seed a few minutes in the past.
    before = iso(now_utc() - dt.timedelta(minutes=5))
    mode = {'full': False}
    try:
        fetched, reached = collect_events(lambda b: fetch_page_auth(b, cookie, org, ws, mode), feed['events'], stop_at, before)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')[:300]
        if e.code in (401, 403):
            print('SHORTCUT_SID is dead. Refresh it per /shortcut-priorities "Auth" (DevTools > activity request > Copy as cURL > sid=).')
        else:
            print(f'HTTP {e.code}: {body}')
        sys.exit(1)
    if reached:
        feed['high_water'] = max((e.get('changed_at') or '' for e in feed['events'].values()), default=feed['high_water'])
    else:
        # Advancing the mark past the unfetched gap would hide those events for good.
        print(f'WARNING: hit the {FEED_MAX_PAGES}-page cap before reaching {stop_at}; high water not advanced, run feed again for the rest.')
    keep_after = iso(now_utc() - dt.timedelta(days=FEED_KEEP_DAYS))
    feed['events'] = {k: e for k, e in feed['events'].items() if (e.get('changed_at') or '') >= keep_after}
    save('feed.json', feed)

    tickets = aggregate_tickets(feed['events'].values())
    print(f'fetched {fetched} events, cache holds {len(feed["events"])}, high water {feed["high_water"]}')
    by_ticket = {}
    for d in open_zng_drafts()[0]:
        for tid in draft_ticket_ids(d['topic']):
            by_ticket.setdefault(tid, []).append(d)
    open_count = 0
    for sid_, t in sorted(tickets.items(), key=lambda x: x[1]['last'], reverse=True):
        if not t['last']:
            continue
        mark = feed['handled'].get(sid_)
        if mark and mark['at'] >= t['last']:
            continue
        if is_noise_only(t):
            continue
        open_count += 1
        since = f" (handled {mark['at'][:10]}, new activity since)" if mark else ''
        print(f"\n#{sid_} {t['name']} | reasons={sorted(r for r in t['reasons'] if r)} | last={t['last']}{since}")
        for d in by_ticket.get(sid_, []):
            print(f"   DRAFT EXISTS: post it, do not redraft | {when(d['updated'])} | {d['topic']} | from: {d['origin']}")
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
    seen, owner_hits = {}, set()
    for i, q in enumerate(queries):
        try:
            for s in search(token, q):
                seen[s['id']] = s
                if i < len(PICKUP_OWNERS):
                    owner_hits.add(s['id'])
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
        if s['id'] not in owner_hits and not FE_TITLE.search(name):
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


# ---------------------------------------------------------------- story

STORY_DESC_MAX = 1500
STORY_COMMENT_MAX = 1200


def clip(text, cap):
    text = (text or '').strip()
    return text if len(text) <= cap else text[:cap] + f' ...[+{len(text) - cap} chars]'


def indent(text):
    return '\n'.join('      ' + l for l in text.splitlines()) or '      -'


def epic_name(token, epic_id):
    if not epic_id:
        return '-'
    try:
        return f"{api_get(f'/epics/{epic_id}', token).get('name', '?')} (epic {epic_id})"
    except urllib.error.HTTPError:
        return f'epic {epic_id}'


def print_story(s, states, members, epic):
    who = lambda ids: ', '.join(members.get(i) or '?' for i in ids) or '-'
    print(f"#{s['id']} {s['name']}")
    print(f"   state: {states.get(s['workflow_state_id'], s['workflow_state_id'])} | owners: {who(s.get('owner_ids') or [])} | "
          f"requester: {members.get(s.get('requested_by_id')) or '?'} | est: {s.get('estimate')}")
    print(f"   epic: {epic} | created {(s.get('created_at') or '')[:10]} | updated {(s.get('updated_at') or '')[:10]}")
    print(f"   blocked: {bool(s.get('blocked'))} | blocker: {bool(s.get('blocker'))}")
    for l in s.get('story_links') or []:
        print(f"   link: #{l.get('subject_id')} {l.get('verb')} #{l.get('object_id')}")
    print('   description:')
    print(indent(clip(s.get('description'), STORY_DESC_MAX)))
    comments = sorted((c for c in s.get('comments') or [] if not c.get('deleted')), key=lambda c: c.get('created_at') or '')
    print(f'   comments: {len(comments)}')
    for c in comments:
        print(f"   C {(c.get('created_at') or '')[:16].replace('T', ' ')} {members.get(c.get('author_id')) or '?'}:")
        print(indent(clip(c.get('text'), STORY_COMMENT_MAX)))


def cmd_story(args):
    bad = [i for i in args.story_ids if not i.isdigit()]
    if bad:
        print(f'story ids are digits only, got: {", ".join(bad)}')
        sys.exit(1)
    token = env()['SHORTCUT_API_TOKEN']
    states, members = state_names(token), member_names(token)
    failed = False
    for sid_ in args.story_ids:
        try:
            s = api_get(f'/stories/{sid_}', token)
        except urllib.error.HTTPError as e:
            print(f'#{sid_}: HTTP {e.code}')
            failed = True
            continue
        print_story(s, states, members, epic_name(token, s.get('epic_id')))
        print()
    if failed:
        sys.exit(1)


def utf8_stdout(stream):
    # `python -I` ignores PYTHONIOENCODING, and a piped Windows stdout is cp1250 here, so one
    # arrow or emoji in a comment or ticket title would crash the whole run mid-print.
    stream.reconfigure(encoding='utf-8', errors='replace')


def main():
    utf8_stdout(sys.stdout)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('leftovers').set_defaults(fn=cmd_leftovers)
    sub.add_parser('drafts').set_defaults(fn=cmd_drafts)
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
    st = sub.add_parser('story')
    st.add_argument('story_ids', nargs='+')
    st.set_defaults(fn=cmd_story)
    d =sub.add_parser('ticket-dismiss')
    d.add_argument('story_ids', nargs='+')
    d.add_argument('--reason', required=True)
    d.set_defaults(fn=cmd_ticket_dismiss)
    args = p.parse_args()
    args.fn(args)


if __name__ == '__main__':
    main()
