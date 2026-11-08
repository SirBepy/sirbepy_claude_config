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
check("'missing' has no non-null value" in problems({"n": 1}, ["missing"])[0], "unresolved path is named")
check(problems({"items": []}, ["items[0].name"]) != [], "[0] on an empty list does not resolve")
check(problems({"n": 1}, ["n.deeper"]) != [], "descending into a number does not resolve")

check("headline_tone" in problems({"_card": {"headline_tone": "red"}})[0], "unknown headline tone rejected")
check("not a known key" in problems({"_card": {"title": "x"}})[0], "unknown _card key rejected")
check("progress" in problems({"_card": {"progress": {"value": 1, "max": 0}}})[0], "progress max 0 rejected")
check("progress" in problems({"_card": {"progress": {"value": "1", "max": 5}}})[0], "non-numeric progress rejected")
check("overflows" in problems({"_card": {"segments": {"items": [{"label": "a", "value": 8}, {"label": "b", "value": 5}], "max": 10}}})[0], "segments summing past max rejected")
check(problems({"_card": {"segments": {"items": [{"label": "a", "value": 0.1}, {"label": "b", "value": 0.2}], "max": 0.3}}}) == [], "float sum that equals max is not an overflow")
check("segments.items" in problems({"_card": {"segments": {"items": [], "max": 10}}})[0], "empty segments rejected")
check("note_tone" in problems({"_card": {"segments": {"items": [{"label": "a", "value": 1}], "max": 2, "note_tone": "bad"}}})[0], "bad note_tone rejected")

check(cc.resolve({"a": [{"b": 5}]}, "a[0].b") == (True, 5), "resolve follows [n]")
check(cc.resolve({"a": [{"b": 5}, {"c": 1}, {"b": 7}]}, "a[].b") == (True, [5, 7]), "[] maps over every element, skipping ones without the key")
check(cc.resolve({"a": [{"c": 1}, {"b": 7}]}, "a[].b") == (True, [7]), "[] finds a key present only in a later element")
check(cc.resolve({"a": []}, "a[].b") == (False, None), "[] over an empty list is not found")
check(cc.resolve({"a": None}, "a") == (False, None), "a null value counts as not found, the card shows '-'")
check(cc.resolve({"items": [1, 2, 3]}, "sum(items[])") == (True, 6) and cc.resolve({"items": [{"n": 2}, {"n": 5}]}, "sum(items[].n)") == (True, 7), "sum() totals a mapped path")
check(cc.resolve({"items": [1, 2, 3]}, "sum(items)") == (True, 6), "sum() of a plain list totals it, as the tool does")
check(cc.resolve({"items": ["x"]}, "sum(items[])") == (False, None), "sum() over non-numbers is not found")
check(problems({"items": [{"n": 2}]}, ["sum(items[].n)", "items[].n"]) == [], "sum() and [] paths pass the checker")
check("progress.value is above max" in problems({"_card": {"progress": {"value": 20, "max": 10}}})[0], "progress above max reported")
check("must not be negative" in problems({"_card": {"segments": {"items": [{"label": "a", "value": -3}, {"label": "b", "value": 9}], "max": 10}}})[0], "negative segment value reported")

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
    run = subprocess.run([sys.executable, str(HERE / "check_card_output.py"), "-", "--paths", "n"],
                         input=json.dumps(good).encode("utf-8"), capture_output=True)
    check(run.returncode == 0 and run.stdout.decode().strip() == "OK", "stdin works end to end")

    script = Path(tmp) / "card.py"
    script.write_text(
        "import json, sys\n"
        "sys.stdout.buffer.write(json.dumps({'name': 'caf\\u00e9'}, ensure_ascii=False).encode('utf-8'))\n",
        encoding="utf-8",
    )
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cc.main(["--paths", "name", "--", sys.executable, str(script)])
    check(code == 0 and out.getvalue().strip() == "OK", "-- command runs the script and decodes UTF-8 output")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cc.main(["--paths", "nope", "--", sys.executable, str(script)])
    check(code == 1 and "PROBLEM" in out.getvalue(), "-- command with a missing path exits 1")
    failing = Path(tmp) / "fail.py"
    failing.write_text("import sys\nprint('boom', file=sys.stderr)\nsys.exit(3)\n", encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cc.main(["--", sys.executable, str(failing)])
    check(code == 1 and "exited 3: boom" in out.getvalue(), "-- command that fails reports its exit code and stderr")
    with contextlib.redirect_stderr(io.StringIO()):
        code = cc.main(["--", "no-such-program-xyz"])
    check(code == 2, "-- command that cannot start exits 2")
    binary = Path(tmp) / "bin.json"
    binary.write_bytes(bytes([0xff, 0xfe]) + b"{}")
    with contextlib.redirect_stderr(io.StringIO()):
        code = cc.main([str(binary)])
    check(code == 2, "non-UTF-8 file exits 2 without a traceback")

check(cc.resolve({"a": {"x": 1}}, "a[x]") == (False, None), "malformed [x] step is not read as a key")
check(cc.resolve({"a": 1}, ".") == (False, None), "a lone dot is not the root")
check(cc.resolve({"a": [[1, 2], [3]]}, "a[0][1]") == (True, 2), "chained [n][n] steps resolve")
with contextlib.redirect_stderr(io.StringIO()):
    check(cc.main(["--paths", "n", "--"]) == 2, "a trailing -- with no command exits 2 instead of reading stdin")

print(f"\n{len(failures)} failure(s)" if failures else "\nall passed")
sys.exit(1 if failures else 0)
