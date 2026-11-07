"""Self-test for check_card_output.py.

Run: python skills/dashboard-card/test_check_card_output.py   (exit 0 = all pass)
"""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_card_output", HERE / "check_card_output.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def problems(data, paths=()):
    return cc.check(data if isinstance(data, str) else json.dumps(data), list(paths))


good = {
    "n": 4,
    "items": [{"name": "a", "url": "https://x"}],
    "_card": {
        "headline": "4 open", "headline_tone": "warn",
        "progress": {"value": 3, "max": 10, "label": "3 of 10"},
        "segments": {"items": [{"label": "done", "value": 6}, {"label": "open", "value": 4}], "max": 10, "note_tone": "good"},
    },
}
check(problems(good, ["n", "items[0].name", "items[].url"]) == [], "a valid card with resolving paths passes")
check(problems({"n": 1}) == [], "a card without _card passes")

check("not a single JSON document" in problems("Loading...\n{}")[0], "log noise before the JSON is named")
check("not a single JSON document" in problems("")[0], "empty stdout is named")
check("top level" in problems([1, 2])[0], "a top-level list is rejected")
check("'missing' does not resolve" in problems({"n": 1}, ["missing"])[0], "unresolved path is named")
check(problems({"items": []}, ["items[0].name"]) != [], "[0] on an empty list does not resolve")
check(problems({"n": 1}, ["n.deeper"]) != [], "descending into a number does not resolve")

check("headline_tone" in problems({"_card": {"headline_tone": "red"}})[0], "unknown headline tone rejected")
check("not a known key" in problems({"_card": {"title": "x"}})[0], "unknown _card key rejected")
check("progress" in problems({"_card": {"progress": {"value": 1, "max": 0}}})[0], "progress max 0 rejected")
check("progress" in problems({"_card": {"progress": {"value": "1", "max": 5}}})[0], "non-numeric progress rejected")
check("overflows" in problems({"_card": {"segments": {"items": [{"label": "a", "value": 8}, {"label": "b", "value": 5}], "max": 10}}})[0], "segments summing past max rejected")
check("segments.items" in problems({"_card": {"segments": {"items": [], "max": 10}}})[0], "empty segments rejected")
check("note_tone" in problems({"_card": {"segments": {"items": [{"label": "a", "value": 1}], "max": 2, "note_tone": "bad"}}})[0], "bad note_tone rejected")

check(cc.resolve({"a": [{"b": 5}]}, "a[0].b") == (True, 5), "resolve follows [n]")
check(cc.resolve({"a": [{"b": 5}]}, "a[].b") == (True, 5), "resolve treats [] as the first element")

with tempfile.TemporaryDirectory() as tmp:
    f = Path(tmp) / "out.json"
    f.write_text(json.dumps(good), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cc.main([str(f), "--paths", "n"])
    check(code == 0 and out.getvalue().strip() == "OK", "main reads a file and prints OK")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cc.main([str(f), "--paths", "nope"])
    check(code == 1 and "PROBLEM" in out.getvalue(), "main exits 1 and prints PROBLEM lines")
    with contextlib.redirect_stderr(io.StringIO()):
        code = cc.main([str(Path(tmp) / "absent.json")])
    check(code == 2, "unreadable file exits 2")

    # Stdin is the documented way to use it, so run it as a real subprocess once.
    run = subprocess.run([sys.executable, str(HERE / "check_card_output.py"), "--paths", "n"],
                         input=json.dumps(good), capture_output=True, text=True)
    check(run.returncode == 0 and run.stdout.strip() == "OK", "stdin pipe works end to end")

print(f"\n{len(failures)} failure(s)" if failures else "\nall passed")
sys.exit(1 if failures else 0)
