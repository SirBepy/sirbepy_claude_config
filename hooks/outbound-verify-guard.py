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
    from _hooklib import read_payload, deny, basename, tokenize_command
    from _outbound_verify_transcript import (
        MIN_PROSE_CHARS,
        REQUIRED_PASSES,
        load_verdicts,
        normalize,
        uncovered,
    )
except Exception as e:
    sys.stderr.write(f"[outbound-verify-guard] FATAL: cannot import a sibling hook module ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_OUTBOUND_VERIFY_BYPASS"
PROSE_KEYS = ("name", "description", "text", "title", "body")

# Cheap gate so the ~every-shell-call matcher costs a regex, not a tokenize.
SHELL_PREFILTER_RE = re.compile(r"shortcut\.com|linear\.app|github\.com|\bgh(?:\.exe)?\b", re.IGNORECASE)

SHORTCUT_TOOL_RE = re.compile(r"^mcp__shortcut__stories-(create|update|create-comment|create-subtask|add-task|update-task)$")
LINEAR_TOOL_RE = re.compile(r"^mcp__.*linear.*__.*(create_issue|issue.?create|update_issue|issue.?update|create_comment|comment.?create|save_issue|save_comment).*$", re.IGNORECASE)
GITHUB_TOOL_RE = re.compile(r"^mcp__.*github.*__(?!get_|list_|search_)\w*(pull_request|comment|review)\w*$", re.IGNORECASE)
# Creating something or commenting always carries text; an update may only move state.
MCP_REQUIRES_PROSE_RE = re.compile(r"stories-create(-comment)?$|create_issue|issue.?create|comment|create_pull_request$", re.IGNORECASE)

SHORTCUT_URL_RE = re.compile(r"api\.app\.shortcut\.com/api/v3/stories(?P<rest>(?:/[\w-]+)*)", re.IGNORECASE)
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


def is_http_write(command: str) -> bool:
    if WRITE_VERB_RE.search(command):
        return True
    return bool(DATA_FLAG_RE.search(command)) and not GET_FLAG_RE.search(command)


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
        found = prose_from_body(read_file(path, cwd), values) or found
    # A PowerShell hashtable piped through ConvertTo-Json never surfaces as a -Body literal.
    if not found:
        found = regex_prose(command, values)
    return values, found


def detect_rest(command: str, tokens: list, cwd: str | None) -> Outbound | None:
    shortcut = SHORTCUT_URL_RE.search(command)
    linear = LINEAR_URL_RE.search(command)
    github = GITHUB_URL_RE.search(command)
    if not (shortcut or linear or github):
        return None
    if not is_http_write(command):
        return None

    if shortcut:
        rest = shortcut.group("rest")
        requires = rest == "" or bool(re.fullmatch(r"/\d+/comments", rest))
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
    return detect_rest(command, tokens, cwd)


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
