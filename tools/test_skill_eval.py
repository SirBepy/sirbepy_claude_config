"""Self-tests for tools/skill_eval.py - the offline half of the eval harness.

The harness itself spends money and needs network, so it can never be a CI
check. Its pure logic can, and the load-bearing test here is the leak suite:
it rebuilds every real grader prompt from the committed fixtures and proves the
grader is never shown the skill's name, its slash command, or any twelve-word
run of its own instructions. That is what makes "the grader is independent" a
checked property instead of an intention.

Run: python tools/test_skill_eval.py
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "tools"))

import _testlib  # noqa: E402
import skill_eval as se  # noqa: E402

PILOT = "rate-it"
SHINGLE_WORDS = 12

# A synthetic skill file for the mutate/restore suite - never the real repo's
# skills/, so these tests cannot collide with a concurrent session editing it.
SAMPLE_SKILL_MD = (
    "# Title\r\n"
    "\r\n"
    "## Intro\r\n"
    "Some intro text.\r\n"
    "\r\n"
    "## How-to-raise rules\r\n"
    "Rule one.\r\n"
    "Rule two.\r\n"
    "\r\n"
    "### A subsection\r\n"
    "Still inside How-to-raise rules.\r\n"
    "\r\n"
    "## Score scale\r\n"
    "Unaffected content.\r\n"
)


def _clear_readonly_and_retry(func, path, _exc_info) -> None:
    """git marks object files read-only after writing them; rmtree's default
    unlink fails on Windows until the attribute is cleared."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _rmtree_retry(path: Path, attempts: int = 5, delay: float = 0.2) -> None:
    """Windows briefly holds a file handle open after a spawned git.exe exits,
    on top of git's own read-only object files, so a bare rmtree right after
    subprocess.run can leave the scratch dir behind (observed here)."""
    for _ in range(attempts):
        try:
            shutil.rmtree(path, onerror=_clear_readonly_and_retry)
        except OSError:
            pass
        if not path.exists():
            return
        time.sleep(delay)


class _Boom(Exception):
    """Stands in for a real crash mid-probe (the KeyboardInterrupt shape)."""


def evals_path(skill: str) -> Path:
    return ROOT / "skills" / skill / "evals" / "evals.json"


def grader_template() -> str:
    return (ROOT / "tools" / "grader_prompt.md").read_text(encoding="utf-8")


def words(text: str) -> list:
    return re.findall(r"[a-z0-9]+", text.lower())


def shingles(text: str, n: int = SHINGLE_WORDS) -> set:
    tokens = words(text)
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


# ------------------------------------------------------------------ leak suite

def check_fixtures_load() -> bool:
    try:
        data = se.load_evals(evals_path(PILOT))
        ok = data["skill_name"] == PILOT and len(data["fixtures"]) >= 5
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"  {exc}")
        ok = False
    return _testlib.report(ok, f"skills/{PILOT}/evals/evals.json loads and has 5+ fixtures")


def check_grader_prompt_hides_skill_identity() -> bool:
    data = se.load_evals(evals_path(PILOT))
    template = grader_template()
    banned = (PILOT, f"/{PILOT}", "skill.md", "panel.md", "disable-model-invocation")
    bad = []
    for fixture in data["fixtures"]:
        prompt = se.build_grader_prompt(template, fixture, "SOME RESPONSE").lower()
        bad += [f"f{fixture['id']}:{token}" for token in banned if token in prompt]
        if fixture["prompt"].lower() in prompt:
            bad.append(f"f{fixture['id']}:executor-prompt-verbatim")
    if bad:
        print(f"  leaked: {bad}")
    return _testlib.report(not bad, "no grader prompt names the skill, its command, or its files")


