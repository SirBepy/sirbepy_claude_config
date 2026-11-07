"""Self-test for the /commit "Push pipeline" step order and /release's non-restatement of it.

Run: python skills/release/test_pipeline_order.py   (exit 0 = all pass)

Keys on the step labels (1, 1b, 1c, 2, 4, 4b, 5), not on wording, so rewording a step
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

order = ["1", "1b", "1c", "2", "4", "4b", "5"]
positions = {step: labels.index(step) for step in order if step in labels}
check(all(step in positions for step in order), "labels 1, 1b, 1c, 2, 4, 4b, 5 all exist: " + ",".join(labels))
if len(positions) == len(order):
    indexes = [positions[step] for step in order]
    check(indexes == sorted(indexes), "order is commit < kit sync < gate hand-off < todo sweep < gate < version bump < push")

# The transcript check reads the parent session's own transcript, so the hand-off
# must run it before spawning; a gate chat that ran it would scan an empty history.
# The procedure lives in the gate-chat skill; commit's "Gate hand-off" section points at it.
handoff = commit_text.split("\n## Gate hand-off", 1)
check(len(handoff) == 2, "Gate hand-off section exists")
if len(handoff) == 2:
    body = re.split(r"\n## ", handoff[1], maxsplit=1)[0]
    check("/gate-chat" in body, "Gate hand-off section points at the gate-chat skill")

GATE_CHAT = ROOT / "skills" / "gate-chat" / "SKILL.md"
check(GATE_CHAT.exists(), "gate-chat skill exists")
if GATE_CHAT.exists():
    gate_text = GATE_CHAT.read_text(encoding="utf-8").replace("\r\n", "\n")
    transcript_at = gate_text.find("Pre-push transcript check")
    spawn_at = gate_text.find("spawn_chat")
    check(0 <= transcript_at < spawn_at, "hand-off runs the transcript check before spawn_chat")
    check("`/close` as the prompt's last word" in gate_text, "the gate chat closes itself with a trailing /close")
    check("/then-close" not in gate_text, "the gate chat no longer names the retired /then-close")
    # Joe's 2026-10-27 rule: a light chat runs the gate in place. Dropping the threshold
    # made a 13%-context chat spawn a gate chat on 2026-10-30.
    check("context-left.mjs" in gate_text and "30%" in gate_text, "gate-chat measures context and skips the hand-off under 30% used")
    check("30%" in commit_text.split("1c. ", 1)[-1].split("\n", 1)[0], "commit step 1c states the 30% threshold")
    # A Subchats-mode chat hands the gate to a hidden gate sub whatever its context
    # level, via spawn_chat's gate: true, and a chat with the mode off keeps today's behaviour.
    step2 = gate_text.split("\n2. ", 1)[-1].split("\n3. ", 1)[0]
    check("gate: true" in step2 and "Subchats mode is ON for this chat" in step2, "gate-chat step 2 adds gate: true in a Subchats-mode chat")
    check("Subchats mode is now OFF" in step2, "gate-chat step 2 honours the later 'now OFF' note")
    check("sections 4a and 4b" in step2, "gate-chat step 2 sends the gate child to /release sections 4a and 4b")
    check("snippets/auto-commit.md" in step2, "gate-chat still pre-reads snippets/auto-commit.md for the push-read gate")
    check("Subchats" in commit_text.split("1c. ", 1)[-1].split("\n", 1)[0], "commit step 1c exempts a Subchats-mode chat from the 30% threshold")

check(len(labels) == len(set(labels)), "no duplicate step labels")

release_text = RELEASE.read_text(encoding="utf-8").replace("\r\n", "\n")
numbered = [ln for ln in release_text.splitlines() if re.match(r"\s*\d+[a-z]?[.)] ", ln)]
check(
    not any(("code-check" in ln or "e2e" in ln or "transcript" in ln) for ln in numbered),
    "release/SKILL.md does not restate the gate or transcript check as numbered steps",
)
gate_section = release_text.split("\n## Gate chat", 1)[-1].split("\n## ", 1)[0]
check("Subchats" in gate_section, "release/SKILL.md Gate chat section names the Subchats-mode hand-off")
check(
    "Push pipeline" in release_text and "skills/commit/SKILL.md" in release_text,
    "release/SKILL.md points at the commit skill's Push pipeline",
)

if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
