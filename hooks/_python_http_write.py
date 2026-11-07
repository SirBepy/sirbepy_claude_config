"""Write verbs of an inline Python (or node) HTTP script, for the Shortcut guards.

`curl -X POST` and `Invoke-RestMethod -Method Post` carry their verb in a flag the guards
already read. A `python -c` script puts it in the call instead: 2026-11-06, a zng-app session
created, posted and edited Shortcut items with `urllib.request.Request(url, data=...,
method='POST')` and neither `shortcut-create-guard.py` nor `outbound-verify-guard.py` saw it.

Read-only calls (`urlopen(url)`, `requests.get`) name no verb here, so reads stay unblocked.
A script FILE's body is not in the command string; that stays the stated limit.
"""

import re

# `method='POST'`, `method="PUT"`, node's `method: 'PATCH'`; a backslash may precede the quote
# when the script sits inside a double-quoted `bash -c` / `python -c "..."` string.
_METHOD_RE = re.compile(r"""\bmethod\s*[=:]\s*\\?["']\s*(POST|PUT|PATCH|DELETE|GET)\b""", re.IGNORECASE)
# `requests.post(`, `httpx.put(`, and the same on a session or client object (`s.post(`,
# `sess.put(`, `client.patch(`), where the receiver is named like one.
_CLIENT_CALL_RE = re.compile(
    r"\b(?:requests|httpx|\w*sess\w*|\w*client\w*|[sc])\.(post|put|patch)\s*\(",
    re.IGNORECASE,
)
_REQUEST_CALL_RE = re.compile(r"""\.request\s*\(\s*\\?["']\s*(POST|PUT|PATCH)\b""", re.IGNORECASE)
_URLLIB_CALL_RE = re.compile(r"\b(?:Request|urlopen)\s*\(")
_DATA_ARG_RE = re.compile(r"\s*data\s*=(?!=)(?!\s*None\b)")
_KWARG_RE = re.compile(r"\s*\w+\s*=(?!=)")
MAX_CALL_CHARS = 5000
MAX_CALLS_SCANNED = 200

# Evidence that the script talks to Shortcut even when the URL is assembled from pieces: the
# host, or the token plumbing (`kickoff.env()`, the env var, the header name).
SHORTCUT_HINT_RE = re.compile(
    r"api\.app\.shortcut\.com|SHORTCUT_API_TOKEN|kickoff\.env|Shortcut-Token",
    re.IGNORECASE,
)

# The create path `/stories`: after a quote (`API + '/stories'`), `v3` (the literal URL), `}`
# (`f"{API}/stories"`) or `%s` (`'%s/stories' % API`). A story LIST under another resource
# (`/epics/5/stories`, `{API}/epics/{eid}/stories`) and `search/stories` are reads.
# `/stories/bulk` is Shortcut's bulk create, so it counts too; `/stories/bulkhead` and
# `/stories/bulk/x` do not.
BARE_STORIES_PATH_RE = re.compile(
    r"""(?:(?<=["'])|(?<=v3)|(?<=\})|(?<=%s)|(?<=\)s))/stories(?:(?![\w/-])|/bulk(?![\w/-]))""",
    re.IGNORECASE,
)
_LIST_PARENT_RE = re.compile(
    r"""/(?:epics|iterations|groups|labels|milestones|objectives|projects|members|workflows)/[^/\s"']*$""",
    re.IGNORECASE,
)


# Where one shell statement ends: `;`, `&&`, `||`, `|` or a newline that is not a backslash
# continuation. A quoted `;` inside a body also splits, which only narrows the segment.
_STATEMENT_BREAK_RE = re.compile(r"(?<!\\)\r?\n|;|&&|\|\|?")
# `-X PUT`, `--request DELETE`, `-Method Put`: a verb other than POST on a REST call.
NON_POST_VERB_RE = re.compile(r"(?:-X\s*|--request\s+|-Method\s+[\"']?)(?:PUT|PATCH|DELETE|GET)\b", re.IGNORECASE)


def bulk_is_not_a_post(command: str, pos: int) -> bool:
    """Whether the `/stories/bulk` URL at `pos` sits in a statement that names a non-POST verb,
    which makes it a bulk update or delete. Only that statement counts: a PUT elsewhere in the
    command says nothing about this call."""
    start = 0
    for m in _STATEMENT_BREAK_RE.finditer(command, 0, pos):
        start = m.end()
    nxt = _STATEMENT_BREAK_RE.search(command, pos)
    return bool(NON_POST_VERB_RE.search(command[start:nxt.start() if nxt else len(command)]))


