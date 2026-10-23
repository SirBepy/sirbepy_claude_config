import contextlib
import io
import os
import sys
import tempfile
import types
import unittest

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


if __name__ == '__main__':
    unittest.main()
