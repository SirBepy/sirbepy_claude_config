"""Todo id parsing/formatting shared by every Python consumer (hooks, tools, the bash
commit scripts via this module's CLI). Twin of skills/close/_shared.ps1; the two must
stay in step and no other script may carry its own id regex.

An id is `<label>-<NNNN>`: the device label (`pc`, `mac`, `pc2`; ~/.claude/device-label)
then a number zero-padded to 4 digits on write, any padding accepted on read. Filenames
are `pc-1407-<slug>.md`, claims `pc-1407.claim`, reservation markers `pc-1407-.reserved`.
A legacy bare-numeric name (`1407-slug.md`, `07-x.md`) reads as label `pc`: every todo
made before labels existed was made on the Windows desktop, whichever machine reads it.

CLI (for bash callers):
    python _todo_ids.py label
        prints this device's label; exit 2 + a one-line fix when the file is missing.
    python _todo_ids.py match <id>
        reads candidate paths from stdin (one per line) and prints those whose basename
        carries the resolved id. A bare number resolves to this device's label first, else
        a unique match on another label; several labels exit 3 with the candidates.
"""

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple, Optional

LEGACY_LABEL = "pc"
LABEL_RE = re.compile(r"^[a-z]+[0-9]*$")
# Group 3 (slug) may be empty: `pc-1407-.reserved` strips to `pc-1407-`.
_ID_RE = re.compile(
    r"^(?:(?P<label>[a-z]+[0-9]*)-)?(?P<num>[0-9]{1,15})(?:-(?P<slug>.*))?$",
    re.IGNORECASE,
)
_NAME_RE = re.compile(r"^(?P<stem>.+)\.(?P<ext>md|claim|reserved)$", re.IGNORECASE)

DEVICE_LABEL_FIX = (
    'Set the label: write "pc" or "mac" (pc2/mac2 for a second one) to ~/.claude/device-label'
)


class DeviceLabelError(Exception):
    """~/.claude/device-label is missing or malformed."""


class AmbiguousTodoId(Exception):
    """A bare number exists on several devices and none is this one."""


class TodoId(NamedTuple):
    label: Optional[str]  # None for a bare number as typed; filled for a parsed filename
    number: int
    slug: Optional[str]
    legacy: bool = False  # a filename that carried no label (read as LEGACY_LABEL)


def device_label_path() -> Path:
    """CLAUDE_DEVICE_LABEL_FILE exists so tests never touch the real label file."""
    override = os.environ.get("CLAUDE_DEVICE_LABEL_FILE")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "device-label"


def get_device_label() -> str:
    """Raises DeviceLabelError, never defaults: a second machine silently defaulting to
    `pc` would mint ids that collide with this one's."""
    path = device_label_path()
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError:
        raise DeviceLabelError(f"No device label found at '{path}'. {DEVICE_LABEL_FIX}") from None
    label = raw.strip()
    if not LABEL_RE.match(label):
        raise DeviceLabelError(
            f"Invalid device label {label!r} in '{path}' (must match ^[a-z]+[0-9]*$). {DEVICE_LABEL_FIX}"
        )
    return label


def format_todo_id(label: str, number: int) -> str:
    return f"{label.lower()}-{number:04d}"


def todo_key(label: str, number: int) -> str:
    """Padding-free identity string, for dict/set keys and collision comparison."""
    return f"{label.lower()}-{number}"


def parse_todo_id(text: str) -> Optional[TodoId]:
    """Parses a typed id: `1407`, `pc-1407`, `pc-7`, or either with a `-slug` tail.
    label is None for a bare number. None when the text is not an id at all."""
    m = _ID_RE.match((text or "").strip())
    if not m:
        return None
    slug = m.group("slug") or None
    label = m.group("label")
    return TodoId(label.lower() if label else None, int(m.group("num")), slug)


