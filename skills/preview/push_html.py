"""Push an HTML file to Conductor's preview panel with this chat's session id.

Usage: python push_html.py <file.html> --slug <slug> --title <title> [--source terminal|chat]

The panel scopes a push to the chat that sent it, so a body without session_id never shows up
anywhere. Hand-written POSTs forgot it (2026-11-05: seven in a row, the first without it, and
Joe kept seeing the previous board). This script refuses to post when CLAUDE_CODE_SESSION_ID is
unset or empty, so the omission cannot happen.

A push under the slug already open in the panel replaces it in place and the panel follows it;
a new slug only adds a dot to the picker.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "http://127.0.0.1:27182/hooks/preview"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("html_file")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--source", choices=("terminal", "chat"), default="terminal")
    ap.add_argument("--endpoint", default=ENDPOINT, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if not session_id:
        print(
            "push_html: CLAUDE_CODE_SESSION_ID is not set; a push without session_id never "
            "shows in any chat's panel, so nothing was posted",
            file=sys.stderr,
        )
        return 2
    try:
        with open(args.html_file, encoding="utf-8") as f:
            html = f.read()
    except (OSError, UnicodeDecodeError) as e:  # a non-UTF-8 file is as unreadable as a missing one
        print(f"push_html: cannot read {args.html_file}: {e}", file=sys.stderr)
        return 2

    body = json.dumps(
        {"title": args.title, "slug": args.slug, "html": html, "source": args.source, "session_id": session_id}
    ).encode("utf-8")
    req = urllib.request.Request(
        args.endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status, text = resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        print(f"push_html: Conductor not reachable on {args.endpoint}: {e.reason}", file=sys.stderr)
        return 3

    if status != 200:
        print(f"push_html: HTTP {status}: {text}", file=sys.stderr)
        return 1
    try:
        print(json.loads(text).get("id", text))
    except (json.JSONDecodeError, AttributeError):
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