def has_bare_stories_path(command: str, bulk: bool = True) -> bool:
    """Whether `command` names the story-create path, not a story list under a parent resource.
    `bulk=False` leaves `/stories/bulk` out, for a caller that saw no POST: only a POST there
    creates, a PUT or DELETE updates or deletes."""
    return any(
        not _LIST_PARENT_RE.search(command[:m.start()]) and (bulk or not m.group(0).lower().endswith("/bulk"))
        for m in BARE_STORIES_PATH_RE.finditer(command)
    )


def _call_args(command: str, open_idx: int) -> list:
    """Top-level arguments of the call whose `(` sits at `open_idx`, split on commas outside
    nested brackets and quotes. A heuristic reader for one-liners, not a Python parser. A
    string inside a double-quoted `python -c "..."` arrives as backslash-quote pairs; that pair
    is the quote, so apostrophes and commas inside it are plain text."""
    args, cur, depth, quote = [], [], 0, ""
    # Bounded window: a one-liner's call fits in it, and an unclosed `Request(` repeated 40k
    # times would otherwise rescan the whole string once per match.
    i, n = open_idx, min(len(command), open_idx + MAX_CALL_CHARS)
    while i < n:
        c = command[i]
        if quote:
            # Three backslashes then a quote is the script's own escaped quote (`a\"b`) as bash
            # double quotes carry it; it must not read as this string's closing pair.
            if quote.startswith("\\") and command.startswith("\\\\\\\"", i):
                cur.append(command[i:i + 4])
                i += 4
                continue
            if command.startswith(quote, i):
                cur.append(quote)
                i += len(quote)
                quote = ""
                continue
            if c == "\\" and not quote.startswith("\\") and i + 1 < n:
                cur.append(command[i:i + 2])
                i += 2
                continue
            cur.append(c)
        elif c == "\\" and i + 1 < n and command[i + 1] in "\"'":
            quote = command[i:i + 2]
            cur.append(quote)
            i += 2
            continue
        elif c in "\"'":
            quote = c
            cur.append(c)
        elif c in "([{":
            depth += 1
            if depth > 1:
                cur.append(c)
        elif c in ")]}":
            depth -= 1
            if depth <= 0:
                args.append("".join(cur))
                return args
            cur.append(c)
        elif c == "," and depth == 1:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    args.append("".join(cur))
    return args


def _urllib_sends_data(command: str) -> bool:
    """Whether some `Request(...)` / `urlopen(...)` call is given a body and no literal method
    of its own, which makes urllib POST: `data=...` anywhere after the url, or a second
    positional argument. Decided call by call: a `method='GET'` on one request says nothing
    about the body-carrying request next to it."""
    for k, m in enumerate(_URLLIB_CALL_RE.finditer(command)):
        if k >= MAX_CALLS_SCANNED:
            break
        args = _call_args(command, m.end() - 1)
        # All args, not args[1:]: `Request(method='GET', url=u, data=b)` puts the method first.
        if _METHOD_RE.search(",".join(args)):
            continue
        for pos, arg in enumerate(args[1:], start=1):
            if _DATA_ARG_RE.match(arg):
                return True
            if pos == 1 and arg.strip() and not _KWARG_RE.match(arg) and arg.strip() != "None":
                return True
    return False


_BASH_DQ_ESCAPE_RE = re.compile(r"""\\([\\"$`])""")


def python_write_verbs(command: str) -> set:
    """Upper-case HTTP write verbs (POST, PUT, PATCH, DELETE) the script calls with. A urllib
    request given a body and no method is POST, which is urllib's own default.

    A script inside a double-quoted `python -c "..."` reaches the hook with bash's escapes still
    in it (`\\"` for a quote, `\\\\` for a backslash), which no single quote-aware reader handles
    for every string the script can hold. So the command is read twice, as written and with
    those bash escapes undone, and the verbs of both reads count."""
    verbs = _verbs(command)
    if "\\" in command:
        verbs |= _verbs(_BASH_DQ_ESCAPE_RE.sub(r"\1", command))
    return verbs


def _verbs(command: str) -> set:
    verbs = {m.group(1).upper() for m in _METHOD_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _CLIENT_CALL_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _REQUEST_CALL_RE.finditer(command)}
    if _urllib_sends_data(command):
        verbs.add("POST")
    verbs.discard("GET")
    return verbs
