"""Stop hook: flag a cc-status/cc-title marker that is PRESENT but malformed
(mixed colon/XML style, or a cc-status value outside done|question|waiting|
working). Missing markers are enforced elsewhere (the Conductor daemon's own
/hooks/stop); this hook only catches malformed present ones, so it stays a
no-op in every project that never emits these markers. Canonical forms from
TURN_STATUS_PROMPT: colon form closes with '>' (<cc-status:done>), XML form
is <cc-status>done</cc-status> - never mixed. Fails open on any error.
"""

import json
import re
import sys

STATUS_VALUES = {"done", "question", "waiting", "working"}
TAG_RE = re.compile(r"<cc-(status|title)\b", re.IGNORECASE)


def colon_match(text: str, pos: int, tag: str):
    return re.match(r"<cc-%s:([^<>]*)>" % tag, text[pos:], re.IGNORECASE)


def xml_match(text: str, pos: int, tag: str):
    return re.match(r"<cc-%s>([^<>]*)</cc-%s>" % (tag, tag), text[pos:], re.IGNORECASE)


def check(text: str) -> list:
    violations = []
    for m in TAG_RE.finditer(text):
        tag = m.group(1).lower()
        pos = m.start()
        colon = colon_match(text, pos, tag)
        xml = xml_match(text, pos, tag)
        if colon:
            value = colon.group(1).strip()
        elif xml:
            value = xml.group(1).strip()
        else:
            snippet = text[pos:pos + 40].replace("\n", " ")
            violations.append(
                'malformed <cc-%s> marker (mixed colon/XML style): "%s..."' % (tag, snippet)
            )
            continue
        # A quoted spec like <cc-status:done|question|waiting|working> is an
        # instruction echo, not a real attempt - never flag it as bogus.
        if tag == "status" and "|" not in value and value.lower() not in STATUS_VALUES:
            violations.append(
                '<cc-status> has an unrecognised value "%s" (expected one of '
                "done, question, waiting, working)" % value
            )
    return violations


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    if payload.get("stop_hook_active") is True:
        sys.exit(0)
    text = payload.get("last_assistant_message")
    if not text:
        sys.exit(0)
    violations = check(text)
    if violations:
        print(json.dumps({
            "decision": "block",
            "reason": (
                "Malformed status marker(s) - use exactly one style, colon form "
                "closes with '>' like <cc-status:done>, XML form is "
                "<cc-status>done</cc-status>, never mixed: " + "; ".join(violations)
            ),
        }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write("[status-marker-guard] hook error, failing open: %s\n" % e)
        sys.exit(0)
