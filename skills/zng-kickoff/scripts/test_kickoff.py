import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
import urllib.error
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kickoff  # noqa: E402


def run(fn, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(types.SimpleNamespace(**kw))
    return out.getvalue()


class StoryOf(unittest.TestCase):
    def test_prefers_story_action_over_reference(self):
        e = {'actions': [{'entity_type': 'story', 'id': 1, 'name': 'A'}],
             'references': [{'entity_type': 'story', 'id': 2, 'name': 'B'}]}
        self.assertEqual(kickoff.story_of(e), (1, 'A'))

    def test_falls_back_to_int_primary_id(self):
        self.assertEqual(kickoff.story_of({'primary_id': 7}), (7, None))

    def test_unresolvable_event(self):
        self.assertEqual(kickoff.story_of({'primary_id': 'x'}), (None, None))


class TodoCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.todos = os.path.join(root, 'projects', 'zng-app', '.claude', 'todos')
        os.makedirs(self.todos)
        self.orig = (kickoff.PROJECTS, kickoff.REPOS, kickoff.STATE_DIR)
        kickoff.PROJECTS = os.path.join(root, 'projects')
        kickoff.REPOS = ['zng-app']
        kickoff.STATE_DIR = os.path.join(root, 'state')
        self.write('12-thing.md', '# 12 - A thing\nbody\n')
        self.write('PLAN.md', '# Plan\n')

    def tearDown(self):
        kickoff.PROJECTS, kickoff.REPOS, kickoff.STATE_DIR = self.orig
        self.tmp.cleanup()

    def write(self, name, text):
        with open(os.path.join(self.todos, name), 'w', encoding='utf-8') as f:
            f.write(text)

    def test_new_todo_needs_triage_and_plan_is_skipped(self):
        out = run(kickoff.cmd_todos)
        self.assertIn('1 todos | 0 not urgent | 0 urgent | 1 to triage', out)
        self.assertIn('TRIAGE (new) zng-app/12-thing.md', out)

    def test_verdict_sticks_until_the_file_changes(self):
        run(kickoff.cmd_todo_verdict, repo='zng-app', file='12', verdict='not-urgent', reason='old')
        self.assertIn('1 not urgent | 0 urgent | 0 to triage', run(kickoff.cmd_todos))
        self.write('12-thing.md', '# 12 - A thing\nbody, now with a met precondition\n')
        self.assertIn('TRIAGE (changed) zng-app/12-thing.md', run(kickoff.cmd_todos))

    def test_archived_todo_drops_out_of_the_cache(self):
        run(kickoff.cmd_todo_verdict, repo='zng-app', file='12', verdict='urgent', reason='now')
        os.remove(os.path.join(self.todos, '12-thing.md'))
        run(kickoff.cmd_todos)
        self.assertEqual(kickoff.load('todos.json', {}), {})

    def test_a_missing_repo_keeps_its_cached_verdicts(self):
        run(kickoff.cmd_todo_verdict, repo='zng-app', file='12', verdict='urgent', reason='now')
        kickoff.REPOS = ['zng-app', 'zng-api']
        cache = kickoff.load('todos.json', {})
        cache['zng-api/3-other.md'] = {'hash': 'abc', 'verdict': 'not-urgent'}
        kickoff.save('todos.json', cache)
        run(kickoff.cmd_todos)
        self.assertIn('zng-api/3-other.md', kickoff.load('todos.json', {}))

    def test_stdout_is_utf8_so_a_non_cp1250_title_prints(self):
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding='cp1250')
        kickoff.utf8_stdout(stream)
        stream.write('ticket → \U0001f600\n')
        stream.flush()
        self.assertIn('→'.encode('utf-8'), raw.getvalue())


class HandledMarks(unittest.TestCase):
    def test_handle_records_a_mark_per_story(self):
        with tempfile.TemporaryDirectory() as root:
            orig = kickoff.STATE_DIR
            kickoff.STATE_DIR = root
            try:
                run(kickoff.cmd_handle, story_ids=['56481', '56423'], note='answered')
                handled = kickoff.load('feed.json', {})['handled']
                self.assertEqual(sorted(handled), ['56423', '56481'])
                self.assertEqual(handled['56481']['note'], 'answered')
            finally:
                kickoff.STATE_DIR = orig


def http_error(code):
    return urllib.error.HTTPError('https://x', code, 'err', {}, io.BytesIO(b'{}'))


class FakeResponse(io.BytesIO):
    pass


class StateDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = kickoff.STATE_DIR
        kickoff.STATE_DIR = self.tmp.name

    def tearDown(self):
        kickoff.STATE_DIR = self.orig
        self.tmp.cleanup()


class EnvQuotes(unittest.TestCase):
    def test_surrounding_quotes_are_stripped(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, '.env')
            with open(path, 'w', encoding='utf-8') as f:
                f.write('QUOTED_VALUE="abc-123"\nSHORTCUT_SID=\'sid=xyz\'\nPLAIN=ok\nODD="half\n')
            orig, kickoff.ENV_PATH = kickoff.ENV_PATH, path
            try:
                vals = kickoff.env()
            finally:
                kickoff.ENV_PATH = orig
        self.assertEqual(vals['QUOTED_VALUE'], 'abc-123')
        self.assertEqual(vals['SHORTCUT_SID'], 'sid=xyz')
        self.assertEqual(vals['PLAIN'], 'ok')
        self.assertEqual(vals['ODD'], '"half')


class FeedAuthRetry(StateDirCase):
    def setUp(self):
        super().setUp()
        self.seen = []

    def urlopen(self, *statuses):
        queue = list(statuses)

        def fake(req, timeout=None):
            self.seen.append(req.get_header('User-agent'))
            status = queue.pop(0)
            if status != 200:
                raise http_error(status)
            return FakeResponse(b'{"data": [], "start": null}')
        return mock.patch.object(kickoff.urllib.request, 'urlopen', fake)

    def feed(self):
        self.out = io.StringIO()
        env = {'SHORTCUT_SID': 'abc', 'SHORTCUT_TENANT_ORG': 'o', 'SHORTCUT_TENANT_WS': 'w'}
        with mock.patch.object(kickoff, 'env', lambda: env), contextlib.redirect_stdout(self.out):
            kickoff.cmd_feed(types.SimpleNamespace(days=1))
        return self.out.getvalue()

    def test_first_401_retries_once_with_the_full_header_set(self):
        with self.urlopen(401, 200):
            out = self.feed()
        self.assertIn('fetched 0 events', out)
        self.assertEqual(self.seen[0], None)
        self.assertIn('Mozilla', self.seen[1])

    def test_two_401s_report_a_dead_cookie(self):
        with self.urlopen(401, 401):
            with self.assertRaises(SystemExit):
                self.feed()
        self.assertEqual(len(self.seen), 2)
        self.assertIn('SHORTCUT_SID is dead', self.out.getvalue())

    def test_a_500_is_not_retried(self):
        with self.urlopen(500):
            with self.assertRaises(SystemExit):
                self.feed()
        self.assertEqual(len(self.seen), 1)


