"""Self-test for skills/cleanup-memory/reachability.mjs's link parser (todo 1039).

Run directly: python tools/test_reachability.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real script via `node` against a scratch memory dir, not a
reimplementation of its regex, since the bug is specifically about what the
compiled pattern does against a MEMORY.md line, not about an isolated
function. A bracketed link LABEL (`#[cfg(test)]`, `[hidden]`) used to
terminate the non-greedy `[^\\]]*` early, splitting `](path)` off from its
label so the link was never associated with a target - a live-linked file
then misreported as `orphan-file`, which Step 6 would "fix" by appending a
duplicate index line for an already-indexed file.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

SCRIPT = ROOT / "skills" / "cleanup-memory" / "reachability.mjs"


def run_reachability(mem_dir: Path) -> str:
    result = subprocess.run(
        ["node", str(SCRIPT), str(mem_dir)],
        capture_output=True, text=True,
    )
    return result.stdout + result.stderr


def authoritative_orphan_count(output: str) -> str:
    """Pulls the `orphan-file: N` line out of the [authoritative] block only -
    the loaded-window, direct-link-only reading /cleanup-memory Step 2 treats
    as real. The other two readings the script prints are context only and
    must not leak a false pass/fail into this check.
    """
    lines = output.splitlines()
    in_block = False
    for line in lines:
        if line.strip().startswith("[authoritative]"):
            in_block = True
            continue
        if in_block and line.strip().startswith("orphan-file:"):
            return line.strip()
    return ""


def check_bracketed_label_single_link() -> bool:
    with tempfile.TemporaryDirectory() as td:
        mem = Path(td)
        (mem / "x.md").write_text("target of a bracketed-label link\n", encoding="utf-8")
        (mem / "MEMORY.md").write_text(
            "# Memory Index\n\n"
            "- [cargo build hides #[cfg(test)]](x.md) - use --all-targets\n",
            encoding="utf-8",
        )
        output = run_reachability(mem)
        ok = authoritative_orphan_count(output) == "orphan-file: 0"
        return _testlib.report(ok, "label with #[cfg(test)] still resolves its (x.md) link")


def check_two_links_one_line_first_label_bracketed() -> bool:
    with tempfile.TemporaryDirectory() as td:
        mem = Path(td)
        (mem / "a.md").write_text("first target\n", encoding="utf-8")
        (mem / "b.md").write_text("second target\n", encoding="utf-8")
        (mem / "MEMORY.md").write_text(
            "# Memory Index\n\n"
            "- [a has a [bracket] in its label](a.md) and also [b](b.md) - two links\n",
            encoding="utf-8",
        )
        output = run_reachability(mem)
        ok = authoritative_orphan_count(output) == "orphan-file: 0"
        return _testlib.report(ok, "two links on one line, first label bracketed, both count")


def check_201_lines_under_byte_cap_flags_line_201() -> bool:
    """The harness cuts at 200 lines as well as at the byte cap (2026-10-27 warning:
    "MEMORY.md is 201 lines (limit: 200)" on a 23,344-byte index). 201 short entries
    sit far under the byte cap, so only the line limit drops line 201."""
    with tempfile.TemporaryDirectory() as td:
        mem = Path(td)
        entries = []
        for i in range(201):
            (mem / f"e{i}.md").write_text("t\n", encoding="utf-8")
            entries.append(f"- [E{i}](e{i}.md) - x")
        (mem / "MEMORY.md").write_text("\n".join(entries) + "\n", encoding="utf-8")
        output = run_reachability(mem)
        lines = output.splitlines()
        i = next((n for n, l in enumerate(lines) if l.strip().startswith("[authoritative]")), -1)
        auth = lines[i + 1: i + 3] if i >= 0 else []
        ok = (
            "line cap: 200 (harness line limit)" in output
            and "TRUNCATING: lines 201-" in output
            and auth[:1] == ["  orphan-file: 1"]
            and auth[1:2] == ["    " + str(mem / "e200.md")]
        )
        return _testlib.report(ok, "201 lines under the byte cap: cut at 200, line 201's file is the orphan")


def main() -> int:
    checks = [
        check_bracketed_label_single_link,
        check_two_links_one_line_first_label_bracketed,
        check_201_lines_under_byte_cap_flags_line_201,
    ]
    fails = [c.__name__ for c in checks if not c()]
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
