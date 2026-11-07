"""Self-test for ci/check_vendored_overrides.py and the impeccable budget exemption (todo 1282).

Run directly: python ci/test_check_vendored_overrides.py
Exits 0 on all-pass, 1 on any failure. Works on throwaway trees, so it never depends on git state.
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ci"))

import check_skill_frontmatter as csf  # noqa: E402
import check_vendored_overrides as cvo  # noqa: E402

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


UPSTREAM = "---\nname: demo\ndescription: Long upstream text\nversion: 1.0.0\n---\n\nBody\n"
LOCAL_FLAG = "---\nname: demo\ndescription: Long upstream text\nversion: 1.0.0\ndisable-model-invocation: true\n---\n\nBody\n"


def make_tree(tmp: Path, skill_text: str, overrides: dict) -> Path:
    (tmp / "skills" / "demo").mkdir(parents=True)
    (tmp / "skills" / "demo" / "SKILL.md").write_bytes(skill_text.encode("utf-8"))
    (tmp / "skills" / "VENDORED.overrides.json").write_text(json.dumps(overrides), encoding="utf-8")
    return tmp / "skills" / "demo" / "SKILL.md"


FLAG = {"_comment": "ignored", "skills/demo/SKILL.md": {"disable-model-invocation": "true"}}


def drift_of(tmp: Path) -> list:
    problems = []
    for rel, wanted in cvo.load_overrides(tmp).items():
        problems.extend(cvo.drift_for(tmp / rel, wanted))
    return problems


with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, LOCAL_FLAG, FLAG)
    check(drift_of(tmp) == [], "override already in place reports no drift")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, UPSTREAM, FLAG)
    problems = drift_of(tmp)
    check(len(problems) == 1 and "disable-model-invocation" in problems[0],
          "a vendor update that dropped the flag is reported as drift")
    check(cvo.apply_to(skill, FLAG["skills/demo/SKILL.md"]) is True, "apply inserts the missing line")
    check(drift_of(tmp) == [], "no drift after apply")
    check(skill.read_text(encoding="utf-8") == LOCAL_FLAG, "inserted line sits inside the frontmatter, body untouched")
    check(cvo.apply_to(skill, FLAG["skills/demo/SKILL.md"]) is False, "apply is idempotent")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, UPSTREAM.replace("version: 1.0.0", "disable-model-invocation: false"), FLAG)
    check(len(drift_of(tmp)) == 1, "a wrong value is drift too")
    cvo.apply_to(skill, FLAG["skills/demo/SKILL.md"])
    text = skill.read_text(encoding="utf-8")
    check(text.count("disable-model-invocation") == 1 and "disable-model-invocation: true" in text,
          "apply rewrites a wrong value in place instead of adding a second line")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, UPSTREAM.replace("\n", "\r\n"), FLAG)
    cvo.apply_to(skill, FLAG["skills/demo/SKILL.md"])
    raw = skill.read_bytes().decode("utf-8")
    check(raw.count("\n") == raw.count("\r\n"), "CRLF files stay CRLF after apply")
    check(drift_of(tmp) == [], "CRLF file passes the check after apply")

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    make_tree(tmp, LOCAL_FLAG, {"skills/gone/SKILL.md": {"disable-model-invocation": "true"}})
    problems = drift_of(tmp)
    check(len(problems) == 1 and "missing" in problems[0], "an override for a deleted skill is reported, not skipped")

# A block-scalar value: the continuation lines go with the key line, nothing else moves.
BLOCK = "---\nname: demo\ndescription: >\n  Long folded upstream\n\n  second paragraph\nversion: 1.0.0\n---\n\nBody\n"
DESC = {"skills/demo/SKILL.md": {"description": "Short local text"}}
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, BLOCK, DESC)
    check(len(drift_of(tmp)) == 1, "a block-scalar description differs from a one-line override")
    check(cvo.apply_to(skill, DESC["skills/demo/SKILL.md"]) is True, "apply rewrites the block scalar")
    check(skill.read_text(encoding="utf-8") == "---\nname: demo\ndescription: Short local text\nversion: 1.0.0\n---\n\nBody\n",
          "apply drops the block scalar's continuation lines, leaving valid frontmatter")
    check(drift_of(tmp) == [] and cvo.apply_to(skill, DESC["skills/demo/SKILL.md"]) is False, "no drift and idempotent after the rewrite")

# A BOM'd SKILL.md is patched and keeps its BOM instead of raising; the check reads it too.
with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    skill = make_tree(tmp, "﻿" + UPSTREAM, FLAG)
    first = drift_of(tmp)
    check(len(first) == 1 and "no frontmatter" not in first[0], "a BOM'd file is read as drift, not as having no frontmatter")
    try:
        changed = cvo.apply_to(skill, FLAG["skills/demo/SKILL.md"])
    except ValueError:
        changed = None
    check(changed is True, "apply patches a BOM'd file without raising")
    check(skill.read_bytes().startswith(b"\xef\xbb\xbf---") and drift_of(tmp) == [], "the BOM is kept and the file passes after apply")

# Simulated vendor update on the real description budget: a long upstream description fails for an
# ordinary skill and passes for impeccable, while the committed overrides file matches the tree.
long_desc = " ".join(["word"] * 118)
seen = {"description": (long_desc, 3)}
check(csf.check_description_budget("skills/x/SKILL.md", Path("skills/x/SKILL.md"), seen) != [],
      "a 118-word description fails the budget for an ordinary skill")
check("impeccable" in csf.LEGACY_OVER_BUDGET_DEBT, "impeccable is in LEGACY_OVER_BUDGET_DEBT")
check(csf.check_description_budget("skills/impeccable/SKILL.md", Path("skills/impeccable/SKILL.md"), seen) == [],
      "impeccable's vendored 118-word description passes the budget")
real = [p for rel, w in cvo.load_overrides(ROOT).items() for p in cvo.drift_for(ROOT / rel, w)]
check(real == [], "the repo's own VENDORED.overrides.json matches the tree: " + "; ".join(real))

if failures:
    print(f"FAIL: {len(failures)} test(s) failed")
    sys.exit(1)
print("OK: all tests passed")
