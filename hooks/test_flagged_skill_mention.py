"""Self-test for flagged-skill-mention.py (todo 332: bracketed-envelope guard).

The hook has no importable functions - it runs top to bottom and calls
sys.exit() as flow control, so it cannot go through _testlib.load_module
(that would execute the whole script, including its stdin read, at import
time). Every case is a full subprocess run instead, using _testlib's
run_cases/summarize for the case table and footer.

Run directly: python hooks/test_flagged_skill_mention.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_HOOK_PATH = _HOOKS_DIR / "flagged-skill-mention.py"

ZWSP = "​"

# Real repro payload from todo 332: a Conductor peer posting to the repo
# coordination channel, reporting (not invoking) /close mid-paragraph.
PEER_PAYLOAD = (
    f"{ZWSP}[daemon-meta]{ZWSP}[repo-channel] Hold sign-off until review lands: "
    "Go ahead, no conflict. I'm in /close and will not commit anything."
)

# (prompt, expect_fire, label)
CASES = [
    (PEER_PAYLOAD, False, "todo 332 repro: peer/daemon envelope, /close mid-sentence"),
    ("[SYSTEM NOTIFICATION] background task finished, see /autopilot log", False,
     "existing guard: [SYSTEM NOTIFICATION prefix, must not regress"),
    ("[some-other-channel][sub-tag] status update, ran /close overnight", False,
     "shape generalization: unrecognised bracketed envelope still skipped"),
    ("/close --dont-close", True, "genuine Joe prompt: /close typed directly, must fire"),
    ("/autopilot then /create-pr when done", True,
     "genuine Joe prompt: two flagged skills named in one prompt, both fire"),
    ("please look into this, /close is what I want to run", True,
     "genuine Joe prompt: skill name mid-sentence, position not penalised"),
    ("[todo item] /close is what I want to run", False,
     "documents the accepted tradeoff: a Joe prompt opening with [tag] reads as an envelope too"),
    ("lets finish off all of the todos!!!\n/auto-do-todos \nbut first go thru them",
     True, "todo 342: real corpus case, invocation on line 2 starting that line, must fire"),
    ("explain the plan first\nI think we should probably use /close when done",
     True, "todo 891: mid-sentence mention on a non-first line now fires, position not checked"),
    ("/e2e\nand then when youre done just /commit and then /close up",
     True, "todo 891 repro: /close mid-line on the last line, must fire"),
    ("I closed the laptop, did a review of the pickup truck listing, no slash anywhere",
     False, "false-positive regression: bare skill-like words in prose, no leading slash, must not fire"),
]


def check(case) -> bool:
    prompt, expect_fire, label = case
    payload = {"prompt": prompt}
    proc = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    got_fire = '"hookSpecificOutput"' in proc.stdout
    ok = got_fire == expect_fire and proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label} -> exit={proc.returncode} fired={got_fire}")
    return ok


def check_wording() -> bool:
    """todo 491: injected text must offer judgement, not suppress it - the
    hook can't tell a relayed mention from a real invocation, so it must
    not tell the model to treat every mention as one.
    """
    proc = subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps({"prompt": "/close --dont-close"}),
        capture_output=True,
        text=True,
    )
    ok = (
        "genuine request to run it" in proc.stdout
        and "never report it as unavailable" not in proc.stdout
    )
    return _testlib.report(ok, "todo 491: injected wording allows judgement, drops the suppression line")


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    if not check_wording():
        fails.append("todo 491: injected wording allows judgement, drops the suppression line")
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
