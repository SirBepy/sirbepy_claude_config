"""Stop hook (todo 410): catch a whole silent stretch, not a single quiet turn.

Confirmed 2026-09-04: no hook anywhere enforced the send_message obligation; a
2026-09-03 incident saw three consecutive turns end via report_turn_status with
no mcp__cc_conductor__send_message and nothing blocked them.

Only turns carrying a Conductor signal are touched at all - `report_turn_status`
(prompted every turn when Conductor is active) or `send_message` itself. A plain
CLI turn with neither tool call is left alone: its own final text reply already
is the user-visible message, so this guard has nothing to add and no signal to
act on. Bias hard toward under-firing per the dispatch brief - a wrong block
here stalls every session on the machine.

Per-session state is a small counter (`.session-markers/silent-turns-<id>`),
never a boolean: it counts CONSECUTIVE Conductor-signal turns with no
send_message, resets to 0 the moment one lands, and blocks only once the
streak reaches SILENT_TURN_THRESHOLD. That is what makes a lone quiet turn
pass while a whole quiet chat does not.

Relay exception (410's own carve-out): a turn whose only real input was a
`[daemon-meta]` peer relay is exempt from both the block AND the counter, but
only when its own tool calls are limited to RELAY_SAFE_SUFFIXES - a relay turn
that also edits, runs commands, or otherwise produces new information gets no
exemption and feeds the same counter as any other turn.

Decoy-pointer check (todo 782): a `send_message` call being present does not
mean it carries the substance. 2026-08-25 (zng-app): Claude wrote a full
multi-section breakdown as regular assistant text - never rendered to Joe -
then called `send_message` with only "...Full breakdown is in the chat
reply.", which points at prose Joe cannot see. The presence-only check above
was satisfied and still missed it. DECOY_PHRASE_RE matches the same shape of
self-referential pointer ("in the chat reply", "as shown above", "see
above" - phrasing that only makes sense if prior assistant prose were
visible, which it never is in this harness); it only fires when the
`send_message` text is ALSO short (<= DECOY_SHORT_CHAR_THRESHOLD), so a long
genuine message that happens to use one of these phrases in passing (e.g.
quoting Joe's own words back) is not blocked - the incident's own stub was
90 characters, well under the threshold.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, iter_turn_tool_uses, is_tool_result_entry
except Exception as e:
    sys.stderr.write(f"[send-message-stop-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
COUNTER_PREFIX = "silent-turns-"
SILENT_TURN_THRESHOLD = 3

# A turn only counts as Conductor-tracked if it called one of these; a relay
# turn stays exempt only while its calls are a subset of this same set.
RELAY_SAFE_SUFFIXES = {"report_turn_status", "read_messages", "list_peers"}

# Same envelope characters flagged-skill-mention.py strips - built from
# codepoints, never pasted literally, so no invisible bytes ride in this file.
_ZERO_WIDTH_RE = re.compile("[" + "".join(chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF)) + "]")
_RELAY_TAG_RE = re.compile(r"^\[daemon-meta\]", re.IGNORECASE)
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# Phrases that only make sense if the assistant's own prior prose were
# visible to Joe - it never is (CLAUDE.md: "Your assistant text ... [is]
# never rendered in the chat view at all"). Narrow on purpose (todo 782's own
# tradeoff note): high precision over coverage, since a false positive here
# gets deleted by the next session that trips over it.
DECOY_PHRASE_RE = re.compile(
    r"\b("
    r"in the chat reply"
    r"|as shown above"
    r"|see above"
    r"|as (?:i |I )?mentioned above"
    r"|in my (?:response|reply|previous message)"
    r")\b",
    re.IGNORECASE,
)
# The incident's own stub was 90 chars; a genuine multi-paragraph message
# that happens to use one of these phrases in passing (e.g. quoting Joe's
# own words) stays well above this and is never touched.
DECOY_SHORT_CHAR_THRESHOLD = 400


def _tool_suffix(name: str) -> str:
    return name.rsplit("__", 1)[-1] if "__" in name else name


def _turn_tool_suffixes(transcript_path: str) -> list:
    if not transcript_path:
        return []
    return [_tool_suffix(name) for name, _ in iter_turn_tool_uses(transcript_path)]


def _turn_send_message_texts(transcript_path: str) -> list:
    """`text` argument of every `send_message` call this turn, in call order."""
    if not transcript_path:
        return []
    return [
        (tool_input.get("text") or "")
        for name, tool_input in iter_turn_tool_uses(transcript_path)
        if _tool_suffix(name) == "send_message"
    ]


def _decoy_send_message_text(transcript_path: str) -> str:
    """The first `send_message` text this turn that both matches
    DECOY_PHRASE_RE and stays under DECOY_SHORT_CHAR_THRESHOLD, or "" if none
    do. Both conditions must hold - see the module docstring's todo 782
    section for why length gates the phrase match.
    """
    for text in _turn_send_message_texts(transcript_path):
        if len(text) <= DECOY_SHORT_CHAR_THRESHOLD and DECOY_PHRASE_RE.search(text):
            return text
    return ""


def _last_real_user_text(transcript_path: str) -> str:
    """Text of the most recent `type: user` transcript entry that is a real
    prompt, not a wrapped tool_result (same distinction _hooklib's own
    iter_turn_tool_uses draws for its turn boundary)."""
    path = Path(transcript_path)
    if not path.exists():
        return ""
    entries = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    for entry in reversed(entries):
        if entry.get("type") != "user" or is_tool_result_entry(entry):
            continue
        content = (entry.get("message", {}) or {}).get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(
                b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
            )
        return ""
    return ""


def _is_relay_input(text: str) -> bool:
    normalized = _ZERO_WIDTH_RE.sub("", text or "").lstrip()
    return bool(_RELAY_TAG_RE.match(normalized))


def _safe_session_id(session_id: str) -> bool:
    return bool(session_id) and bool(_SAFE_SESSION_ID_RE.match(session_id))


def _counter_path(session_id: str) -> Path:
    return SESSION_MARKER_DIR / f"{COUNTER_PREFIX}{session_id}"


def _reset_counter(session_id: str) -> None:
    if not _safe_session_id(session_id):
        return
    try:
        _counter_path(session_id).unlink()
    except OSError:
        pass


def _increment_counter(session_id: str) -> int:
    if not _safe_session_id(session_id):
        return 0
    path = _counter_path(session_id)
    try:
        current = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        current = 0
    new_count = current + 1
    try:
        SESSION_MARKER_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(str(new_count), encoding="utf-8")
    except OSError:
        pass
    return new_count


def _block(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    payload = read_payload()
    if payload.get("stop_hook_active") is True:
        sys.exit(0)

    session_id = payload.get("session_id") or ""
    transcript_path = payload.get("transcript_path") or ""
    suffixes = _turn_tool_suffixes(transcript_path)

    if "send_message" in suffixes:
        decoy_text = _decoy_send_message_text(transcript_path)
        if decoy_text:
            _block(
                "[send-message-stop-guard] This turn's send_message points at "
                "content Joe cannot see (%r) - your own assistant text and tool "
                "narration are never rendered in the chat view. Call "
                "mcp__cc_conductor__send_message again with the actual "
                "substance inlined, not a pointer to it. (todo 782)"
                % (decoy_text[:200],)
            )
        _reset_counter(session_id)
        sys.exit(0)

    if "report_turn_status" not in suffixes:
        sys.exit(0)  # no Conductor signal this turn, nothing to enforce

    last_user_text = _last_real_user_text(transcript_path) if transcript_path else ""
    if _is_relay_input(last_user_text) and all(s in RELAY_SAFE_SUFFIXES for s in suffixes):
        sys.exit(0)  # relay-only turn, exempt per 410 - no bookkeeping either way

    count = _increment_counter(session_id)
    if count >= SILENT_TURN_THRESHOLD:
        _block(
            "[send-message-stop-guard] %d consecutive turns have ended via "
            "report_turn_status with no send_message - call "
            "mcp__cc_conductor__send_message with a status summary before "
            "ending this turn. (todo 410: a quiet turn or two is fine, a whole "
            "silent stretch is not.)" % count
        )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[send-message-stop-guard] hook error, failing open: {e}\n")
        sys.exit(0)
