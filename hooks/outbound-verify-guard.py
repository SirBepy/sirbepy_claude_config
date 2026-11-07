"""PreToolUse hook: block outbound prose until 3 fresh subagents verified that exact text.

Covers ticket writes (Shortcut, Linear: create, text-rewriting update, comment) and GitHub
PR writes (create, title/body edit, comment, review with a body). The procedure that
satisfies it lives in `refs/outbound-verify.md`.

No marker file on purpose: a marker is something Claude can write without dispatching
anyone. The proof is read from the session transcript (`transcript_path` in the payload)
instead, where Claude cannot author entries:

- a verifier is an Agent/Task dispatch (never `subagent_type: "fork"`, which inherits the
  session's context and so is not independent) whose prompt carries the text between
  `<<<OUTBOUND-DRAFT` and `OUTBOUND-DRAFT>>>` lines;
- its verdict is the last `OUTBOUND-VERDICT: PASS|FAIL` line of its returned report, found
  in the Agent tool_result or in the `<agent-message from="<agentId>">` hand-back the
  harness delivers for sync and async dispatches alike.

A draft is cleared at 3 PASS and zero FAIL. A single FAIL poisons that exact text for good,
so re-rolling verifiers until three agree cannot work; the text has to change.

Every prose field the call sends (title, body, description, comment text) of at least
MIN_PROSE_CHARS must sit inside one cleared draft, compared whitespace-normalized and
otherwise exact, so a typo fix after verification needs a new round. Shorter values (label
names, a "WIP" title) are skipped: the nested `name` keys in a ticket payload are labels,
and gating those would make every create fail on text nobody would ever verify.

Known false positive, shared with the ground-check guards: matching is on the command
STRING, so a command that merely mentions an endpoint and a write verb is checked too.

Override: set CLAUDE_OUTBOUND_VERIFY_BYPASS=1 in the session environment if this hook
itself is broken; an inline prefix on the command never reaches it.

Module layout (todo 1088): this file stays outbound-call detection (`Outbound`, the
`detect_*` functions) and `main()`. The transcript-verdict tally (whether 3 independent
PASS verdicts cover a given text) lives in the sibling `_outbound_verify_transcript.py`,
imported below alongside `_hooklib`.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, basename, strip_quotes, tokenize_command, without_display_segments
    from _outbound_verify_transcript import (
        MIN_PROSE_CHARS,
        REQUIRED_PASSES,
        load_verdicts,
        normalize,
        uncovered,
    )
    from _outbound_window import window_denial
    from _python_http_write import SHORTCUT_HINT_RE, python_write_verbs
except Exception as e:
    sys.stderr.write(f"[outbound-verify-guard] FATAL: cannot import a sibling hook module ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_OUTBOUND_VERIFY_BYPASS"
PROSE_KEYS = ("name", "description", "text", "title", "body")

# Cheap gate so the ~every-shell-call matcher costs a regex, not a tokenize.
# The Shortcut token names are there for python scripts that build their URL from a base.
SHELL_PREFILTER_RE = re.compile(
    r"shortcut\.com|linear\.app|github\.com|\bgh(?:\.exe)?\b|SHORTCUT_API_TOKEN|kickoff\.env|Shortcut-Token",
    re.IGNORECASE,
)

SHORTCUT_TOOL_RE = re.compile(r"^mcp__shortcut__stories-(create|update|create-comment|create-subtask|add-task|update-task)$")
LINEAR_TOOL_RE = re.compile(r"^mcp__.*linear.*__.*(create_issue|issue.?create|update_issue|issue.?update|create_comment|comment.?create|save_issue|save_comment).*$", re.IGNORECASE)
GITHUB_TOOL_RE = re.compile(r"^mcp__.*github.*__(?!get_|list_|search_)\w*(pull_request|comment|review)\w*$", re.IGNORECASE)
# Creating something or commenting always carries text; an update may only move state.
MCP_REQUIRES_PROSE_RE = re.compile(r"stories-create(-comment)?$|create_issue|issue.?create|comment|create_pull_request$", re.IGNORECASE)

# A path segment may be a literal id or an unexpanded shell variable (`$id`, `${id}`,
# `$($s.id)`): the hook reads the command string before the shell expands it, and a segment
# that stopped at `$` would leave `rest` empty, the shape of a bare `POST /stories` create.
SHORTCUT_URL_RE = re.compile(
    r"api\.app\.shortcut\.com/api/v3/stories"
    r"(?P<rest>(?:/(?:[\w.~%-]|\$\{[^}\s\"']*\}|\$\([^)\"']*\)|\$)+)*)",
    re.IGNORECASE,
)
LINEAR_URL_RE = re.compile(r"api\.linear\.app/graphql", re.IGNORECASE)
LINEAR_REQUIRES_RE = re.compile(r"\b(issueCreate|commentCreate)\b")
LINEAR_GATED_RE = re.compile(r"\b(issueCreate|commentCreate|issueUpdate|commentUpdate)\b")
GITHUB_URL_RE = re.compile(r"api\.github\.com/(?P<path>repos/[^\s\"'?]+)", re.IGNORECASE)
GITHUB_PATH_RE = re.compile(r"repos/[^/]+/[^/]+/(?:pulls\b|issues/(?:\d+/comments|comments/\d+)\b)")
GITHUB_PATH_REQUIRES_RE = re.compile(r"(?:/comments(?:/\d+/replies)?|/pulls)$")
GITHUB_GRAPHQL_RE = re.compile(
    r"\b(createPullRequest|updatePullRequest|addComment|addPullRequestReview|addPullRequestReviewComment|"
    r"addPullRequestReviewThread|addPullRequestReviewThreadReply|submitPullRequestReview|updateIssueComment|"
    r"updatePullRequestReviewComment)\b"
)

WRITE_VERB_RE = re.compile(
    r"(?:-X\s*[\"']?(POST|PUT|PATCH)\b|--request\s+[\"']?(POST|PUT|PATCH)\b|-Method\s+[\"']?(Post|Put|Patch)\b)",
    re.IGNORECASE,
)
DATA_FLAG_RE = re.compile(r"(?:^|\s)(?:-d\b|--data(?:-raw|-binary|-urlencode)?\b|--json\b)", re.IGNORECASE)
GET_FLAG_RE = re.compile(r"(?:^|\s)(?:-G\b|--get\b)", re.IGNORECASE)
# One argv token that is a curl data flag: `-d`, a short cluster like `-sd`, an attached value
# like `-d{...}` / `-d@file`, or a long form. The cluster is capped at 4 letters before the d
# so PowerShell's `-Method` / `-Header` never read as `-d`.
DATA_TOKEN_RE = re.compile(
    r"-[A-Za-z]{0,4}[dD](?![A-Za-z])|--(?:data(?:-raw|-binary|-urlencode|-ascii)?|json)(?:=|$)",
)
# Commands whose `-d` means something other than an HTTP body (delimiter, delete, date).
NON_HTTP_COMMANDS = {"cut", "tr", "sort", "uniq", "date", "head", "tail", "grep", "egrep", "fgrep", "du", "wc", "ls", "tee"}
# Words that precede the real command in a segment without being it.
COMMAND_PREFIX_WORDS = {"do", "then", "else", "elif", "if", "while", "until", "time", "!", "{", "command", "sudo", "nohup", "exec", "env"}
SHELL_PUNCT = set("();&|<>")

PROSE_KV_RE = re.compile(
    r"[\"']?\b(?:name|description|text|title|body)\b[\"']?\s*[:=]\s*"
    r"(?:@\"\r?\n(?P<here2>.*?)\r?\n\"@|@'\r?\n(?P<here1>.*?)\r?\n'@"
    r"|\"(?P<dq>(?:[^\"\\]|\\.)*)\"|'(?P<sq>(?:[^'\\]|\\.)*)')",
    re.DOTALL | re.IGNORECASE,
)

SEPARATORS = {"|", "||", "&&", ";", "&"}
GH_GLOBAL_VALUE_FLAGS = {"-R", "--repo", "--hostname"}
GH_PR_TEXT_FLAGS = ("--title", "-t", "--body", "-b")
GH_PR_FILE_FLAGS = ("--body-file", "-F")
GH_API_VALUE_FLAGS = {
    "-X", "--method", "-f", "--raw-field", "-F", "--field", "-H", "--header", "--input",
    "-q", "--jq", "-t", "--template", "--hostname", "-p", "--preview", "--cache",
}
CURL_DATA_FLAGS = ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "--json")


class Unverifiable(Exception):
    """The call's text lives somewhere this hook cannot read (stdin, a missing file)."""


