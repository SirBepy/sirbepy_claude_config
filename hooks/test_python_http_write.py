"""Self-test for _python_http_write.py.

Run directly: python hooks/test_python_http_write.py
Pure string probes: nothing is sent anywhere. The guards' own tests cover the end-to-end shapes;
these pin the reader's edge cases (quoting, commas, assignments named data, parent resources).
"""

import sys

import _testlib
from _python_http_write import has_bare_stories_path, python_write_verbs

SH = "https://api.app.shortcut.com/api/v3"
# (command, expected write verbs, label)
VERB_CASES = [
    (f"u.urlopen(u.Request('{SH}/x', data=b'{{}}'))", {"POST"}, "data kwarg"),
    (f"u.urlopen(u.Request('{SH}/x', b'{{}}'))", {"POST"}, "positional body in Request"),
    ("u.urlopen(req, b'{}')", {"POST"}, "positional body in urlopen"),
    ("u.urlopen(req, timeout=5)", set(), "timeout kwarg is not a body"),
    ("u.urlopen(req, None, 5)", set(), "None body"),
    ("u.Request(url, data=None, headers=h)", set(), "data=None"),
    ("u.Request(url, data = None, headers=h)", set(), "data = None with spaces"),
    ("data = json.load(u.urlopen(r))", set(), "assignment to a variable named data"),
    ("data=json.load(u.urlopen(r))", set(), "assignment without spaces"),
    ("u.urlopen(u.Request(url, headers=json.dumps(o, indent=2)))", set(), "commas inside nested call args"),
    ('python -c "u.urlopen(u.Request(\\"https://x/search?q=a,b\\", headers=h))"', set(), "comma inside an escaped-quote string"),
    ('python -c "u.Request(\\"u\\", headers={\\"X\\": \\"it\'s\\"}, data=b)"', {"POST"}, "apostrophe inside an escaped-quote string"),
    ('python -c "u.Request(\\"a\\\\\\"b\\", data=b\'x\')"', {"POST"}, "escaped quote inside an escaped-quote string"),
    ('python -c "u.urlopen(u.Request(url, headers={\\"X\\": \\"it\\\\\\"s\\"}, data=b\'x\'))"', {"POST"}, "escaped quote inside a header value"),
    ("u.Request(" * 30000, set(), "an unclosed call repeated many times finishes (bounded scan)"),
    ("u.Request(url, headers=h, method='GET')", set(), "explicit GET"),
    ("u.Request(url, data=b, method='PUT')", {"PUT"}, "explicit PUT"),
    ("requests.post(url, json={})", {"POST"}, "requests.post"),
    ("s.put(url, json={})", {"PUT"}, "short session name"),
    ("sess.patch(url)", {"PATCH"}, "sess receiver"),
    ("http_client.post(url)", {"POST"}, "client receiver"),
    ("cache.put(key)", set(), "unrelated put"),
    ("c.request('POST', '/api/v3/stories')", {"POST"}, ".request with a verb"),
]

# (command, expected, label)
PATH_CASES = [
    (f"u.Request('{SH}/stories')", True, "literal create URL"),
    ("API + '/stories'", True, "base plus quoted path"),
    ('f"{API}/stories"', True, "f-string base"),
    ("'%s/stories' % API", True, "percent-format base"),
    ("'%(api)s/stories' % d", True, "named percent-format base"),
    (f"u.Request('{SH}/epics/5/stories')", False, "literal epic story list"),
    ('f"{API}/epics/{eid}/stories"', False, "f-string epic story list with a variable id"),
    ('f"{API}/iterations/{i}/stories?x=1"', False, "iteration story list"),
    ("API + '/search/stories'", False, "search"),
    (f"u.Request('{SH}/stories/123')", False, "one story"),
    (f"u.Request('{SH}/stories/123/comments')", False, "comments"),
]


def check_verbs(case) -> bool:
    command, expected, label = case
    got = python_write_verbs(command)
    return _testlib.report(got == expected, f"verbs: {label} (expected {expected}, got {got})")


def check_paths(case) -> bool:
    command, expected, label = case
    got = has_bare_stories_path(command)
    return _testlib.report(got == expected, f"path: {label} (expected {expected}, got {got})")


fails = _testlib.run_cases(VERB_CASES, check_verbs) + _testlib.run_cases(PATH_CASES, check_paths)
sys.exit(_testlib.summarize(fails, style="count"))