class FeedPageCap(StateDirCase):
    OLD_MARK = '2026-01-01T00:00:00.000Z'

    def feed_with_pages(self, start):
        kickoff.save('feed.json', {'high_water': self.OLD_MARK, 'events': {}, 'handled': {}})
        newest = kickoff.iso(kickoff.now_utc())
        calls = []

        def page(before, cookie, org, ws, full=False):
            calls.append(before)
            n = len(calls)
            return {'data': [{'id': f'e{n}', 'changed_at': newest}], 'start': start}
        env = {'SHORTCUT_SID': 'abc', 'SHORTCUT_TENANT_ORG': 'o', 'SHORTCUT_TENANT_WS': 'w'}
        with mock.patch.object(kickoff, 'fetch_page', page), mock.patch.object(kickoff, 'env', lambda: env):
            out = run(kickoff.cmd_feed, days=1)
        return out, calls, newest

    def test_cap_hit_warns_and_keeps_the_old_high_water(self):
        out, calls, _ = self.feed_with_pages('2026-06-01T00:00:00.000Z')
        self.assertEqual(len(calls), kickoff.FEED_MAX_PAGES)
        self.assertIn('WARNING', out)
        self.assertEqual(kickoff.load('feed.json', {})['high_water'], self.OLD_MARK)

    def test_reaching_the_mark_advances_the_high_water(self):
        out, calls, newest = self.feed_with_pages(self.OLD_MARK)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('WARNING', out)
        self.assertEqual(kickoff.load('feed.json', {})['high_water'], newest)

    def test_a_capped_walk_resumes_below_its_cursor_and_then_advances(self):
        kickoff.save('feed.json', {'high_water': self.OLD_MARK, 'events': {}, 'handled': {}})
        newest = kickoff.iso(kickoff.now_utc())
        calls = []
        env = {'SHORTCUT_SID': 'abc', 'SHORTCUT_TENANT_ORG': 'o', 'SHORTCUT_TENANT_WS': 'w'}

        def descending(before, cookie, org, ws, full=False):
            calls.append(before)
            n = len(calls)
            return {'data': [{'id': f'e{n}', 'changed_at': newest}], 'start': f'2026-09-{(n % 28) + 1:02d}T00:00:00.000Z'}

        def finishing(before, cookie, org, ws, full=False):
            calls.append(before)
            return {'data': [{'id': 'last', 'changed_at': newest}], 'start': self.OLD_MARK}
        with mock.patch.object(kickoff, 'env', lambda: env):
            with mock.patch.object(kickoff, 'fetch_page', descending):
                run(kickoff.cmd_feed, days=1)
            cursor = kickoff.load('feed.json', {})['resume_before']
            self.assertTrue(cursor)
            calls.clear()
            with mock.patch.object(kickoff, 'fetch_page', finishing):
                out = run(kickoff.cmd_feed, days=1)
        self.assertEqual(calls, [cursor])
        self.assertNotIn('WARNING', out)
        saved = kickoff.load('feed.json', {})
        self.assertEqual(saved['high_water'], newest)
        self.assertIsNone(saved['resume_before'])


def feed_event(eid, story, member='someone', at='2026-11-02T10:00:00.000Z', reasons=(), actions=()):
    return {'id': eid, 'changed_at': at, 'member_id': member, 'actor_name': 'A',
            'reasons': [{'reason': r} for r in reasons], 'actions': list(actions),
            'references': [{'entity_type': 'story', 'id': story, 'name': f'Story {story}'}]}


class AggregateTickets(unittest.TestCase):
    def test_dev_authored_events_do_not_count_as_activity(self):
        t = kickoff.aggregate_tickets([feed_event('1', 5, member=kickoff.DEV_UUID)])['5']
        self.assertEqual(t['last'], '')

    def test_last_is_the_newest_non_dev_event(self):
        events = [feed_event('1', 5, at='2026-11-01T00:00:00.000Z'),
                  feed_event('2', 5, at='2026-11-02T00:00:00.000Z'),
                  feed_event('3', 5, member=kickoff.DEV_UUID, at='2026-11-03T00:00:00.000Z')]
        self.assertEqual(kickoff.aggregate_tickets(events)['5']['last'], '2026-11-02T00:00:00.000Z')

    def test_comments_collect_and_flag_a_dev_mention(self):
        comment = {'entity_type': 'story-comment', 'action': 'create', 'text': 'hi\nthere', 'mention_ids': [kickoff.DEV_UUID]}
        t = kickoff.aggregate_tickets([feed_event('1', 5, actions=[comment])])['5']
        self.assertEqual(len(t['comments']), 1)
        self.assertTrue(t['comments'][0][2])
        self.assertEqual(t['comments'][0][3], 'hi there')

    def test_noise_only_is_followers_and_group_assignment_without_comments(self):
        noisy = kickoff.aggregate_tickets([feed_event('1', 5, reasons=['follower'])])['5']
        self.assertTrue(kickoff.is_noise_only(noisy))
        real = kickoff.aggregate_tickets([feed_event('2', 6, reasons=['follower', 'mention'])])['6']
        self.assertFalse(kickoff.is_noise_only(real))


class PickableTickets(StateDirCase):
    def story(self, sid, name):
        return {'id': sid, 'name': name, 'workflow_state_id': 1, 'owner_ids': [], 'created_at': kickoff.iso(kickoff.now_utc()),
                'updated_at': kickoff.iso(kickoff.now_utc()), 'estimate': None}

    def run_tickets(self, owner_hits, title_hits):
        def api_get(path, token):
            if path == '/workflows':
                return [{'states': [{'id': 1, 'name': 'Backlog'}]}]
            if path == '/members':
                return []
            query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)['query'][0]
            return {'data': owner_hits if query.startswith('owner:') else title_hits, 'next': None}
        with mock.patch.object(kickoff, 'api_get', api_get), mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}):
            return run(kickoff.cmd_tickets)

    def test_fuzzy_title_hit_without_a_frontend_word_is_filtered(self):
        out = self.run_tickets([], [self.story(1, 'Send feedback email'), self.story(2, 'FE: new loan screen'),
                                    self.story(3, 'Web App banner'), self.story(4, 'Frontend cleanup')])
        self.assertNotIn('#1 ', out)
        for sid in ('#2 ', '#3 ', '#4 '):
            self.assertIn(sid, out)

    def test_owner_query_hit_is_kept_whatever_its_title(self):
        out = self.run_tickets([self.story(1, 'Send feedback email')], [])
        self.assertIn('#1 ', out)

    def test_be_titles_are_still_dropped_for_owner_hits(self):
        out = self.run_tickets([self.story(1, 'Implement BE endpoint')], [])
        self.assertNotIn('#1 ', out)