class Outbound:
    def __init__(self, label: str, values: list, requires_prose: bool, found_any: bool):
        self.label = label
        self.values = values
        self.requires_prose = requires_prose
        self.found_any = found_any


def collect_prose(obj, out: list) -> bool:
    """Append every string under a prose key, at any depth. Returns whether any prose key
    was present at all, so a create whose text is empty still counts as having one."""
    found = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str) and key.lower() in PROSE_KEYS and isinstance(value, str):
                out.append(value)
                found = True
            elif isinstance(value, (dict, list)):
                found = collect_prose(value, out) or found
            if isinstance(key, str) and key.lower() == "query" and isinstance(value, str):
                found = regex_prose(value, out) or found
    elif isinstance(obj, list):
        for item in obj:
            found = collect_prose(item, out) or found
    return found


def unescape_dq(value: str) -> str:
    try:
        return json.loads('"' + value + '"')
    except ValueError:
        return value


def regex_prose(text: str, out: list) -> bool:
    found = False
    for m in PROSE_KV_RE.finditer(text):
        if m.group("dq") is not None:
            out.append(unescape_dq(m.group("dq")))
        elif m.group("sq") is not None:
            out.append(m.group("sq").replace("\\'", "'"))
        else:
            out.append(m.group("here2") if m.group("here2") is not None else m.group("here1"))
        found = True
    return found


