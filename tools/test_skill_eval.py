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
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "tools"))

import _testlib  # noqa: E402
import skill_eval as se  # noqa: E402

PILOT = "rate-it"
SHINGLE_WORDS = 12


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
    ):
        if not fn():
            fails.append(fn.__name__)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