def parse_todo_name(name: str) -> Optional[TodoId]:
    """Parses a backlog/done `*.md`, a `.claims` `*.claim` or a `*-.reserved` marker
    name. A legacy bare-numeric name reads as LEGACY_LABEL (legacy=True). A `.md` must
    carry a slug, which is what separates a todo file from a note that merely ends in
    digits."""
    nm = _NAME_RE.match(name or "")
    if not nm:
        return None
    parsed = parse_todo_id(nm.group("stem"))
    if parsed is None:
        return None
    if nm.group("ext").lower() == "md" and not parsed.slug:
        return None
    if parsed.label is None:
        return TodoId(LEGACY_LABEL, parsed.number, parsed.slug, True)
    return parsed


def is_todo_filename(name: str) -> bool:
    nm = _NAME_RE.match(name or "")
    return bool(nm) and nm.group("ext").lower() == "md" and parse_todo_name(name) is not None


def name_key(name: str) -> Optional[str]:
    """todo_key of a filename/claim/marker name, None when it is not a todo name."""
    info = parse_todo_name(name)
    return todo_key(info.label, info.number) if info else None


def resolve_label(raw_id: str, names) -> Optional[str]:
    """Label an id resolves to against the todo names present (basenames).

    A labelled id is itself. A bare number resolves to THIS device's label first, else a
    unique match on another label, else (nothing carries the number) this device's label;
    several other labels raise AmbiguousTodoId naming every candidate. Returns None when
    raw_id is not an id. Raises DeviceLabelError for a bare number with no device label.
    """
    parsed = parse_todo_id(raw_id)
    if parsed is None:
        return None
    if parsed.label:
        return parsed.label
    device = get_device_label()
    labels = set()
    for n in names:
        info = parse_todo_name(os.path.basename(n))
        if info and info.number == parsed.number:
            labels.add(info.label)
    if device in labels:
        return device
    if len(labels) == 1:
        return next(iter(labels))
    if len(labels) > 1:
        candidates = ", ".join(format_todo_id(l, parsed.number) for l in sorted(labels))
        raise AmbiguousTodoId(
            f"Ambiguous id {raw_id!r}: it exists on several devices ({candidates}) and none is "
            f"this device ({device!r}). Retry with the full id."
        )
    return device


def match_names(raw_id: str, paths):
    """Subset of `paths` (any dirs, judged by basename) carrying the id raw_id resolves
    to; a slug in raw_id narrows further. Raises the errors resolve_label does."""
    parsed = parse_todo_id(raw_id)
    if parsed is None:
        return []
    paths = list(paths)
    label = resolve_label(raw_id, paths)
    out = []
    for p in paths:
        info = parse_todo_name(os.path.basename(p))
        if not info or info.label != label or info.number != parsed.number:
            continue
        if parsed.slug and info.slug != parsed.slug:
            continue
        out.append(p)
    return out


def _emit(line: str) -> None:
    """Bash consumers read these lines; text-mode print would end them with CRLF on Windows."""
    sys.stdout.buffer.write((line + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def _main(argv) -> int:
    if len(argv) >= 2 and argv[1] == "label":
        try:
            _emit(get_device_label())
            return 0
        except DeviceLabelError as e:
            sys.stderr.write(f"{e}\n")
            return 2
    if len(argv) == 3 and argv[1] == "match":
        paths = [ln.rstrip("\r\n") for ln in sys.stdin if ln.strip()]
        try:
            if parse_todo_id(argv[2]) is None:
                sys.stderr.write(f"'{argv[2]}' is not a todo id (expected e.g. pc-1407 or 1407)\n")
                return 4
            for p in match_names(argv[2], paths):
                _emit(p)
            return 0
        except DeviceLabelError as e:
            sys.stderr.write(f"{e}\n")
            return 2
        except AmbiguousTodoId as e:
            sys.stderr.write(f"{e}\n")
            return 3
    sys.stderr.write("usage: _todo_ids.py label | match <id>   (match reads paths on stdin)\n")
    return 64


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