def prose_from_body(body: str, out: list) -> bool:
    try:
        parsed = json.loads(body)
    except ValueError:
        return regex_prose(body, out)
    return collect_prose(parsed, out)


MSYS_DRIVE_RE = re.compile(r"^/([A-Za-z])/")


def read_file(path: str, cwd: str | None) -> str:
    if path in ("-", ""):
        raise Unverifiable("the text is piped from stdin")
    if os.name == "nt":
        m = MSYS_DRIVE_RE.match(path)
        if m:
            path = f"{m.group(1).upper()}:/{path[m.end():]}"
    p = Path(os.path.expanduser(path))
    if not p.is_absolute() and cwd:
        p = Path(cwd) / p
    try:
        return p.read_text(encoding="utf-8-sig")
    except OSError:
        raise Unverifiable(f"cannot read the body file {path}")


def split_tokens(command: str, posix: bool) -> list:
    """posix for Bash, where backslash escapes. PowerShell escapes with a backtick, and a
    posix split would eat the backslashes out of every Windows body-file path."""
    if not posix:
        return tokenize_command(command)
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return tokenize_command(command)


def flag_values(args: list, names) -> list:
    out = []
    k = 0
    while k < len(args):
        arg = args[k]
        for name in names:
            if arg == name and k + 1 < len(args):
                out.append(args[k + 1])
                k += 1
                break
            if name.startswith("--") and arg.startswith(name + "="):
                out.append(arg[len(name) + 1:])
                break
        k += 1
    return out


def gh_calls(tokens: list):
    """Yield (subcommand, args) for each `gh <sub> ...`, args stopping at a separator."""
    for i, tok in enumerate(tokens):
        if basename(tok) not in ("gh", "gh.exe"):
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            j += 2 if tokens[j] in GH_GLOBAL_VALUE_FLAGS else 1
        if j >= len(tokens):
            continue
        args = []
        for t in tokens[j + 1:]:
            if t in SEPARATORS:
                break
            args.append(t)
        yield tokens[j], args


def detect_gh_pr(args: list, cwd: str | None) -> Outbound | None:
    action = next((a for a in args if not a.startswith("-")), None)
    if action not in ("create", "edit", "comment", "review"):
        return None
    values = flag_values(args, GH_PR_TEXT_FLAGS)
    values += [read_file(p, cwd) for p in flag_values(args, GH_PR_FILE_FLAGS)]
    found = bool(values)
    # An edit of labels/reviewers, or an approve with no body, says nothing.
    if action in ("edit", "review") and not found:
        return None
    return Outbound(f"gh pr {action}", values, action in ("create", "comment"), found)