class MineCommand(unittest.TestCase):
    def story(self, sid, state, owners=(kickoff.DEV_UUID,), updated='2026-11-10T09:00:00Z'):
        return {'id': sid, 'name': f'Title {sid}', 'workflow_state_id': state, 'owner_ids': list(owners), 'updated_at': updated}

    def run_mine(self, hits, state='In Progress'):
        queries = []

        def api_get(path, token):
            if path == '/workflows':
                return [{'states': [{'id': 1, 'name': 'In Progress'}, {'id': 2, 'name': 'In Progress Review '}]}]
            queries.append(urllib.parse.parse_qs(urllib.parse.urlparse(path).query)['query'][0])
            return {'data': hits, 'next': None}
        with mock.patch.object(kickoff, 'api_get', api_get), mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}):
            return run(kickoff.cmd_mine, state=state), queries

    def test_lists_only_the_devs_stories_in_exactly_that_state_oldest_first(self):
        out, queries = self.run_mine([self.story(1, 1, updated='2026-11-12T00:00:00Z'), self.story(2, 2),
                                      self.story(3, 1, owners=('someone-else',)), self.story(4, 1)])
        self.assertEqual(out.splitlines(), ['#4 2026-11-10 | Title 4', '#1 2026-11-12 | Title 1',
                                            '2 stories owned by josipmui in In Progress'])
        self.assertIn('owner:josipmui', queries[0])
        self.assertIn('state:"In Progress"', queries[0])

    def test_an_unknown_state_name_fails_instead_of_printing_a_false_zero(self):
        with self.assertRaises(SystemExit):
            self.run_mine([self.story(1, 1)], state='in progress')

    def test_prints_a_zero_count_when_nothing_matches(self):
        out, _ = self.run_mine([])
        self.assertEqual(out.strip(), '0 stories owned by josipmui in In Progress')


class StoryCommand(unittest.TestCase):
    ALICE, BOB = 'uuid-alice', 'uuid-bob'

    def story(self, sid, **extra):
        s = {'id': sid, 'name': f'Title {sid}', 'workflow_state_id': 7, 'owner_ids': [self.ALICE],
             'requested_by_id': self.BOB, 'epic_id': 9, 'blocked': True, 'blocker': False, 'estimate': 3,
             'created_at': '2026-10-01T00:00:00Z', 'updated_at': '2026-10-02T00:00:00Z',
             'story_links': [{'subject_id': sid, 'object_id': 11111, 'verb': 'blocks'}],
             'description': 'Body line one\nBody line two',
             'comments': [{'author_id': self.BOB, 'text': 'second', 'created_at': '2026-10-03T09:30:00Z'},
                          {'author_id': self.ALICE, 'text': 'first', 'created_at': '2026-10-02T08:00:00Z'},
                          {'author_id': self.ALICE, 'text': 'GONE', 'created_at': '2026-10-02T09:00:00Z', 'deleted': True},
                          {'author_id': 'uuid-unknown', 'text': 'third', 'created_at': '2026-10-04T10:00:00Z'}]}
        s.update(extra)
        return s

    def story_cmd(self, ids, stories=None, tokens=None):
        stories = stories or {}
        calls = []

        def api_get(path, token):
            calls.append(path)
            if tokens is not None:
                tokens.append(token)
            if path == '/workflows':
                return [{'states': [{'id': 7, 'name': 'In Progress '}]}]
            if path == '/members':
                return [{'id': self.ALICE, 'profile': {'mention_name': 'alice'}},
                        {'id': self.BOB, 'profile': {'mention_name': 'bob'}}]
            if path == '/epics/9':
                return {'name': 'Big Epic'}
            if path.startswith('/stories/'):
                sid = path.split('/')[2]
                if sid in stories:
                    raise http_error(stories[sid])
                return self.story(int(sid))
            raise AssertionError(path)
        with mock.patch.object(kickoff, 'api_get', api_get), mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 'sekrit-token'}):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    kickoff.cmd_story(types.SimpleNamespace(story_ids=ids))
            except SystemExit as e:
                buf.write(f'EXIT {e.code}')
        return buf.getvalue(), calls

    def test_two_tickets_print_with_named_state_people_epic_and_links(self):
        out, calls = self.story_cmd(['56503', '56238'])
        for sid in ('#56503 Title 56503', '#56238 Title 56238'):
            self.assertIn(sid, out)
        self.assertEqual(out.count('state: In Progress |'), 2)
        self.assertIn('owners: alice | requester: bob', out)
        self.assertIn('epic: Big Epic (epic 9)', out)
        self.assertIn('blocked: True', out)
        self.assertIn('link: #56503 blocks #11111', out)
        self.assertIn('Body line two', out)
        self.assertEqual(calls.count('/workflows'), 1)
        self.assertEqual(calls.count('/members'), 1)

    def test_comments_are_chronological_with_author_and_date_and_skip_deleted(self):
        out, _ = self.story_cmd(['56503'])
        self.assertIn('comments: 3', out)
        self.assertIn('C 2026-10-02 08:00 alice:', out)
        self.assertIn('C 2026-10-04 10:00 ?:', out)
        self.assertNotIn('GONE', out)
        self.assertLess(out.index('first'), out.index('second'))
        self.assertLess(out.index('second'), out.index('third'))

    def test_non_digit_id_is_rejected_before_any_request(self):
        out, calls = self.story_cmd(['56503', '../members'])
        self.assertIn('digits only', out)
        self.assertIn('EXIT 1', out)
        self.assertEqual(calls, [])

    def test_long_description_is_truncated(self):
        long = 'x' * (kickoff.STORY_DESC_MAX + 50)
        with mock.patch.object(kickoff, 'api_get', lambda p, t: {'/workflows': [], '/members': []}.get(p) if p in ('/workflows', '/members')
                               else self.story(1, description=long, epic_id=None)):
            with mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}):
                out = run(kickoff.cmd_story, story_ids=['1'])
        self.assertIn('[+50 chars]', out)
        self.assertNotIn('x' * (kickoff.STORY_DESC_MAX + 1), out)

    def test_http_error_on_one_ticket_still_prints_the_rest_then_exits_nonzero(self):
        out, _ = self.story_cmd(['404', '56503'], stories={'404': 404})
        self.assertIn('#404: HTTP 404', out)
        self.assertIn('#56503 Title 56503', out)
        self.assertIn('EXIT 1', out)

    def test_token_is_sent_but_never_printed(self):
        tokens = []
        out, _ = self.story_cmd(['56503'], tokens=tokens)
        self.assertIn('sekrit-token', tokens)
        self.assertNotIn('sekrit-token', out)

    def test_cli_registers_story_with_one_or_more_ids(self):
        with mock.patch.object(sys, 'argv', ['kickoff.py', 'story', '1', '2']), \
                mock.patch.object(kickoff, 'cmd_story') as fn:
            kickoff.main()
        self.assertEqual(fn.call_args[0][0].story_ids, ['1', '2'])


def skip_stale_guard(case):
    """The posting tests below are about payloads; StaleGuard covers the refusal with the real functions."""
    for name in ('approval_time', 'refuse_if_stale'):
        patcher = mock.patch.object(kickoff, name)
        patcher.start()
        case.addCleanup(patcher.stop)


