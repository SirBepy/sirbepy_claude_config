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
_CLIENT_CALL_RE = re.compile(r"\b(?:requests|httpx)\.(post|put|patch)\s*\(", re.IGNORECASE)
_REQUEST_CALL_RE = re.compile(r"""\.request\s*\(\s*\\?["']\s*(POST|PUT|PATCH)\b""", re.IGNORECASE)
_URLLIB_RE = re.compile(r"\burllib\b")
_DATA_KWARG_RE = re.compile(r"\bdata\s*=")

# Evidence that the script talks to Shortcut even when the URL is assembled from pieces: the
# host, or the token plumbing (`kickoff.env()`, the env var, the header name).
SHORTCUT_HINT_RE = re.compile(
    r"api\.app\.shortcut\.com|SHORTCUT_API_TOKEN|kickoff\.env|Shortcut-Token",
    re.IGNORECASE,
)


def python_write_verbs(command: str) -> set:
    """Upper-case HTTP write verbs (POST, PUT, PATCH, DELETE) the script calls with. A urllib
    request given `data=` and no method is POST, which is urllib's own default."""
    verbs = {m.group(1).upper() for m in _METHOD_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _CLIENT_CALL_RE.finditer(command)}
    verbs |= {m.group(1).upper() for m in _REQUEST_CALL_RE.finditer(command)}
    if _URLLIB_RE.search(command) and _DATA_KWARG_RE.search(command) and not _METHOD_RE.search(command):
        verbs.add("POST")
    verbs.discard("GET")
    return verbs
