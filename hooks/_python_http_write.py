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
_DATA_ARG_RE = re.compile(r"\s*data\s*=(?!=)\s*(?!None\b)")
_KWARG_RE = re.compile(r"\s*\w+\s*=(?!=)")

# Evidence that the script talks to Shortcut even when the URL is assembled from pieces: the
# host, or the token plumbing (`kickoff.env()`, the env var, the header name).
SHORTCUT_HINT_RE = re.compile(
    r"api\.app\.shortcut\.com|SHORTCUT_API_TOKEN|kickoff\.env|Shortcut-Token",
    re.IGNORECASE,
)

# The create path `/stories`: after a quote (`API + '/stories'`), `v3` (the literal URL) or `}`
# (`f"{API}/stories"`). `/epics/5/stories`, `/iterations/2/stories` and `search/stories` are
# reads of a story list, so a bare `/stories` anywhere else must not count.
BARE_STORIES_PATH_RE = re.compile(r"""(?:(?<=["'])|(?<=v3)|(?<=\}))/stories(?![\w/-])""", re.IGNORECASE)


def _call_args(command: str, open_idx: int) -> list:
    """Top-level arguments of the call whose `(` sits at `open_idx`, split on commas outside
    nested brackets and quotes. A heuristic reader for one-liners, not a Python parser."""
    args, cur, depth, quote = [], [], 0, ""
    i, n = open_idx, len(command)
    while i < n:
        c = command[i]
        if quote:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(command[i + 1])
                i += 1
            elif c == quote:
                quote = ""
        elif c == "\\" and i + 1 < n and command[i + 1] in "\"'":
            cur.append(c + command[i + 1])
            i += 1
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
    """Whether some `Request(...)` / `urlopen(...)` call is given a body, which makes urllib
    POST: `data=...` anywhere after the url, or a second positional argument."""
    for m in _URLLIB_CALL_RE.finditer(command):
        args = _call_args(command, m.end() - 1)
        for pos, arg in enumerate(args[1:], start=1):
            if _DATA_ARG_RE.match(arg):
                return True
            if pos == 1 and arg.strip() and not _KWARG_RE.match(arg) and arg.strip() != "None":
                return True
    return False


def python_write_verbs(command: str) -> set:
    """Upper-case HTTP write verbs (POST, PUT, PATCH, DELETE) the script calls with. A urllib
    request given a body and no method is POST, which is urllib's own default."""
    verbs = {m.group(1).upper() for m in _METHOD_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _CLIENT_CALL_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _REQUEST_CALL_RE.finditer(command)}
    if not _METHOD_RE.search(command) and _urllib_sends_data(command):
        verbs.add("POST")
    verbs.discard("GET")
    return verbs