class WriteCommands(unittest.TestCase):
    """comment / describe / move, with urlopen mocked: nothing here reaches Shortcut."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sent = []
        skip_stale_guard(self)

    def tearDown(self):
        self.tmp.cleanup()

    def body_file(self, raw, name='body.md'):
        path = os.path.join(self.tmp.name, name)
        with open(path, 'wb') as f:
            f.write(raw)
        return path

    def call(self, fn, responses=None, gets=None, **kw):
        """Runs fn(**kw); returns (stdout or 'EXIT n: stdout'). Writes land in self.sent as (method, path, json)."""
        responses = responses or {}

        def urlopen(req, timeout=None):
            self.sent.append((req.get_method(), req.full_url.replace(kickoff.API, ''),
                              json.loads(req.data.decode('utf-8')), req.get_header('Shortcut-token'),
                              req.get_header('Content-type')))
            return FakeResponse(json.dumps(responses.get(req.get_method(), {})).encode())

        def api_get(path, token):
            if path == '/workflows':
                return [{'states': [{'id': 1, 'name': 'To Do '}, {'id': 2, 'name': 'Testing'}]},
                        {'states': [{'id': 3, 'name': 'Testing'}, {'id': 4, 'name': 'Done'}]}]
            return {'workflow_state_id': (gets or {}).get(path.split('/')[2], 1)}
        buf = io.StringIO()
        with mock.patch.object(kickoff.urllib.request, 'urlopen', urlopen), \
                mock.patch.object(kickoff, 'api_get', api_get), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 'sekrit-token'}), \
                contextlib.redirect_stdout(buf):
            try:
                fn(types.SimpleNamespace(**kw))
            except SystemExit as e:
                return f'EXIT {e.code}: {buf.getvalue()}'
        return buf.getvalue()

    def test_comment_posts_the_file_text_exactly_and_prints_the_id(self):
        text = 'Pozdrav → emoji \U0001f600\n\n  indented line\n'
        out = self.call(kickoff.cmd_comment, {'POST': {'id': 777}}, story_id='56709', parent=None,
                        body_file=self.body_file(text.encode('utf-8')))
        self.assertEqual(self.sent, [('POST', '/stories/56709/comments', {'text': text}, 'sekrit-token',
                                      'application/json; charset=utf-8')])
        self.assertIn('comment 777 on #56709', out)
        self.assertNotIn('sekrit-token', out)

    def test_comment_reply_sends_the_parent_id_as_an_int(self):
        self.call(kickoff.cmd_comment, {'POST': {'id': 1}}, story_id='5', parent='999',
                  body_file=self.body_file(b'a reply that is long enough'))
        self.assertEqual(self.sent[0][2], {'text': 'a reply that is long enough', 'parent_id': 999})

    def test_a_utf8_bom_is_not_sent(self):
        self.call(kickoff.cmd_comment, {'POST': {'id': 1}}, story_id='5', parent=None,
                  body_file=self.body_file(b'\xef\xbb\xbfhello there'))
        self.assertEqual(self.sent[0][2]['text'], 'hello there')

    def test_empty_missing_and_non_digit_inputs_fail_before_any_request(self):
        for kw in ({'story_id': '5', 'body_file': self.body_file(b' \n', 'empty.md')},
                   {'story_id': '5', 'body_file': os.path.join(self.tmp.name, 'nope.md')},
                   {'story_id': '5', 'body_file': self.body_file(b'\xff\xfe not utf-8 \x80', 'latin.md')},
                   {'story_id': '../members', 'body_file': self.body_file(b'text')},
                   {'story_id': '5', 'parent': 'x', 'body_file': self.body_file(b'text')}):
            kw.setdefault('parent', None)
            self.assertIn('EXIT 1', self.call(kickoff.cmd_comment, **kw))
        self.assertEqual(self.sent, [])

    def test_http_error_exits_nonzero_with_the_status(self):
        def urlopen(req, timeout=None):
            raise http_error(403)
        with mock.patch.object(kickoff.urllib.request, 'urlopen', urlopen), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}), \
                contextlib.redirect_stdout(io.StringIO()) as buf, self.assertRaises(SystemExit):
            kickoff.cmd_describe(types.SimpleNamespace(story_id='5', body_file=self.body_file(b'text')))
        self.assertIn('HTTP 403', buf.getvalue())

    def test_describe_puts_only_the_description(self):
        out = self.call(kickoff.cmd_describe, {'PUT': {'id': 56709, 'updated_at': '2026-11-16T10:00:00Z'}},
                        story_id='56709', body_file=self.body_file('Opis č\n'.encode('utf-8')))
        self.assertEqual(self.sent[0][:3], ('PUT', '/stories/56709', {'description': 'Opis č\n'}))
        self.assertIn('#56709 description updated, updated_at 2026-11-16T10:00:00Z', out)

    def test_move_by_id_prints_old_and_new_state_names(self):
        out = self.call(kickoff.cmd_move, story_ids=['11', '12'], state='2', gets={'12': 4})
        self.assertEqual([s[:3] for s in self.sent], [('PUT', '/stories/11', {'workflow_state_id': 2}),
                                                      ('PUT', '/stories/12', {'workflow_state_id': 2})])
        self.assertIn('#11: To Do -> Testing', out)
        self.assertIn('#12: Done -> Testing', out)

    def test_move_by_exact_name_and_a_story_already_there_is_left_alone(self):
        out = self.call(kickoff.cmd_move, story_ids=['11', '12'], state='To Do', gets={'12': 2})
        self.assertEqual([s[1] for s in self.sent], ['/stories/12'])
        self.assertIn('#11: already To Do, left alone', out)

    def test_move_refuses_an_ambiguous_or_unknown_state_without_writing(self):
        for state in ('Testing', 'Nowhere', '999', 'testing'):
            self.assertIn('EXIT 1', self.call(kickoff.cmd_move, story_ids=['11'], state=state))
        self.assertEqual(self.sent, [])

    def test_move_rejects_non_digit_ids(self):
        self.assertIn('EXIT 1', self.call(kickoff.cmd_move, story_ids=['11', 'x'], state='4'))
        self.assertEqual(self.sent, [])

    def test_an_abbreviated_body_flag_is_rejected_so_the_hook_sees_every_text(self):
        for sub in ('comment', 'describe'):
            with mock.patch.object(sys, 'argv', ['kickoff.py', sub, '5', '--body', 'b.md']), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                kickoff.main()

    def test_non_ascii_digits_are_not_ids(self):
        self.assertIn('EXIT 1', self.call(kickoff.cmd_comment, story_id='5', parent='²', body_file=self.body_file(b'text')))
        self.assertIn('EXIT 1', self.call(kickoff.cmd_move, story_ids=['٥'], state='4'))
        self.assertEqual(self.sent, [])

    def test_a_timeout_warns_that_the_write_may_have_landed(self):
        def urlopen(req, timeout=None):
            raise TimeoutError('timed out')
        with mock.patch.object(kickoff.urllib.request, 'urlopen', urlopen), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}), \
                contextlib.redirect_stdout(io.StringIO()) as buf, self.assertRaises(SystemExit):
            kickoff.cmd_comment(types.SimpleNamespace(story_id='5', parent=None, body_file=self.body_file(b'text')))
        self.assertIn('may have gone through', buf.getvalue())

    def test_cli_registers_the_three_commands(self):
        for argv, fn, attrs in (
                (['comment', '5', '--body-file', 'b.md', '--parent', '9'], 'cmd_comment', {'story_id': '5', 'parent': '9'}),
                (['describe', '5', '--body-file', 'b.md'], 'cmd_describe', {'story_id': '5', 'body_file': 'b.md'}),
                (['move', '5', '6', '--state', 'Testing'], 'cmd_move', {'story_ids': ['5', '6'], 'state': 'Testing'})):
            with mock.patch.object(sys, 'argv', ['kickoff.py'] + argv), mock.patch.object(kickoff, fn) as called:
                kickoff.main()
            for k, v in attrs.items():
                self.assertEqual(getattr(called.call_args[0][0], k), v)


class CreateCommand(unittest.TestCase):
    """create, with urlopen mocked: no story is ever created for real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sent = []
        skip_stale_guard(self)
        self.body = os.path.join(self.tmp.name, 'body.md')
        with open(self.body, 'wb') as f:
            f.write('Opis → č\n'.encode('utf-8'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_create(self, fail_on=None, **kw):
        """Returns stdout, or 'EXIT n: stdout'. Writes land in self.sent as (method, path, json)."""
        def urlopen(req, timeout=None):
            path = req.full_url.replace(kickoff.API, '')
            self.sent.append((req.get_method(), path, json.loads(req.data.decode('utf-8')), req.get_header('Shortcut-token')))
            if path == fail_on:
                raise http_error(422)
            reply = {'id': 99001, 'app_url': 'https://app.shortcut.com/zirtue/story/99001'} if path == '/stories' else {}
            return FakeResponse(json.dumps(reply).encode())

        def api_get(path, token):
            if path == '/workflows':
                return [{'states': [{'id': 7, 'name': 'Backlog'}, {'id': 8, 'name': 'Testing'}]},
                        {'states': [{'id': 9, 'name': 'Testing'}]}]
            return [{'id': 'uuid-dev', 'profile': {'mention_name': 'josipmui'}}, {'id': 'uuid-p', 'profile': {'mention_name': 'peter'}}]
        args = dict(title='FE: Add the thing', body_file=self.body, owner=None, state=None, epic=None,
                    type='feature', label=[], relates=[])
        args.update(kw)
        buf = io.StringIO()
        with mock.patch.object(kickoff.urllib.request, 'urlopen', urlopen), \
                mock.patch.object(kickoff, 'api_get', api_get), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 'sekrit-token'}), \
                contextlib.redirect_stdout(buf):
            try:
                kickoff.cmd_create(types.SimpleNamespace(**args))
            except SystemExit as e:
                return f'EXIT {e.code}: {buf.getvalue()}'
        return buf.getvalue()

    def test_minimal_create_posts_the_pinned_team_and_default_state_and_prints_id_and_url(self):
        out = self.run_create()
        self.assertEqual(self.sent, [('POST', '/stories', {
            'name': 'FE: Add the thing', 'description': 'Opis → č\n', 'story_type': 'feature',
            'group_id': kickoff.ENG_TEAM_ID, 'workflow_state_id': kickoff.ENG_TODO_STATE_ID}, 'sekrit-token')])
        self.assertIn('#99001 created: https://app.shortcut.com/zirtue/story/99001', out)
        self.assertNotIn('sekrit-token', out)

    def test_every_option_lands_in_the_payload_and_each_relates_becomes_a_link(self):
        out = self.run_create(owner='josipmui', state='Backlog', epic='53696', type='bug',
                              label=['fe', 'urgent'], relates=['56709', '56710'])
        story = self.sent[0][2]
        self.assertEqual((story['owner_ids'], story['workflow_state_id'], story['epic_id'], story['story_type'], story['labels']),
                         (['uuid-dev'], 7, 53696, 'bug', [{'name': 'fe'}, {'name': 'urgent'}]))
        self.assertEqual([s[:3] for s in self.sent[1:]], [
            ('POST', '/story-links', {'subject_id': 99001, 'object_id': 56709, 'verb': 'relates to'}),
            ('POST', '/story-links', {'subject_id': 99001, 'object_id': 56710, 'verb': 'relates to'})])
        self.assertIn('#99001 relates to #56710', out)

    def test_bad_input_fails_before_any_request(self):
        for kw in ({'title': '  '}, {'title': 'two\nlines'}, {'relates': ['x']}, {'epic': '5a'},
                   {'state': 'Testing'}, {'state': 'Nowhere'}, {'owner': 'nobody'},
                   {'body_file': os.path.join(self.tmp.name, 'nope.md')}):
            self.assertIn('EXIT 1', self.run_create(**kw), kw)
        self.assertEqual(self.sent, [])

    def test_duplicate_relates_ids_link_once(self):
        self.run_create(relates=['56709', '56709', '056709'])
        self.assertEqual([s[1] for s in self.sent], ['/stories', '/story-links'])

    def test_an_unreachable_relates_story_stops_everything_before_the_post(self):
        def api_get(path, token):
            raise http_error(404)
        with mock.patch.object(kickoff, 'api_get', api_get), mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}), \
                mock.patch.object(kickoff.urllib.request, 'urlopen', side_effect=AssertionError('posted')), \
                contextlib.redirect_stdout(io.StringIO()) as buf, self.assertRaises(SystemExit):
            kickoff.cmd_create(types.SimpleNamespace(title='T', body_file=self.body, owner=None, state=None, epic=None,
                                                     type='feature', label=[], relates=['5']))
        self.assertIn('nothing created', buf.getvalue())

    def test_a_failed_story_post_exits_nonzero_and_links_nothing(self):
        out = self.run_create(fail_on='/stories', relates=['56709'])
        self.assertIn('HTTP 422', out)
        self.assertEqual([s[1] for s in self.sent], ['/stories'])

    def test_a_failed_link_keeps_the_created_id_in_the_output(self):
        out = self.run_create(fail_on='/story-links', relates=['56709'])
        self.assertIn('#99001 created', out)
        self.assertIn('EXIT 1', out)

    def test_cli_registers_create_and_rejects_an_abbreviated_flag(self):
        argv = ['kickoff.py', 'create', '--title', 'T', '--body-file', 'b.md', '--label', 'a', '--label', 'b',
                '--relates', '5', '--relates', '6', '--epic', '9', '--type', 'chore', '--owner', 'peter', '--state', 'Backlog']
        with mock.patch.object(sys, 'argv', argv), mock.patch.object(kickoff, 'cmd_create') as called:
            kickoff.main()
        a = called.call_args[0][0]
        self.assertEqual((a.title, a.label, a.relates, a.epic, a.type, a.owner, a.state),
                         ('T', ['a', 'b'], ['5', '6'], '9', 'chore', 'peter', 'Backlog'))
        with mock.patch.object(sys, 'argv', ['kickoff.py', 'create', '--ti', 'T', '--body-file', 'b.md']), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            kickoff.main()
        with mock.patch.object(sys, 'argv', ['kickoff.py', 'create', '--title', 'T', '--body-file', 'b.md', '--type', 'epic']), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            kickoff.main()