def detect_gh_api(args: list, cwd: str | None) -> Outbound | None:
    endpoint, method, fields, inputs = None, None, [], []
    k = 0
    while k < len(args):
        arg = args[k]
        if arg in GH_API_VALUE_FLAGS and k + 1 < len(args):
            value = args[k + 1]
            if arg in ("-X", "--method"):
                method = value.upper()
            elif arg in ("-f", "--raw-field", "-F", "--field"):
                fields.append((arg, value))
            elif arg == "--input":
                inputs.append(value)
            k += 2
            continue
        if not arg.startswith("-") and endpoint is None:
            endpoint = arg.lstrip("/")
        k += 1
    if endpoint is None:
        return None
    if method is None:
        method = "POST" if fields or inputs else "GET"
    if method not in ("POST", "PATCH", "PUT"):
        return None

    values: list = []
    found = False
    for flag, field in fields:
        key, _, value = field.partition("=")
        if flag in ("-F", "--field") and value.startswith("@"):
            value = read_file(value[1:], cwd)
        if key.lower() in PROSE_KEYS:
            values.append(value)
            found = True
        elif key.lower() == "query":
            found = regex_prose(value, values) or found
    for path in inputs:
        found = prose_from_body(read_file(path, cwd), values) or found

    if endpoint == "graphql":
        if not GITHUB_GRAPHQL_RE.search(" ".join(v for _, v in fields) + " ".join(values)):
            return None
        return Outbound("gh api graphql", values, False, found)
    if not GITHUB_PATH_RE.search(endpoint):
        return None
    requires = method == "POST" and bool(GITHUB_PATH_REQUIRES_RE.search(endpoint.split("?")[0]))
    if not requires and not found:
        return None
    return Outbound(f"gh api {method} {endpoint}", values, requires, found)