def check_grader_prompt_hides_skill_instructions() -> bool:
    skill_dir = ROOT / "skills" / PILOT
    corpus = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(skill_dir.glob("*.md"))
    )
    forbidden = shingles(corpus)
    data = se.load_evals(evals_path(PILOT))
    template = grader_template()
    hits = []
    for fixture in data["fixtures"]:
        prompt = se.build_grader_prompt(template, fixture, "SOME RESPONSE")
        overlap = shingles(prompt) & forbidden
        hits += [f"f{fixture['id']}: {s}" for s in sorted(overlap)[:3]]
    if hits:
        print(f"  verbatim instruction runs reached the grader: {hits}")
    return _testlib.report(
        not hits,
        f"no grader prompt echoes any {SHINGLE_WORDS}-word run of the skill's own instructions",
    )


def check_grader_is_toolless() -> bool:
    must_deny = ("Read", "Grep", "Glob", "Write", "Edit", "Bash", "Task", "WebFetch")
    missing = [t for t in must_deny if t not in se.GRADER_DENIED_TOOLS]
    if missing:
        print(f"  grader could still use: {missing}")
    return _testlib.report(not missing, "grader process is launched with file/exec/delegate tools denied")


# ------------------------------------------------------------- parsing / maths

PARSE_CASES = [
    ('{"expectations":[{"n":1,"verdict":"PASS","evidence":"x"}]}', 1, "PASS", "bare JSON object"),
    ('here you go:\n```json\n{"expectations":[{"n":1,"verdict":"fail","evidence":"y"}]}\n```',
     1, "FAIL", "fenced JSON with a preamble and lowercase verdict"),
    ('prose first {"expectations":[{"n":1,"verdict":"UNVERIFIABLE","evidence":""}]} trailing',
     1, "UNVERIFIABLE", "JSON embedded in prose"),
]


def check_parse(case) -> bool:
    raw, count, verdict, label = case
    fixture = {"expectations": ["e"] * count}
    try:
        parsed = se.parse_grading(raw, fixture)
        ok = parsed["expectations"][0]["verdict"] == verdict
    except ValueError as exc:
        print(f"  {exc}")
        ok = False
    return _testlib.report(ok, f"parse_grading: {label}")


def check_parse_rejects_bad() -> bool:
    fixture = {"expectations": ["a", "b"]}
    bad = [
        ('{"expectations":[{"n":1,"verdict":"PASS"}]}', "verdict count mismatch"),
        ('{"expectations":[{"n":1,"verdict":"MAYBE"},{"n":2,"verdict":"PASS"}]}', "unknown verdict"),
        ("no json here at all", "no JSON object"),
        ('{"summary":"all good"}', "missing expectations list"),
    ]
    fails = []
    for raw, label in bad:
        try:
            se.parse_grading(raw, fixture)
            fails.append(label)
        except ValueError:
            pass
    if fails:
        print(f"  silently accepted: {fails}")
    return _testlib.report(not fails, "parse_grading rejects malformed grader replies loudly")


def check_summarize() -> bool:
    results = [
        {"id": 1, "expectations": [
            {"verdict": "PASS"}, {"verdict": "FAIL"}, {"verdict": "UNVERIFIABLE"}]},
        {"id": 2, "expectations": [{"verdict": "PASS"}]},
        {"id": 3, "error": "executor: timeout"},
    ]
    got = se.summarize(results)
    ok = (got["passed"] == 2 and got["failed"] == 1 and got["unverifiable"] == 1
          and got["total"] == 4 and got["pass_rate"] == 0.5
          and got["errored_fixtures"] == [3])
    ok = ok and se.summarize([])["pass_rate"] == 0.0
    return _testlib.report(ok, "summarize counts UNVERIFIABLE as not-passed and surfaces errored fixtures")


def check_compare() -> bool:
    def entry(rate, set_hash="h1", ids=(1, 2, 3), repeat=1):
        return {"fixture_set_hash": set_hash, "fixture_ids": list(ids), "repeat": repeat,
                "summary": {"pass_rate": rate}}
    ok = (
        se.compare(None, entry(0.5)) == "baseline"
        and se.compare(entry(0.5), entry(0.7)) == "won"
        and se.compare(entry(0.7), entry(0.5)) == "lost"
        and se.compare(entry(0.5), entry(0.5)) == "tied"
        and se.compare(entry(0.5, "h1"), entry(0.9, "h2")) == "incomparable"
        and se.compare(entry(0.5, ids=(1, 2, 3)), entry(0.9, ids=(1, 2))) == "incomparable"
        and se.compare(entry(0.5, ids=(3, 1, 2)), entry(0.5, ids=(1, 2, 3))) == "tied"
        and se.compare(entry(0.5, repeat=1), entry(0.9, repeat=3)) == "incomparable"
    )
    return _testlib.report(
        ok, "compare refuses to call a win across a changed set, subset or repeat count")