class StaleGuard(unittest.TestCase):
    """comment / describe / create refuse to post text approved before someone else touched the ticket."""
    BOB = 'uuid-bob'
    APPROVED = '2026-11-17T08:00:00.000Z'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sent = []
        self.orig_state = kickoff.STATE_DIR
        kickoff.STATE_DIR = os.path.join(self.tmp.name, 'state')
        self.body = os.path.join(self.tmp.name, 'body.md')
        with open(self.body, 'wb') as f:
            f.write(b'Merged and ready to be tested.\n')
        self.story = {'workflow_state_id': 1, 'comments': []}
        self.history = []

    def tearDown(self):
        kickoff.STATE_DIR = self.orig_state
        self.tmp.cleanup()

    def approve(self, at, text='Merged and ready to be tested.'):
        os.makedirs(os.path.join(kickoff.STATE_DIR, 'approvals'), exist_ok=True)
        kickoff.save(f'approvals/{kickoff.body_key(text)}.json', {'approved_at': at})

    def comment(self, by, at, text='tested, it fails'):
        return {'author_id': by, 'created_at': at, 'updated_at': at, 'text': text}

    def call(self, fn, **kw):
        def urlopen(req, timeout=None):
            self.sent.append((req.get_method(), req.full_url.replace(kickoff.API, '')))
            return FakeResponse(json.dumps({'id': 99001, 'updated_at': 'x'}).encode())

        def api_get(path, token):
            if path == '/workflows':
                return [{'states': [{'id': 1, 'name': 'To Do'}, {'id': 2, 'name': 'Testing'}]}]
            if path == '/members':
                return [{'id': self.BOB, 'profile': {'mention_name': 'lenar'}},
                        {'id': kickoff.DEV_UUID, 'profile': {'mention_name': 'josipmui'}}]
            if path.endswith('/history'):
                return self.history
            return self.story
        args = dict(story_id='56709', parent=None, body_file=self.body, approved_at=None)
        args.update(kw)
        buf = io.StringIO()
        with mock.patch.object(kickoff.urllib.request, 'urlopen', urlopen), mock.patch.object(kickoff, 'api_get', api_get), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}), contextlib.redirect_stdout(buf):
            try:
                fn(types.SimpleNamespace(**args))
            except SystemExit as e:
                return f'EXIT {e.code}: {buf.getvalue()}'
        return buf.getvalue()

    def test_a_comment_by_someone_else_after_approval_refuses_the_post_and_names_it(self):
        self.approve(self.APPROVED)
        self.story['comments'] = [self.comment(self.BOB, '2026-11-17T09:30:00Z', 'Tested: modal is off on desktop')]
        out = self.call(kickoff.cmd_comment)
        self.assertIn('EXIT 1', out)
        self.assertIn('REFUSED', out)
        self.assertIn('lenar', out)
        self.assertIn('2026-11-17 09:30', out)
        self.assertIn('modal is off on desktop', out)
        self.assertEqual(self.sent, [])

    def test_the_same_comment_posts_when_it_came_before_the_approval(self):
        self.approve(self.APPROVED)
        self.story['comments'] = [self.comment(self.BOB, '2026-11-17T07:59:00Z')]
        self.assertIn('comment 99001 on #56709', self.call(kickoff.cmd_comment))
        self.assertEqual(self.sent, [('POST', '/stories/56709/comments')])

    def test_a_later_approval_lets_the_post_through(self):
        self.story['comments'] = [self.comment(self.BOB, '2026-11-17T09:30:00Z')]
        self.approve('2026-11-17T09:31:00.000Z')
        self.assertIn('comment 99001', self.call(kickoff.cmd_comment))

    def test_the_dev_own_comment_and_a_deleted_one_do_not_count(self):
        self.approve(self.APPROVED)
        self.story['comments'] = [self.comment(kickoff.DEV_UUID, '2026-11-17T09:30:00Z'),
                                  dict(self.comment(self.BOB, '2026-11-17T09:40:00Z'), deleted=True)]
        self.assertIn('comment 99001', self.call(kickoff.cmd_comment))

    def test_a_state_move_by_someone_else_refuses_describe_with_the_old_and_new_state(self):
        self.approve(self.APPROVED)
        self.history = [{'changed_at': '2026-11-17T09:00:00Z', 'member_id': self.BOB, 'actions': [
            {'entity_type': 'story', 'changes': {'workflow_state_id': {'old': 1, 'new': 2}}}]}]
        out = self.call(kickoff.cmd_describe)
        self.assertIn('state move by lenar', out)
        self.assertIn('To Do -> Testing', out)
        self.assertEqual(self.sent, [])

    def test_a_description_edit_by_someone_else_refuses_and_a_memberless_event_counts_as_automation(self):
        # Shape read live from /stories/56709/history on 2026-11-17: story/update with changes.description.
        self.approve(self.APPROVED)
        self.history = [{'changed_at': '2026-11-17T09:00:00Z', 'member_id': self.BOB, 'actions': [
            {'entity_type': 'story', 'action': 'update', 'changes': {'description': {'old': 'a', 'new': 'b'}}}]}]
        self.assertIn('description edit by lenar', self.call(kickoff.cmd_comment))
        self.history[0].pop('member_id')
        self.assertIn('description edit by automation', self.call(kickoff.cmd_comment))
        self.assertEqual(self.sent, [])

    def test_a_follower_or_link_change_does_not_refuse(self):
        self.approve(self.APPROVED)
        self.history = [{'changed_at': '2026-11-17T09:00:00Z', 'member_id': self.BOB, 'actions': [
            {'entity_type': 'story', 'action': 'update', 'changes': {'follower_ids': {'adds': ['x']}}}]}]
        self.assertIn('comment 99001', self.call(kickoff.cmd_comment))

    def test_the_hash_matches_the_one_the_outbound_hook_computes(self):
        import hashlib
        text = '  Merged,\r\n  ready   to test.\n'
        self.assertEqual(kickoff.body_key(text), hashlib.sha256(b'Merged, ready to test.').hexdigest())

    def test_a_state_move_by_the_dev_does_not_count(self):
        self.approve(self.APPROVED)
        self.history = [{'changed_at': '2026-11-17T09:00:00Z', 'member_id': kickoff.DEV_UUID, 'actions': [
            {'entity_type': 'story', 'changes': {'workflow_state_id': {'old': 1, 'new': 2}}}]}]
        self.assertIn('description updated', self.call(kickoff.cmd_describe))

    def test_no_record_and_no_flag_refuses_and_the_flag_supplies_the_time(self):
        self.story['comments'] = [self.comment(self.BOB, '2026-11-10T09:30:00Z')]
        out = self.call(kickoff.cmd_comment)
        self.assertIn('EXIT 1', out)
        self.assertIn('--approved-at', out)
        self.assertIn('EXIT 1', self.call(kickoff.cmd_comment, approved_at='2026-11-10T08:00:00Z'))
        self.assertIn('EXIT 1', self.call(kickoff.cmd_comment, approved_at='not a time'))
        self.assertIn('comment 99001', self.call(kickoff.cmd_comment, approved_at='2026-11-11T00:00:00Z'))
        self.assertEqual(len(self.sent), 1)

    def test_a_future_approved_at_cannot_skip_the_check(self):
        self.story['comments'] = [self.comment(self.BOB, '2026-11-10T09:30:00Z')]
        out = self.call(kickoff.cmd_comment, approved_at='2099-01-01T00:00:00Z')
        self.assertIn('future', out)
        self.assertEqual(self.sent, [])

    def test_a_history_in_an_unexpected_shape_refuses_instead_of_assuming_no_activity(self):
        self.approve(self.APPROVED)
        self.history = {'message': 'oops'}
        self.assertIn('EXIT 1', self.call(kickoff.cmd_comment))
        self.assertEqual(self.sent, [])

    def test_a_comment_edited_after_approval_counts_by_its_updated_at(self):
        self.approve(self.APPROVED)
        c = self.comment(self.BOB, '2026-11-17T07:00:00Z')
        c['updated_at'] = '2026-11-17T09:00:00Z'
        self.story['comments'] = [c]
        self.assertIn('REFUSED', self.call(kickoff.cmd_comment))

    def test_create_without_relates_checks_nothing(self):
        self.story['comments'] = [self.comment(self.BOB, '2026-11-17T09:30:00Z')]
        out = self.call(kickoff.cmd_create, title='T', owner=None, state=None, epic=None, type='feature', label=[], relates=[])
        self.assertIn('#99001 created', out)

    def test_an_unreadable_ticket_refuses_instead_of_posting_blind(self):
        self.approve(self.APPROVED)
        with mock.patch.object(kickoff, 'api_get', side_effect=http_error(500)), \
                mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_API_TOKEN': 't'}), \
                mock.patch.object(kickoff.urllib.request, 'urlopen', side_effect=AssertionError('posted')), \
                contextlib.redirect_stdout(io.StringIO()) as buf, self.assertRaises(SystemExit):
            kickoff.cmd_comment(types.SimpleNamespace(story_id='5', parent=None, body_file=self.body, approved_at=None))
        self.assertIn('nothing posted', buf.getvalue())

    def test_create_checks_each_relates_story_before_creating(self):
        self.approve(self.APPROVED)
        self.story['comments'] = [self.comment(self.BOB, '2026-11-17T09:30:00Z')]
        out = self.call(kickoff.cmd_create, title='T', owner=None, state=None, epic=None, type='feature', label=[],
                        relates=['56709'])
        self.assertIn('REFUSED', out)
        self.assertEqual(self.sent, [])

    def test_cli_accepts_approved_at_on_the_three_posting_commands(self):
        for argv, fn in ((['comment', '5', '--body-file', 'b.md', '--approved-at', 'T'], 'cmd_comment'),
                         (['describe', '5', '--body-file', 'b.md', '--approved-at', 'T'], 'cmd_describe'),
                         (['create', '--title', 'T', '--body-file', 'b.md', '--approved-at', 'T'], 'cmd_create')):
            with mock.patch.object(sys, 'argv', ['kickoff.py'] + argv), mock.patch.object(kickoff, fn) as called:
                kickoff.main()
            self.assertEqual(called.call_args[0][0].approved_at, 'T')


