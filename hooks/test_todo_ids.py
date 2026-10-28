"""Self-test for _todo_ids.py: id parsing, formatting, label resolution, the CLI bash uses.

Run directly: python hooks/test_todo_ids.py
Never reads the real ~/.claude/device-label: every case sets CLAUDE_DEVICE_LABEL_FILE.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
ids = _testlib.load_module("todo_ids", _HOOKS_DIR / "_todo_ids.py")

fails = []


def check(label: str, ok: bool) -> None:
    if not _testlib.report(ok, label):
        fails.append(label)


tmp = tempfile.TemporaryDirectory()
label_file = Path(tmp.name) / "device-label"
label_file.write_text("pc\n", encoding="utf-8")
os.environ["CLAUDE_DEVICE_LABEL_FILE"] = str(label_file)

# parse_todo_id: (text, (label, number, slug) or None)
for text, want in [
    ("pc-1407", ("pc", 1407, None)),
    ("PC-7", ("pc", 7, None)),
    ("mac2-0003-some-slug", ("mac2", 3, "some-slug")),
    ("1407", (None, 1407, None)),
    ("07-x", (None, 7, "x")),
    ("1407-2fa-fix", (None, 1407, "2fa-fix")),
    ("pc-1407-", ("pc", 1407, None)),
    ("notes", None),
    ("", None),
    ("pc", None),
]:
    got = ids.parse_todo_id(text)
    got = None if got is None else (got.label, got.number, got.slug)
    check(f"parse_todo_id({text!r}) -> {got}", got == want)

check("format_todo_id pads to 4 digits", ids.format_todo_id("pc", 7) == "pc-0007")
check("format_todo_id grows past 9999", ids.format_todo_id("mac2", 10000) == "mac2-10000")
check("format_todo_id lowercases the label", ids.format_todo_id("PC", 1) == "pc-0001")

# parse_todo_name: names of backlog files, claims and reserve markers
for name, want in [
    ("pc-1407-x.md", ("pc", 1407, "x", False)),
    ("07-x.md", ("pc", 7, "x", True)),
    ("pc-1407.md", None),
    ("pc-1407.claim", ("pc", 1407, None, False)),
    ("8.claim", ("pc", 8, None, True)),
    ("pc-1407-slug.claim", ("pc", 1407, "slug", False)),
    ("pc-1407-.reserved", ("pc", 1407, None, False)),
    ("7-.reserved", ("pc", 7, None, True)),
    ("PLAN.md", None),
    ("pc-1407-.reserved.tmp-12", None),
]:
    got = ids.parse_todo_name(name)
    got = None if got is None else (got.label, got.number, got.slug, got.legacy)
    check(f"parse_todo_name({name!r}) -> {got}", got == want)

check("name_key is padding-free and label-qualified",
      ids.name_key("pc-0007-x.md") == ids.name_key("7-y.md") == "pc-7" and ids.name_key("mac-7-x.md") == "mac-7")

# resolve_label / match_names
names = ["pc-0050-a.md", "mac-0050-b.md", "mac-0060-c.md", "mac-0070-d.md", "mac2-0070-e.md", "0123-legacy.md"]
check("bare number prefers this device even when another label has it", ids.resolve_label("50", names) == "pc")
check("bare number with a unique other label resolves to it", ids.resolve_label("60", names) == "mac")
check("bare number nobody carries falls back to this device", ids.resolve_label("999", names) == "pc")
check("bare number matching a legacy file resolves to pc", ids.resolve_label("123", names) == "pc")
try:
    ids.resolve_label("70", names)
    check("bare number on two other labels raises AmbiguousTodoId", False)
except ids.AmbiguousTodoId as e:
    check("bare number on two other labels raises AmbiguousTodoId naming both", "mac-0070" in str(e) and "mac2-0070" in str(e))
check("a full id needs no lookup", ids.resolve_label("mac2-0070", []) == "mac2")
check("match_names narrows by label and number, ignoring directories",
      ids.match_names("pc-50", ["x/done/pc-0050-a.md", "x/mac-0050-b.md"]) == ["x/done/pc-0050-a.md"])
check("match_names narrows by slug when the id carries one",
      ids.match_names("pc-0050-b", ["pc-0050-a.md", "pc-0050-b.md"]) == ["pc-0050-b.md"])

# device label failures never default
label_file.unlink()
try:
    ids.get_device_label()
    check("missing device-label raises", False)
except ids.DeviceLabelError as e:
    check("missing device-label raises with the one-line fix", "device-label" in str(e) and '"pc" or "mac"' in str(e))
try:
    ids.resolve_label("50", names)
    check("a bare number with no device-label raises", False)
except ids.DeviceLabelError:
    check("a bare number with no device-label raises", True)
check("a full id still resolves without a device-label", ids.resolve_label("pc-50", names) == "pc")
for bad in ("PC", "pc 1", "1pc", "pc-2", ""):
    label_file.write_text(bad, encoding="utf-8")
    try:
        ids.get_device_label()
        check(f"invalid device-label {bad!r} raises", False)
    except ids.DeviceLabelError:
        check(f"invalid device-label {bad!r} raises", True)
label_file.write_text("mac2\r\n", encoding="utf-8")
check("a valid label with CRLF and no trailing garbage reads clean", ids.get_device_label() == "mac2")

# CLI: what commit-pathspec.sh calls
label_file.write_text("pc\n", encoding="utf-8")


def cli(*args, stdin=""):
    return subprocess.run([sys.executable, str(_HOOKS_DIR / "_todo_ids.py"), *args],
                          input=stdin.encode(), capture_output=True)


proc = cli("match", "50", stdin="a/pc-0050-a.md\na/mac-0050-b.md\n")
check("CLI match prints matching paths with bare LF line endings",
      proc.returncode == 0 and proc.stdout == b"a/pc-0050-a.md\n")
proc = cli("match", "70", stdin="mac-0070-d.md\nmac2-0070-e.md\n")
check("CLI match exits 3 on ambiguity", proc.returncode == 3 and b"mac2-0070" in proc.stderr)
proc = cli("match", "nope", stdin="")
check("CLI match exits 4 on a non-id", proc.returncode == 4)
label_file.unlink()
proc = cli("label")
check("CLI label exits 2 with the fix when the file is missing", proc.returncode == 2 and b"device-label" in proc.stderr)

tmp.cleanup()
sys.exit(_testlib.summarize(fails))
