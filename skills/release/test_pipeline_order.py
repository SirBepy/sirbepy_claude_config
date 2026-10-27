"""Self-test for the /commit "Push pipeline" step order and /release's non-restatement of it.

Run: python skills/release/test_pipeline_order.py   (exit 0 = all pass)

Keys on the step labels (1, 1b, 2, 4, 4b, 5), not on wording, so rewording a step
does not break it; reordering or dropping one does.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
COMMIT = ROOT / "skills" / "commit" / "SKILL.md"
RELEASE = ROOT / "skills" / "release" / "SKILL.md"

failures = []


def check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        failures.append(label)


def pipeline_labels(text: str) -> list:
    """Step labels of the numbered list under the '## Push pipeline' heading, in order."""
    section = text.split("\n## Push pipeline", 1)[1]
    section = re.split(r"\n## ", section, maxsplit=1)[0]
    return re.findall(r"^(\d+[a-z]?)\. \*\*", section, flags=re.M)


commit_text = COMMIT.read_text(encoding="utf-8").replace("\r\n", "\n")
labels = pipeline_labels(commit_text)
check(bool(labels), "Push pipeline list is found")

order = ["1", "1b", "2", "4", "4b", "5"]
positions = {step: labels.index(step) for step in order if step in labels}
check(all(step in positions for step in order), "labels 1, 1b, 2, 4, 4b, 5 all exist: " + ",".join(labels))
if len(positions) == len(order):
    indexes = [positions[step] for step in order]
    check(indexes == sorted(indexes), "order is commit < kit sync < todo sweep < gate < version bump < push")

check(len(labels) == len(set(labels)), "no duplicate step labels")

release_text = RELEASE.read_text(encoding="utf-8").replace("\r\n", "\n")
numbered = [ln for ln in release_text.splitlines() if re.match(r"\s*\d+[a-z]?[.)] ", ln)]
check(
    not any(("code-check" in ln or "e2e" in ln or "transcript" in ln) for ln in numbered),
    "release/SKILL.md does not restate the gate or transcript check as numbered steps",
)
check(
    "Push pipeline" in release_text and "skills/commit/SKILL.md" in release_text,
    "release/SKILL.md points at the commit skill's Push pipeline",
)

if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