class Leftovers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.orig = (kickoff.PROJECTS, kickoff.REPOS)
        kickoff.PROJECTS = self.tmp.name
        kickoff.REPOS = ['zng-app']
        os.makedirs(os.path.join(self.tmp.name, 'zng-app'))

    def tearDown(self):
        kickoff.PROJECTS, kickoff.REPOS = self.orig
        self.tmp.cleanup()

    def leftovers(self, answers):
        def git_try(repo, *args):
            return answers.get(args[0] if args[0] != 'rev-parse' else ' '.join(args), (True, ''))
        with mock.patch.object(kickoff, 'git_try', git_try):
            return run(kickoff.cmd_leftovers)

    def test_no_upstream_says_so_instead_of_printing_a_git_error(self):
        out = self.leftovers({'rev-parse --abbrev-ref HEAD': (True, 'feat'),
                              'rev-parse --verify --quiet @{u}': (False, ''),
                              'log': (False, 'fatal: no upstream configured'),
                              'rev-list': (True, '3')})
        self.assertIn('no upstream, 3 local commits', out)
        self.assertNotIn('git error', out)
        self.assertNotIn('fatal', out)

    def test_dirty_paths_and_unpushed_commits_are_listed(self):
        out = self.leftovers({'rev-parse --abbrev-ref HEAD': (True, 'main'),
                              'rev-parse --verify --quiet @{u}': (True, 'abc'),
                              'status': (True, 'M a.py\n?? b.py'),
                              'log': (True, 'abc1234 do a thing')})
        self.assertIn('2 dirty', out)
        self.assertIn('   dirty M a.py', out)
        self.assertIn('   dirty ?? b.py', out)
        self.assertIn('   unpushed abc1234 do a thing', out)

    def test_a_failed_fetch_is_reported(self):
        out = self.leftovers({'fetch': (False, 'could not resolve host'),
                              'rev-parse --verify --quiet @{u}': (True, 'abc')})
        self.assertIn('fetch failed', out)
        self.assertIn('could not resolve host', out)