def check_stability() -> bool:
    def run(fid, verdicts):
        return {"id": fid, "rep": 1,
                "expectations": [{"text": f"e{i}", "verdict": v} for i, v in enumerate(verdicts)]}
    rows = se.stability([
        run(5, ["PASS", "PASS", "FAIL"]),
        run(5, ["PASS", "FAIL", "FAIL"]),
        run(5, ["PASS", "PASS", "FAIL"]),
    ])
    worst, middle, best = rows[0], rows[1], rows[2]
    ok = (worst["n"] == 3 and worst["passed"] == 0 and worst["runs"] == 3
          and middle["n"] == 2 and middle["passed"] == 2
          and best["n"] == 1 and best["passed"] == 3)
    return _testlib.report(ok, "stability ranks a 0/3 expectation above a 2/3 and a 3/3")


def check_hashes() -> bool:
    data = se.load_evals(evals_path(PILOT))
    base = se.fixture_set_hash(data)
    mutated = json.loads(json.dumps(data))
    mutated["fixtures"][0]["expectations"].append("something new")
    moved = json.loads(json.dumps(data))
    moved["fixtures"].reverse()
    ok = (base == se.fixture_set_hash(moved)
          and base != se.fixture_set_hash(mutated))
    return _testlib.report(ok, "fixture_set_hash is order-independent but expectation-sensitive")


def check_skill_hash_ignores_evals() -> bool:
    skill_dir = ROOT / "skills" / PILOT
    before = se.skill_hash(skill_dir)
    stray = skill_dir / "evals" / "_hash_probe.md"
    stray.write_text("scratch\n", encoding="utf-8")
    try:
        after = se.skill_hash(skill_dir)
    finally:
        stray.unlink()
    return _testlib.report(before == after, "skill_hash ignores evals/, so adding fixtures is not a skill change")


def check_regrade_keeps_skill_hash() -> bool:
    prior = {"skill_hash": "mutantaaa"}
    ok = (se.resolve_skill_hash(True, prior, "restoredbbb") == "mutantaaa"
          and se.resolve_skill_hash(False, prior, "restoredbbb") == "restoredbbb"
          and se.resolve_skill_hash(True, None, "restoredbbb") == "restoredbbb")
    return _testlib.report(ok, "a regrade keeps the hash of the skill that produced the responses")


def check_format_turns() -> bool:
    joined = se.format_turns("  first  ", "push back", "second")
    ok = (joined.index("first") < joined.index("push back") < joined.index("second")
          and "FIRST REPLY" in joined and "SECOND REPLY" in joined)
    return _testlib.report(ok, "format_turns keeps both replies and the pushback in order")


def check_resume_is_flagged() -> bool:
    argv = se.build_claude_argv("claude", "sonnet", resume="abc-123")
    ok = "--resume" in argv and argv[argv.index("--resume") + 1] == "abc-123"
    return _testlib.report(ok, "a follow-up turn resumes the executor's own session")


def check_prompt_never_positional() -> bool:
    argv = se.build_claude_argv("claude", "sonnet", se.GRADER_DENIED_TOOLS)
    last_flag = max(i for i, tok in enumerate(argv) if tok.startswith("--"))
    trailing = argv[last_flag + 1:]
    ok = (argv[-1] in se.GRADER_DENIED_TOOLS
          and all(t in se.GRADER_DENIED_TOOLS for t in trailing))
    if not ok:
        print(f"  argv ends with something a variadic flag would eat: {trailing}")
    return _testlib.report(
        ok, "build_claude_argv leaves no positional prompt after a variadic flag (stdin only)")