def newlines_to_separators(command: str, posix: bool) -> str:
    """An unquoted line break ends a statement just like `;`, but shlex treats it as plain
    whitespace, so `ls\\ncurl -d ...` would read as one `ls` command and hide the curl's data
    flag. Quoted newlines (multi-line strings, PowerShell here-strings) are left alone, and an
    escaped one (`\\` in Bash, a backtick in PowerShell) is a line continuation, i.e. a space."""
    out: list = []
    quote = ""
    escape = "\\" if posix else "`"
    i, n = 0, len(command)
    while i < n:
        c = command[i]
        if quote:
            if c == quote:
                quote = ""
            elif c == escape and quote == '"' and i + 1 < n:
                out.append(c)
                i += 1
                c = command[i]
            out.append(c)
        elif c in "\"'":
            quote = c
            out.append(c)
        elif c == escape and i + 1 < n:
            if command[i + 1] in "\r\n":
                i += 2 if command.startswith("\r\n", i + 1) else 1
                out.append(" ")
            else:
                out.append(c + command[i + 1])
                i += 1
        elif c in "\r\n":
            if c == "\r" and command.startswith("\n", i + 1):
                i += 1
            out.append(" ; ")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def shell_segments(command: str, posix: bool) -> list | None:
    """The command's tokens grouped per simple command, split on ; | & ( ) < > and unquoted
    line breaks even when they touch a word (`$s|python`, `done;`), which a plain shlex split
    leaves glued on. None when the quoting does not parse."""
    lex = shlex.shlex(newlines_to_separators(command, posix), posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        tokens = list(lex)
    except ValueError:
        return None
    segments: list = [[]]
    for tok in tokens:
        if tok and all(c in SHELL_PUNCT for c in tok):
            segments.append([])
        else:
            segments[-1].append(strip_quotes(tok) if not posix else tok)
    return segments


def segment_has_data_flag(segment: list) -> bool:
    k = 0
    while k < len(segment) and (re.match(r"\w+=", segment[k]) or segment[k] in COMMAND_PREFIX_WORDS):
        k += 1
    if k >= len(segment) or basename(segment[k]) in NON_HTTP_COMMANDS:
        return False
    for tok in segment[k + 1:]:
        if DATA_TOKEN_RE.match(tok):
            return True
        # A nested shell string (`bash -c "curl -d ..."`) is one token holding its own flags.
        if re.search(r"\s", tok) and DATA_FLAG_RE.search(tok):
            return True
    return False


def has_http_data_flag(command: str, posix: bool) -> bool:
    """Whether some command in the string carries a curl-style data flag. Tested per command
    rather than on the whole string: `cut -d=` and `tr -d` in a token-extraction pipeline are
    not request bodies. An unparseable string falls back to the whole-string match."""
    segments = shell_segments(command, posix)
    if segments is None:
        return bool(DATA_FLAG_RE.search(command))
    return any(segment_has_data_flag(s) for s in segments)


def is_http_write(command: str, posix: bool = True) -> bool:
    if WRITE_VERB_RE.search(command):
        return True
    # An inline python script names its verb in the call (`method='POST'`, `requests.post(`).
    if python_write_verbs(command) & {"POST", "PUT", "PATCH"}:
        return True
    return has_http_data_flag(command, posix) and not GET_FLAG_RE.search(command)


def rest_prose(command: str, tokens: list, cwd: str | None) -> tuple:
    values: list = []
    found = False
    for body in flag_values(tokens, CURL_DATA_FLAGS):
        if body.startswith("@"):
            body = read_file(body[1:], cwd)
        found = prose_from_body(body, values) or found
    # No @file form here: a leading @ on a PowerShell -Body is an inline hashtable.
    for body in flag_values(tokens, ("-Body", "-body")):
        found = prose_from_body(body, values) or found
    for path in flag_values(tokens, ("-InFile", "-infile")):
        # PowerShell statement punctuation stays glued to an unquoted path token.
        found = prose_from_body(read_file(path.rstrip(";,)"), cwd), values) or found
    # A PowerShell hashtable piped through ConvertTo-Json never surfaces as a -Body literal.
    if not found:
        found = regex_prose(command, values)
    # `python -c "...{\"text\": \"...\"}..."`: the quotes of the script's own strings arrive escaped.
    if not found and '\\"' in command:
        found = regex_prose(command.replace('\\"', '"'), values)
    return values, found


URL_PATH_END_CHARS = set(" \t\r\n\"'?#);|&<>")
CLOSERS = {"(": ")", "{": "}"}


def shortcut_path_segments(command: str, start: int) -> list | None:
    """The URL path after `/stories` split on top-level slashes, scanned from `start` with
    `$(...)`, `${...}` and backtick spans kept whole (nesting and inner spaces included), since
    the hook sees the command before the shell expands it. None when an expansion never closes."""
    segments: list = [""]
    i, n = start, len(command)
    while i < n:
        c = command[i]
        if c in URL_PATH_END_CHARS:
            break
        if c == "$" and i + 1 < n and command[i + 1] in CLOSERS:
            opener, depth, j = command[i + 1], 1, i + 2
            while j < n and depth:
                depth += (command[j] == opener) - (command[j] == CLOSERS[opener])
                j += 1
            if depth:
                return None
            segments[-1] += command[i:j]
            i = j
            continue
        if c == "`":
            j = command.find("`", i + 1)
            if j < 0:
                return None
            segments[-1] += command[i:j + 1]
            i = j + 1
            continue
        if c == "/":
            segments.append("")
        else:
            segments[-1] += c
        i += 1
    return segments


def shortcut_requires_prose(command: str, match: re.Match) -> bool:
    """True when the call may create a story or comment (text required). Unknown reads as
    gated: only a literal or single-expansion id optionally followed by literal non-comment
    segments is a known read/update shape."""
    segments = shortcut_path_segments(command, match.start("rest"))
    # segments[0] is whatever touches `/stories` before the first slash; a bare create has none.
    if segments is None or segments[0] != "" or len(segments) < 2:
        return True
    ids = segments[1:]
    if not ids[0]:
        return True
    tail = ids[1:]
    if any("$" in s or "`" in s for s in tail):
        return True
    # `/comments` or `/comments/` posts a comment; any other literal tail is not prose-creating.
    return bool(tail) and tail[0].lower() == "comments" and not any(tail[1:])


# A python script often builds the URL from a base (`API + "/stories"`), so SHORTCUT_URL_RE misses
# it. Only a bare `/stories` or anything under `/comments` is known to carry prose; an id-only
# write (`/stories/<id>` with a state id) stays ungated unless its text is found.
PY_SHORTCUT_PROSE_PATH_RE = re.compile(r"(?<!search)/stories(?![\w/-])|/comments", re.IGNORECASE)
PY_SHORTCUT_STORIES_RE = re.compile(r"(?<!search)/stories\b", re.IGNORECASE)


def python_shortcut_write(command: str) -> bool:
    return bool(
        python_write_verbs(command) & {"POST", "PUT", "PATCH"}
        and SHORTCUT_HINT_RE.search(command)
        and PY_SHORTCUT_STORIES_RE.search(command)
    )


def detect_rest(command: str, tokens: list, cwd: str | None, posix: bool = True) -> Outbound | None:
    # `echo "curl -X POST <url> -d x"` or a commit message quoting one names a
    # request without sending it, so those statements are left out of the read.
    command = without_display_segments(command)
    shortcut = SHORTCUT_URL_RE.search(command)
    linear = LINEAR_URL_RE.search(command)
    github = GITHUB_URL_RE.search(command)
    py_shortcut = not (shortcut or linear or github) and python_shortcut_write(command)
    if not (shortcut or linear or github or py_shortcut):
        return None
    if not is_http_write(command, posix):
        return None
    if py_shortcut:
        requires = bool(PY_SHORTCUT_PROSE_PATH_RE.search(command))
        label = "Shortcut REST write (python)"
    elif shortcut:
        requires = shortcut_requires_prose(command, shortcut)
        label = "Shortcut REST write"
    elif linear:
        if not LINEAR_GATED_RE.search(command):
            return None
        requires = bool(LINEAR_REQUIRES_RE.search(command))
        label = "Linear GraphQL write"
    else:
        path = github.group("path")
        if not GITHUB_PATH_RE.search(path):
            return None
        requires = bool(GITHUB_PATH_REQUIRES_RE.search(path))
        label = "GitHub REST write"

    values, found = rest_prose(command, tokens, cwd)
    if not requires and not found:
        return None
    return Outbound(label, values, requires, found)


def detect_shell(command: str, cwd: str | None, posix: bool) -> Outbound | None:
    if not SHELL_PREFILTER_RE.search(command):
        return None
    tokens = split_tokens(command, posix)
    for sub, args in gh_calls(tokens):
        if sub == "pr":
            hit = detect_gh_pr(args, cwd)
        elif sub == "api":
            hit = detect_gh_api(args, cwd)
        else:
            hit = None
        if hit:
            return hit
    return detect_rest(command, tokens, cwd, posix)


def detect(tool_name: str, tool_input: dict, cwd: str | None) -> Outbound | None:
    if tool_name in ("Bash", "PowerShell"):
        return detect_shell(tool_input.get("command", "") or "", cwd, tool_name == "Bash")
    if SHORTCUT_TOOL_RE.match(tool_name) or LINEAR_TOOL_RE.match(tool_name) or GITHUB_TOOL_RE.match(tool_name):
        values: list = []
        found = collect_prose(tool_input, values)
        requires = bool(MCP_REQUIRES_PROSE_RE.search(tool_name))
        if not requires and not found:
            return None
        return Outbound(tool_name, values, requires, found)
    return None


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}

    try:
        outbound = detect(tool_name, tool_input, payload.get("cwd"))
    except Unverifiable as e:
        if os.environ.get(OVERRIDE_ENV):
            sys.exit(0)
        deny(
            f"[outbound-verify-guard] Outbound write blocked: {e}, so the 3-verifier check "
            "cannot see what is being posted. Put the text in the command or in a readable "
            "body file. See refs/outbound-verify.md."
        )
    if outbound is None or os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    night = window_denial(payload, outbound.label)
    if night:
        deny(night)

    if outbound.requires_prose and not outbound.found_any:
        deny(
            f"[outbound-verify-guard] {outbound.label} blocked: its text is not visible in the "
            "call (a variable, --fill, or an editor), so the 3-verifier check cannot match it. "
            "Put the text literally in the command or a body file. See refs/outbound-verify.md."
        )

    checked = [v for v in outbound.values if len(normalize(v)) >= MIN_PROSE_CHARS]
    if not checked:
        sys.exit(0)

    transcript_path = payload.get("transcript_path") or ""
    if not transcript_path or not os.path.isfile(transcript_path):
        sys.stderr.write("[outbound-verify-guard] no readable transcript_path in payload, failing open.\n")
        sys.exit(0)

    misses = uncovered(checked, load_verdicts(transcript_path))
    if not misses:
        sys.exit(0)

    lines = "\n".join(f'  - "{snippet}": {reason}' for snippet, reason in misses)
    deny(
        f"[outbound-verify-guard] {outbound.label} blocked: this text has not been verified by "
        f"{REQUIRED_PASSES} independent subagents with zero FAIL.\n{lines}\n"
        "Follow refs/outbound-verify.md: dispatch 3 identical non-fork verifiers whose prompt "
        "carries the exact text between <<<OUTBOUND-DRAFT and OUTBOUND-DRAFT>>> lines, each ending "
        "its report with OUTBOUND-VERDICT: PASS or FAIL. Any edit after verification, even a typo, "
        "needs a new round; a FAIL means fix the claim and verify the new text. "
        f"If this hook itself is broken, set {OVERRIDE_ENV}=1 in the session environment."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[outbound-verify-guard] hook error, failing open: {e}\n")
        sys.exit(0)