def draft(topic, state='needs-you', origin='the hub chat', updated='2026-11-02T10:00:00+00:00', sent=(False,), brief=''):
    return {'id': topic, 'topic': topic, 'brief': brief, 'state': state, 'origin_label': origin,
            'updated_at': updated, 'variants': [{'recipient': 'x', 'sent': s} for s in sent]}


class Drafts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, 'data')
        self.store_dir = os.path.join(self.data, 'message-drafts')
        os.makedirs(self.store_dir)
        self.env = mock.patch.dict(os.environ, {'CC_DATA_DIR': self.data})
        self.env.start()
        self.state = mock.patch.object(kickoff, 'STATE_DIR', os.path.join(self.tmp.name, 'state'))
        self.state.start()
        self.zng = [draft('sc-56344 Johanna reply', origin='Oct 23 hub', updated='2026-10-23T09:15:00+00:00'),
                    draft('New FE ticket 1: Team roles'),
                    draft('sc-56160 how to test', state='copied'),
                    draft('sc-56161 old', state='archived'),
                    draft('sc-56162 posted by Claude', sent=(True, True)),
                    draft('Epic 55507 half sent', sent=(True, False))]
        self.write('zng.json', {'drafts': self.zng, 'handles': {}})
        self.write('other.json', {'drafts': [draft('Minecraft server invite')], 'handles': {}})

    def tearDown(self):
        self.state.stop()
        self.env.stop()
        self.tmp.cleanup()

    def write(self, name, obj):
        with open(os.path.join(self.store_dir, name), 'w', encoding='utf-8') as f:
            json.dump(obj, f)

    def test_unsent_zng_drafts_are_listed_with_origin_and_time(self):
        out = run(kickoff.cmd_drafts)
        self.assertIn('sc-56344 Johanna reply', out)
        self.assertIn('Oct 23 hub', out)
        self.assertIn('2026-10-23 09:15', out)
        self.assertIn('New FE ticket 1: Team roles', out)
        self.assertIn('Epic 55507 half sent', out)

    def test_copied_archived_and_fully_sent_drafts_are_hidden(self):
        out = run(kickoff.cmd_drafts)
        for gone in ('sc-56160', 'sc-56161', 'sc-56162'):
            self.assertNotIn(gone, out)

    def test_a_project_with_no_zng_draft_is_not_listed(self):
        self.assertNotIn('Minecraft', run(kickoff.cmd_drafts))

    def test_leftovers_reports_the_drafts_too(self):
        with mock.patch.object(kickoff, 'REPOS', []):
            self.assertIn('sc-56344 Johanna reply', run(kickoff.cmd_leftovers))

    def test_only_the_topic_is_printed_never_the_body(self):
        self.zng[0]['variants'][0]['versions'] = [{'body': 'SECRET-BODY-TEXT'}]
        self.zng[0]['brief'] = 'SECRET-BRIEF-TEXT'
        self.write('zng.json', {'drafts': self.zng, 'handles': {}})
        out = run(kickoff.cmd_drafts)
        self.assertNotIn('SECRET', out)

    def test_missing_dir_fails_soft(self):
        os.environ['CC_DATA_DIR'] = os.path.join(self.tmp.name, 'nope')
        out = run(kickoff.cmd_drafts)
        self.assertIn('no drafts store', out)

    def test_unreadable_and_wrong_shaped_files_are_skipped(self):
        with open(os.path.join(self.store_dir, 'bad.json'), 'w') as f:
            f.write('{not json')
        self.write('list.json', [1, 2])
        self.write('nokey.json', {'other': 1})
        self.write('baditem.json', {'drafts': ['x', {'topic': 5}, {}]})
        self.assertIn('sc-56344 Johanna reply', run(kickoff.cmd_drafts))

    def test_ticket_ids_are_found_in_topics(self):
        self.assertEqual(kickoff.draft_ticket_ids('SC-56344 reply, also 55507 and 2026'), {'56344', '55507'})
        self.assertEqual(kickoff.draft_ticket_ids('New FE ticket 1'), set())

    def _feed(self, comment_by='someone-else', dev_reply=False):
        now = kickoff.now_utc()
        mk = lambda sid, who, at: {'changed_at': kickoff.iso(at), 'member_id': who, 'actor_name': 'Lenar',
                                   'actions': [{'entity_type': 'story', 'id': sid, 'name': 'ACH'},
                                               {'entity_type': 'story-comment', 'action': 'create', 'text': 'q?'}]}
        events = {'a': mk(56468, comment_by, now - kickoff.dt.timedelta(days=7))}
        if dev_reply:
            events['b'] = mk(56468, kickoff.DEV_UUID, now - kickoff.dt.timedelta(days=6))

        def collect(fetch, ev, stop_at, before):
            ev.update(events)
            return len(events), True, None
        with mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_SID': 'x'}), \
                mock.patch.object(kickoff, 'collect_events', collect):
            return run(kickoff.cmd_feed, days=30, show_answered=True)

    def test_a_copied_draft_naming_the_ticket_in_its_body_answers_it_silently(self):
        d = draft('Biller Groups: how to test everything', state='copied', updated=kickoff.iso(kickoff.now_utc()))
        d['variants'][0]['current'] = '1'
        d['variants'][0]['versions'] = [{'n': 1, 'body': 'ACH is hidden, see https://app.shortcut.com/zirtue/story/56468'}]
        self.write('zng.json', {'drafts': self.zng + [d], 'handles': {}})
        out = self._feed()
        self.assertNotIn('UNANSWERED', out)
        self.assertIn('0 tickets with unhandled activity', out)
        self.assertIn('#56468 ACH | draft copied', out)

    def test_a_question_with_no_reply_anywhere_is_labelled_with_what_was_checked(self):
        out = self._feed()
        self.assertIn('#56468', out)
        self.assertIn('UNANSWERED: last comment', out)
        self.assertIn('no copied draft naming it', out)

    def test_a_dev_comment_on_the_ticket_clears_the_unanswered_label(self):
        self.assertNotIn('UNANSWERED', self._feed(dev_reply=True))

    def test_a_draft_that_is_only_unsent_does_not_answer_the_ticket(self):
        d = draft('how to test', updated=kickoff.iso(kickoff.now_utc()))
        d['variants'][0]['current'] = '1'
        d['variants'][0]['versions'] = [{'n': 1, 'body': 'story/56468'}]
        self.write('zng.json', {'drafts': self.zng + [d], 'handles': {}})
        self.assertIn('UNANSWERED', self._feed())

    def test_answered_command_records_the_channel_and_hides_the_ticket_draft(self):
        run(kickoff.cmd_handle, story_ids=['56344'], note='told her', channel='slack')
        mark = kickoff.load('feed.json', {})['handled']['56344']
        self.assertEqual(mark['answered_via'], 'slack')
        self.assertNotIn('sc-56344 Johanna reply', run(kickoff.cmd_drafts))

    def test_feed_flags_a_ticket_that_already_has_an_open_draft(self):
        root = self.tmp.name
        event = {'changed_at': kickoff.iso(kickoff.now_utc()), 'member_id': 'someone-else', 'actor_name': 'Johanna',
                 'actions': [{'entity_type': 'story', 'id': 56344, 'name': 'Q'},
                             {'entity_type': 'story-comment', 'action': 'create', 'text': 'hi'}]}
        other = dict(event, actions=[{'entity_type': 'story', 'id': 77777, 'name': 'R'},
                                     {'entity_type': 'story-comment', 'action': 'create', 'text': 'yo'}])

        def collect(fetch, events, stop_at, before):
            events.update({'a': event, 'b': other})
            return 2, True, None
        with mock.patch.object(kickoff, 'STATE_DIR', os.path.join(root, 'state')),                 mock.patch.object(kickoff, 'env', lambda: {'SHORTCUT_SID': 'x'}),                 mock.patch.object(kickoff, 'collect_events', collect):
            out = run(kickoff.cmd_feed, days=3)
        flagged = out.split('#56344')[1].split('#77777')[0]
        self.assertIn('DRAFT EXISTS: post it, do not redraft', flagged)
        self.assertIn('Oct 23 hub', flagged)
        self.assertNotIn('DRAFT EXISTS', out.split('#77777')[1])


if __name__ == '__main__':
    unittest.main()