def check_not_a_ci_check() -> bool:
    run_all = (ROOT / "ci" / "run_all.py").read_text(encoding="utf-8")
    checks_block = run_all.split("CHECKS = (", 1)[1].split(")", 1)[0]
    ok = "skill_eval" not in checks_block
    return _testlib.report(ok, "skill_eval.py is not wired into ci/run_all.py's CHECKS")


# ------------------------------------------------------------ mutate/restore

def check_locate_section_slices_heading_to_heading() -> bool:
    span = se.locate_section(SAMPLE_SKILL_MD, "## How-to-raise rules")
    ok = span is not None
    if ok:
        cut = SAMPLE_SKILL_MD[span[0]:span[1]]
        ok = (cut.startswith("## How-to-raise rules")
              and "Still inside How-to-raise rules" in cut
              and "## Score scale" not in cut and "Unaffected content" not in cut)
    return _testlib.report(
        ok, "locate_section spans a heading through its subsections, stopping at the next "
            "equal-or-higher heading")


def check_locate_section_returns_none_when_missing() -> bool:
    ok = se.locate_section(SAMPLE_SKILL_MD, "## Not A Real Heading") is None
    return _testlib.report(ok, "locate_section returns None for a heading that is not present")


def check_cut_sections_removes_named_section() -> bool:
    mutated, removed = se.cut_sections(SAMPLE_SKILL_MD, ["## How-to-raise rules"])
    ok = (removed > 0 and "## How-to-raise rules" not in mutated
          and "Still inside How-to-raise rules" not in mutated
          and "## Score scale" in mutated and "Unaffected content" in mutated)
    return _testlib.report(ok, "cut_sections removes a named section and leaves the rest intact")


def check_cut_sections_refuses_on_missing_heading() -> bool:
    try:
        se.cut_sections(SAMPLE_SKILL_MD, ["## How-to-raise rules", "## Does Not Exist"])
        ok = False
    except se.SectionNotFound as exc:
        ok = exc.headings == ["## Does Not Exist"]
    return _testlib.report(
        ok, "cut_sections refuses (naming only the missing heading) rather than cutting the "
            "one it did find")


def check_dangling_references_flags_leftover_mention() -> bool:
    text = "## How-to-raise rules\r\nBody.\r\n\r\n## Elsewhere\r\nSee How-to-raise rules above.\r\n"
    mutated, _ = se.cut_sections(text, ["## How-to-raise rules"])
    ok = se.dangling_references(mutated, "## How-to-raise rules") == 1
    return _testlib.report(
        ok, "dangling_references counts a leftover mention of a cut section's own label")


def check_mutated_files_round_trips_crlf_bytes() -> bool:
    tmp_dir = Path(tempfile.mkdtemp(prefix="skill-eval-mutate-"))
    path = tmp_dir / "SKILL.md"
    original = SAMPLE_SKILL_MD.encode("utf-8")
    path.write_bytes(original)
    try:
        with se.mutated_files({path: ["## How-to-raise rules"]}):
            mid = path.read_bytes()
        ok = (mid != original and b"## How-to-raise rules" not in mid
              and path.read_bytes() == original)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return _testlib.report(
        ok, "mutated_files restores the exact original bytes (CRLF) after a normal exit")


