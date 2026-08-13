"""Self-test for EXPERIMENTAL-bare-question-detector.py (todo 308 spike).

Run directly: python hooks/test_bare_question_detector.py
Exits 0 on all-pass, 1 on any failure. This tests the spike's own logic
only - it does NOT certify the spike as safe to wire, see its docstring
and the todo 308 report for the measured false-negative rate.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_SPIKE_PATH = _HOOKS_DIR / "EXPERIMENTAL-bare-question-detector.py"

_spec = importlib.util.spec_from_file_location("bare_question_spike", _SPIKE_PATH)
spike = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(spike)

# (text, expect_bare_question, label) - pure trailing-line heuristic
UNIT_CASES = [
    ("Want me to check the admin side?", True, "todo 308's own cited real violation"),
    ("Ship it, run another manual round, or park it?", True, "corpus: multi-option trailing question"),
    ("Nothing is running. Branch is green, unpushed.", False, "clean status close, no question"),
    ("> Tiket sam lose napisao, zvuci kao da treba na loanu?", False, "blockquoted user text ending in ?"),
    ("Two questions decide everything: are you in the VAT system, and how many employees?\nRegardless, one move: ask your accountant.", False, "KNOWN MISS: real question not on trailing line"),
    ("```\nfunc foo() { return x ? 1 : 0; }\n```", False, "ternary ? mid-fence is not the trailing line, correctly clean"),
    ("Command used:\ndir *.ex?", True, "KNOWN FALSE-POSITIVE RISK: glob wildcard ending in ? is not a question"),
    ("All done.\n<cc-title>Foo</cc-title>\n<cc-status:done>", False, "trailing status markers skipped, no question beneath"),
    ("Say the word if you want that done, or Claude holds.", False, "corpus: decision framed without a literal ?"),
]


def run_unit_cases() -> list:
    fails = []
    for text, expect, label in UNIT_CASES:
        got = spike.is_bare_question(text)
        ok = got == expect
        print(f"[{'PASS' if ok else 'FAIL'}] unit: {label} -> {got} (expected {expect})")
        if not ok:
            fails.append(label)
    return fails


def write_transcript(tmpdir: Path, has_auq: bool) -> Path:
    entries = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}},
    ]
    if has_auq:
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion", "input": {}}]},
        })
    entries.append({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "Want me to check the admin side?"}]},
    })
    path = tmpdir / "transcript.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


# (has_auq_in_turn, expect_output_prefix, label)
INTEGRATION_CASES = [
    (False, "FLAG", "integration: bare question, no AUQ this turn"),
    (True, "EXEMPT_AUQ_IN_TURN", "integration: bare question, AUQ used earlier this turn"),
]


def run_integration_cases() -> list:
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        for has_auq, expect_prefix, label in INTEGRATION_CASES:
            transcript = write_transcript(tmpdir, has_auq)
            payload = {
                "last_assistant_message": "Want me to check the admin side?",
                "transcript_path": str(transcript),
                "stop_hook_active": False,
            }
            proc = subprocess.run(
                [sys.executable, str(_SPIKE_PATH)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
            )
            ok = proc.stdout.strip().startswith(expect_prefix) and proc.returncode == 0
            print(f"[{'PASS' if ok else 'FAIL'}] {label} -> {proc.stdout.strip()!r}")
            if not ok:
                fails.append(label)
    return fails


def run() -> int:
    fails = run_unit_cases() + run_integration_cases()
    print("\nALL PASS" if not fails else f"\nFAILURES: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
