"""Self-test for patch-file.py.

Run directly: python tools/test_patch_file.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real CLI via subprocess (not an import) since patch-file.py is a
standalone tool invoked exactly this way from a session. Covers the four
line-ending shapes named in todo 827's acceptance list plus the exactly-once
match guarantee that is the load-bearing part of the whole tool.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

SCRIPT = ROOT / "tools" / "patch-file.py"
BOM = b"\xef\xbb\xbf"


def run_patch(path: Path, *replace_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path), *replace_args],
        capture_output=True, text=True,
    )


def write_pair(tmp: Path, old: str, new: str) -> tuple[str, str]:
    old_file = tmp / "old.txt"
    new_file = tmp / "new.txt"
    old_file.write_bytes(old.encode("utf-8"))
    new_file.write_bytes(new.encode("utf-8"))
    return str(old_file), str(new_file)


def check_crlf_stays_crlf() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        target.write_bytes(b"line one\r\nline two\r\nline three\r\n")
        old_f, new_f = write_pair(tmp, "line two", "line TWO")
        result = run_patch(target, "--replace", old_f, new_f)
        got = target.read_bytes()
        ok = result.returncode == 0 and got == b"line one\r\nline TWO\r\nline three\r\n"
        return _testlib.report(ok, "CRLF file stays CRLF")


def check_lf_stays_lf() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        target.write_bytes(b"line one\nline two\nline three\n")
        old_f, new_f = write_pair(tmp, "line two", "line TWO")
        result = run_patch(target, "--replace", old_f, new_f)
        got = target.read_bytes()
        ok = result.returncode == 0 and got == b"line one\nline TWO\nline three\n"
        return _testlib.report(ok, "LF file stays LF")


def check_bom_kept() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        target.write_bytes(BOM + b"line one\nline two\n")
        old_f, new_f = write_pair(tmp, "line one", "line ONE")
        result = run_patch(target, "--replace", old_f, new_f)
        got = target.read_bytes()
        ok = result.returncode == 0 and got == BOM + b"line ONE\nline two\n"
        return _testlib.report(ok, "UTF-8 BOM is kept")


def check_mixed_endings_not_normalised() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        original = b"line one\r\nline two\nline three\r\n"
        target.write_bytes(original)
        old_f, new_f = write_pair(tmp, "line two", "line TWO")
        result = run_patch(target, "--replace", old_f, new_f)
        got = target.read_bytes()
        ok = result.returncode != 0 and got == original
        return _testlib.report(ok, "mixed-ending file is refused, not silently normalised")


def check_zero_matches_fails() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        original = b"line one\nline two\n"
        target.write_bytes(original)
        old_f, new_f = write_pair(tmp, "not present", "x")
        result = run_patch(target, "--replace", old_f, new_f)
        ok = result.returncode != 0 and target.read_bytes() == original
        return _testlib.report(ok, "zero matches exits non-zero and leaves file untouched")


def check_duplicate_match_fails_and_names_it() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        original = b"dup\ndup\n"
        target.write_bytes(original)
        old_f, new_f = write_pair(tmp, "dup", "DUP")
        result = run_patch(target, "--replace", old_f, new_f)
        names_it = old_f in result.stderr or "2 times" in result.stderr
        ok = result.returncode != 0 and target.read_bytes() == original and names_it
        return _testlib.report(ok, "a string matching twice exits non-zero and names the pair")


def check_stdin_json_mode() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "f.txt"
        target.write_bytes(b"line one\r\nline two\r\n")
        import json
        payload = json.dumps({
            "path": str(target),
            "replacements": [{"old": "line one", "new": "line ONE"}],
        })
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--stdin-json"],
            input=payload, capture_output=True, text=True,
        )
        got = target.read_bytes()
        ok = result.returncode == 0 and got == b"line ONE\r\nline two\r\n"
        return _testlib.report(ok, "JSON-on-stdin mode applies and preserves CRLF")


def main() -> int:
    checks = [
        check_crlf_stays_crlf,
        check_lf_stays_lf,
        check_bom_kept,
        check_mixed_endings_not_normalised,
        check_zero_matches_fails,
        check_duplicate_match_fails_and_names_it,
        check_stdin_json_mode,
    ]
    fails = [c.__name__ for c in checks if not c()]
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