def check_mutated_files_restores_on_exception() -> bool:
    """The hard constraint of todo 478: a probe body that crashes must not
    leave a mutated file on disk. try/finally (not a sequential restore) is
    what makes this true; a plain end-of-function restore would never run."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="skill-eval-mutate-crash-"))
    path = tmp_dir / "SKILL.md"
    original = SAMPLE_SKILL_MD.encode("utf-8")
    path.write_bytes(original)
    raised = False
    try:
        try:
            with se.mutated_files({path: ["## How-to-raise rules"]}):
                assert path.read_bytes() != original
                raise _Boom("simulated crash mid-probe")
        except _Boom:
            raised = True
        restored = path.read_bytes()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    ok = raised and restored == original
    return _testlib.report(
        ok, "mutated_files restores the original bytes even when the probe body raises")


def check_assert_mutation_target_clean() -> bool:
    tmp_dir = Path(tempfile.mkdtemp(prefix="skill-eval-git-"))
    try:
        for cmd in (["init", "-q"], ["config", "user.email", "t@t.test"],
                    ["config", "user.name", "t"]):
            subprocess.run(["git", *cmd], cwd=tmp_dir, check=True, timeout=30,
                           capture_output=True)
        target = tmp_dir / "SKILL.md"
        target.write_text("# X\r\n", encoding="utf-8")
        subprocess.run(["git", "add", "SKILL.md"], cwd=tmp_dir, check=True, timeout=30,
                       capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_dir, check=True,
                       timeout=30, capture_output=True)

        allowed_when_clean = True
        try:
            se.assert_mutation_target_clean(tmp_dir, target)
        except RuntimeError:
            allowed_when_clean = False

        target.write_text("# X changed\r\n", encoding="utf-8")
        refused_when_dirty = False
        try:
            se.assert_mutation_target_clean(tmp_dir, target)
        except RuntimeError:
            refused_when_dirty = True
        ok = allowed_when_clean and refused_when_dirty
    finally:
        _rmtree_retry(tmp_dir)
    return _testlib.report(
        ok, "assert_mutation_target_clean passes on a committed file, refuses one with "
            "uncommitted changes")


def check_cli_refuses_missing_heading_and_runs_nothing() -> bool:
    """End-to-end through argv, against a throwaway skill tree (never the real
    repo's skills/), proving the missing-heading refusal fires before any file
    write - acceptance item 3 of todo 478."""
    tmp_root = Path(tempfile.mkdtemp(prefix="skill-eval-cli-"))
    try:
        skill_dir = tmp_root / "skills" / "cli-test-skill"
        (skill_dir / "evals").mkdir(parents=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(SAMPLE_SKILL_MD, encoding="utf-8")
        original = skill_md.read_bytes()
        (skill_dir / "evals" / "evals.json").write_text(json.dumps({
            "skill_name": "cli-test-skill",
            "fixture_set_version": 1,
            "fixtures": [{"id": 1, "label": "f1", "prompt": "p", "task_for_grader": "t",
                          "expectations": ["e1"]}],
        }), encoding="utf-8")
        (tmp_root / "tools").mkdir()
        (tmp_root / "tools" / "grader_prompt.md").write_text(
            "{{TASK}}\n{{EXPECTATIONS}}\n{{RESPONSE}}", encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "skill_eval.py"),
             "--root", str(tmp_root), "--skill", "cli-test-skill", "--label", "t1",
             "--dry-run", "--cut-section", "## Does Not Exist"],
            capture_output=True, text=True, timeout=30,
        )
        ok = (proc.returncode == 1 and "heading(s) not found" in proc.stdout
              and "MUTATED" not in proc.stdout and skill_md.read_bytes() == original)
        if not ok:
            print(f"  exit={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    return _testlib.report(
        ok, "CLI exits non-zero and mutates nothing when --cut-section names a missing heading")


def run() -> int:
    fails = _testlib.run_cases(PARSE_CASES, check_parse)
    for fn in (
        check_fixtures_load,
        check_grader_prompt_hides_skill_identity,
        check_grader_prompt_hides_skill_instructions,
        check_grader_is_toolless,
        check_parse_rejects_bad,
        check_summarize,
        check_compare,
        check_stability,
        check_hashes,
        check_skill_hash_ignores_evals,
        check_regrade_keeps_skill_hash,
        check_format_turns,
        check_resume_is_flagged,
        check_prompt_never_positional,
        check_not_a_ci_check,
        check_locate_section_slices_heading_to_heading,
        check_locate_section_returns_none_when_missing,
        check_cut_sections_removes_named_section,
        check_cut_sections_refuses_on_missing_heading,
        check_dangling_references_flags_leftover_mention,
        check_mutated_files_round_trips_crlf_bytes,
        check_mutated_files_restores_on_exception,
        check_assert_mutation_target_clean,
        check_cli_refuses_missing_heading_and_runs_nothing,
    ):
        if not fn():
            fails.append(fn.__name__)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
