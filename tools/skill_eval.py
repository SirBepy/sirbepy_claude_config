"""Eval harness for skills: run fixtures through a skill, grade them blind.

Answers the one question `bepy-skill-creator` cannot: did an edit to a skill make
it BETTER at its job, rather than merely conformant to conventions.

Mechanism, and the reason it is a subprocess runner rather than an in-session
skill: each fixture is executed by a fresh `claude -p` process that really
invokes the skill, then graded by a SECOND `claude -p` process that is launched
with every tool disallowed and is never told which skill produced the text. The
grader's independence is therefore structural (a different process, no file
access, no skill identity in its prompt) and inspectable via --dry-run, not a
promise made in a prompt. `tools/test_skill_eval.py` asserts the no-leak
property over the real fixture files on every CI run.

NOT a CI check and must never join `ci/run_all.py`'s CHECKS tuple: it spends
real money (~$0.20 per process) and needs network. The unit tests of its pure
logic are the CI-able part, and those are wired.

Usage:
    python tools/skill_eval.py --skill rate-it --label v0-baseline
    python tools/skill_eval.py --skill rate-it --label v1-verify --parent v0-baseline
    python tools/skill_eval.py --skill rate-it --label x --dry-run
    python tools/skill_eval.py --skill rate-it --label v0-baseline --regrade
    python tools/skill_eval.py --skill rate-it --label mutant \\
        --skill-under-test C:\\tmp\\mutant\\rate-it --only 2,3

Results land in scratch (`C:\\tmp\\skill-eval\\<skill>\\<label>\\`), never the
repo: they contain full model output and are regenerable. Only the pass rates
and the hashes that make them comparable are committed, in the skill's own
`evals/history.json`.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

# The grader reasons over text handed to it and nothing else. Denying Read/Grep
# is what makes "it cannot see the skill it is grading" a fact about the process.
GRADER_DENIED_TOOLS = (
    "Write", "Edit", "MultiEdit", "NotebookEdit", "Read", "Grep", "Glob",
    "Bash", "PowerShell", "Task", "Agent", "WebSearch", "WebFetch", "TodoWrite",
)
VERDICTS = ("PASS", "FAIL", "UNVERIFIABLE")
MAX_INLINE_OUTPUT_CHARS = 40000
DEFAULT_MODEL = "sonnet"
CONCURRENCY_CAP = 5  # global process-hygiene rule, never exceed
SCRATCH_ROOT = Path("C:/tmp/skill-eval")


# ---------------------------------------------------------------- pure helpers

def load_evals(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("skill_name", "fixture_set_version", "fixtures"):
        if key not in data:
            raise ValueError(f"{path}: missing required key {key!r}")
    seen = set()
    for fixture in data["fixtures"]:
        for key in ("id", "label", "prompt", "task_for_grader", "expectations"):
            if key not in fixture:
                raise ValueError(f"{path}: fixture {fixture.get('id')} missing {key!r}")
        if fixture["id"] in seen:
            raise ValueError(f"{path}: duplicate fixture id {fixture['id']}")
        seen.add(fixture["id"])
        if not fixture["expectations"]:
            raise ValueError(f"{path}: fixture {fixture['id']} has no expectations")
    return data


def canonical_hash(payload) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def fixture_set_hash(evals: dict) -> str:
    graded = [
        {"id": f["id"], "prompt": f["prompt"], "expectations": f["expectations"]}
        for f in sorted(evals["fixtures"], key=lambda f: f["id"])
    ]
    return canonical_hash(graded)


def skill_hash(skill_dir: Path) -> str:
    parts = {}
    for path in sorted(skill_dir.rglob("*.md")):
        if "evals" in path.relative_to(skill_dir).parts:
            continue
        parts[path.relative_to(skill_dir).as_posix()] = path.read_text(encoding="utf-8")
    return canonical_hash(parts)


def resolve_skill_hash(regrade: bool, prior_entry: dict, computed: str) -> str:
    """A regrade must keep the hash of the skill that produced the responses.

    Re-hashing at regrade time silently attributes an old run to whatever the
    skill looks like now, which is exactly wrong when the run under study was a
    mutation that has since been restored.
    """
    if regrade and prior_entry and prior_entry.get("skill_hash"):
        return prior_entry["skill_hash"]
    return computed


def build_grader_prompt(template: str, fixture: dict, response: str) -> str:
    numbered = "\n".join(
        f"{i}. {text}" for i, text in enumerate(fixture["expectations"], start=1)
    )
    return (
        template
        .replace("{{TASK}}", fixture["task_for_grader"].strip())
        .replace("{{EXPECTATIONS}}", numbered)
        .replace("{{RESPONSE}}", response.strip())
    )


def extract_json_object(raw: str) -> dict:
    """Pull the grader's JSON out of a reply that may be fenced or prefaced."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("grader reply contained no JSON object")
        candidate = raw[start:end + 1]
    return json.loads(candidate)


def parse_grading(raw: str, fixture: dict) -> dict:
    obj = extract_json_object(raw)
    rows = obj.get("expectations")
    if not isinstance(rows, list):
        raise ValueError("grader JSON has no 'expectations' list")
    expected_count = len(fixture["expectations"])
    if len(rows) != expected_count:
        raise ValueError(
            f"grader returned {len(rows)} verdicts for {expected_count} expectations"
        )
    graded = []
    for text, row in zip(fixture["expectations"], rows):
        verdict = str(row.get("verdict", "")).strip().upper()
        if verdict not in VERDICTS:
            raise ValueError(f"unknown verdict {verdict!r}")
        graded.append({
            "text": text,
            "verdict": verdict,
            "evidence": str(row.get("evidence", "")).strip(),
        })
    return {
        "expectations": graded,
        "grader_notes": str(obj.get("notes", "")).strip(),
        "weak_expectations": obj.get("weak_expectations", []),
    }


def summarize(fixture_results: list) -> dict:
    counts = {v: 0 for v in VERDICTS}
    for result in fixture_results:
        for row in result.get("expectations", []):
            counts[row["verdict"]] += 1
    total = sum(counts.values())
    errored = [r["id"] for r in fixture_results if r.get("error")]
    return {
        "passed": counts["PASS"],
        "failed": counts["FAIL"],
        "unverifiable": counts["UNVERIFIABLE"],
        "total": total,
        "pass_rate": round(counts["PASS"] / total, 4) if total else 0.0,
        "errored_fixtures": errored,
    }


def compare(previous: dict, current: dict) -> str:
    """won / lost / tied, or incomparable when the graded set is not the same one.

    Both guards matter: an edited expectation changes the hash, and --only
    changes which fixtures were graded, so a subset run against a full baseline
    is a different measurement wearing the same units.
    """
    if previous is None:
        return "baseline"
    if previous.get("fixture_set_hash") != current.get("fixture_set_hash"):
        return "incomparable"
    if sorted(previous.get("fixture_ids") or []) != sorted(current.get("fixture_ids") or []):
        return "incomparable"
    if (previous.get("repeat") or 1) != (current.get("repeat") or 1):
        return "incomparable"
    before, after = previous["summary"]["pass_rate"], current["summary"]["pass_rate"]
    if after > before:
        return "won"
    if after < before:
        return "lost"
    return "tied"


# ------------------------------------------------------------------- processes

def claude_cli() -> str:
    found = shutil.which("claude")
    if not found:
        raise RuntimeError("`claude` not on PATH; the harness cannot run")
    return found


def format_turns(first: str, follow_up: str, second: str) -> str:
    """Two assistant turns, graded as one transcript.

    Some rules only exist across a turn boundary (holding a score when the dev
    pushes back), and a single -p call cannot exercise them at all.
    """
    return (
        "FIRST REPLY\n" + first.strip()
        + "\n\nTHE USER THEN SAID: " + follow_up.strip()
        + "\n\nSECOND REPLY\n" + second.strip()
    )


def build_claude_argv(cli: str, model: str, denied_tools=(), allowed_tools=(),
                      resume: str = None) -> list:
    """Argv carries flags only; the prompt always goes in on stdin.

    --disallowed-tools is variadic, so a positional prompt after it is eaten as
    another tool name and the CLI dies with "Input must be provided" (cost a
    whole $1.88 grader pass on 2026-08-21). stdin has no such ambiguity.
    """
    argv = [cli, "-p", "--model", model, "--output-format", "json"]
    if resume:
        argv += ["--resume", resume]
    if denied_tools:
        argv += ["--disallowed-tools", *denied_tools]
    if allowed_tools:
        argv += ["--allowed-tools", *allowed_tools]
    return argv


def run_claude(prompt: str, *, model: str, cwd: Path, timeout: int,
               denied_tools=(), allowed_tools=(), resume: str = None) -> dict:
    argv = build_claude_argv(claude_cli(), model, denied_tools, allowed_tools, resume)
    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), input=prompt, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "text": "", "cost_usd": 0.0}
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"exit {proc.returncode}: {(proc.stderr or proc.stdout)[-600:]}",
            "text": "", "cost_usd": 0.0,
        }
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "non-JSON CLI output", "text": proc.stdout[-600:], "cost_usd": 0.0}
    if payload.get("is_error"):
        return {"ok": False, "error": str(payload.get("result"))[:600], "text": "", "cost_usd": 0.0}
    return {
        "ok": True,
        "text": payload.get("result", ""),
        "cost_usd": float(payload.get("total_cost_usd") or 0.0),
        "duration_s": round((datetime.now(timezone.utc) - started).total_seconds(), 1),
        "session_id": payload.get("session_id"),
    }


def stability(results: list) -> list:
    """Per-expectation PASS count across repeats, worst first.

    The number that matters once --repeat is used. A single run's pass rate
    moves by an expectation or two on its own: same response graded twice, and
    same prompt run twice, both produced different verdicts during 422's build.
    An expectation that is 3/3 in one version and 0/3 in another is a signal; a
    pass rate that moved four points is not.
    """
    tally = {}
    for result in results:
        for index, row in enumerate(result.get("expectations", [])):
            key = (result["id"], index)
            slot = tally.setdefault(key, {"text": row["text"], "passed": 0, "runs": 0})
            slot["passed"] += row["verdict"] == "PASS"
            slot["runs"] += 1
    rows = [
        {"fixture": fid, "n": index + 1, "passed": v["passed"], "runs": v["runs"],
         "text": v["text"]}
        for (fid, index), v in sorted(tally.items())
    ]
    rows.sort(key=lambda r: (r["passed"] / r["runs"], r["fixture"], r["n"]))
    return rows


def run_fixture(fixture: dict, *, run_dir: Path, template: str, model: str,
                regrade: bool, executor_cwd: Path, rep: int = 1,
                repeats: int = 1) -> dict:
    out_dir = run_dir / f"f{fixture['id']:02d}-{fixture['label']}"
    if repeats > 1:
        out_dir = out_dir / f"rep{rep}"
    out_dir.mkdir(parents=True, exist_ok=True)
    response_path = out_dir / "response.txt"
    result = {"id": fixture["id"], "label": fixture["label"], "rep": rep,
              "dir": str(out_dir)}

    if regrade and response_path.is_file():
        response = response_path.read_text(encoding="utf-8")
        result["executor"] = {"reused": True}
    else:
        timeout = int(fixture.get("timeout_seconds", 300))
        executed = run_claude(fixture["prompt"], model=model, cwd=executor_cwd, timeout=timeout)
        result["executor"] = {k: v for k, v in executed.items() if k != "text"}
        if not executed["ok"]:
            result["error"] = f"executor: {executed['error']}"
            return result
        response = executed["text"]
        if fixture.get("follow_up"):
            session = executed.get("session_id")
            if not session:
                result["error"] = "executor: no session_id to resume for follow_up"
                return result
            second = run_claude(fixture["follow_up"], model=model, cwd=executor_cwd,
                                timeout=timeout, resume=session)
            result["executor_follow_up"] = {k: v for k, v in second.items() if k != "text"}
            if not second["ok"]:
                result["error"] = f"executor follow-up: {second['error']}"
                return result
            response = format_turns(response, fixture["follow_up"], second["text"])
        response_path.write_text(response, encoding="utf-8")

    if len(response) > MAX_INLINE_OUTPUT_CHARS:
        result["error"] = f"response too long to grade inline ({len(response)} chars)"
        return result

    grader_prompt = build_grader_prompt(template, fixture, response)
    (out_dir / "grader-prompt.txt").write_text(grader_prompt, encoding="utf-8")
    graded = run_claude(
        grader_prompt, model=model, cwd=executor_cwd, timeout=300,
        denied_tools=GRADER_DENIED_TOOLS,
    )
    result["grader"] = {k: v for k, v in graded.items() if k != "text"}
    if not graded["ok"]:
        result["error"] = f"grader: {graded['error']}"
        return result
    (out_dir / "grader-raw.txt").write_text(graded["text"], encoding="utf-8")
    try:
        result.update(parse_grading(graded["text"], fixture))
    except ValueError as exc:
        result["error"] = f"grader parse: {exc}"
    return result


# --------------------------------------------------------------------- history

def read_history(path: Path) -> dict:
    if not path.is_file():
        return {"skill_name": None, "runs": []}
    return json.loads(path.read_text(encoding="utf-8"))


def append_history(path: Path, entry: dict) -> dict:
    """Fresh read immediately before the write: concurrent sessions share this repo."""
    history = read_history(path)
    history["skill_name"] = entry["skill_name"]
    history["runs"] = [r for r in history.get("runs", []) if r["label"] != entry["label"]]
    history["runs"].append(entry)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return history


# ------------------------------------------------------------------------ main

def main() -> int:
    # Model output carries emoji; a cp1252 console would otherwise kill the run
    # after the money was already spent.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    default_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--skill", required=True, help="skill name under skills/")
    parser.add_argument("--label", required=True, help="run label, e.g. v0-baseline")
    parser.add_argument("--parent", default=None, help="label this run is compared against")
    parser.add_argument("--skill-under-test", type=Path, default=None,
                        help="hash this dir instead of skills/<skill> (mutant copies)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--only", default=None, help="comma-separated fixture ids")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--repeat", type=int, default=1,
                        help="run each fixture N times; below 3 the noise swamps the signal")
    parser.add_argument("--regrade", action="store_true",
                        help="reuse saved responses, re-run only the grader")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the exact prompts and commands, spend nothing")
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    skill_dir = root / "skills" / args.skill
    evals_path = skill_dir / "evals" / "evals.json"
    template_path = root / "tools" / "grader_prompt.md"
    if not evals_path.is_file():
        print(f"FAIL: no fixtures at {evals_path}")
        return 1

    evals = load_evals(evals_path)
    template = template_path.read_text(encoding="utf-8")
    fixtures = evals["fixtures"]
    if args.only:
        wanted = {int(x) for x in args.only.split(",")}
        fixtures = [f for f in fixtures if f["id"] in wanted]
    if not fixtures:
        print("FAIL: no fixtures selected")
        return 1

    hashed_dir = (args.skill_under_test or skill_dir).resolve()
    set_hash = fixture_set_hash(evals)
    prior_path = SCRATCH_ROOT / args.skill / args.label / "results.json"
    prior_entry = (
        json.loads(prior_path.read_text(encoding="utf-8")).get("entry")
        if prior_path.is_file() else None
    )
    sk_hash = resolve_skill_hash(args.regrade, prior_entry, skill_hash(hashed_dir))
    print(f"skill={args.skill} label={args.label} fixtures={len(fixtures)}")
    print(f"fixture_set_hash={set_hash} skill_hash={sk_hash} (hashed: {hashed_dir})")

    if args.dry_run:
        for fixture in fixtures:
            print("\n" + "=" * 70)
            print(f"FIXTURE {fixture['id']} ({fixture['label']}) mode={fixture.get('mode', 'solo')}")
            executor_argv = build_claude_argv("claude", args.model)
            grader_argv = build_claude_argv("claude", args.model, GRADER_DENIED_TOOLS)
            print(f"--- executor: {' '.join(executor_argv)}\n"
                  f"    stdin: {fixture['prompt']!r}")
            print(f"--- grader: {' '.join(grader_argv)}\n    stdin: the prompt below")
            print("--- grader prompt ---")
            print(build_grader_prompt(template, fixture, "<EXECUTOR RESPONSE GOES HERE>"))
        return 0

    run_dir = SCRATCH_ROOT / args.skill / args.label
    run_dir.mkdir(parents=True, exist_ok=True)
    executor_cwd = Path(tempfile.mkdtemp(prefix="skill-eval-cwd-"))

    workers = max(1, min(args.concurrency, CONCURRENCY_CAP))
    repeats = max(1, args.repeat)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(run_fixture, f, run_dir=run_dir, template=template,
                        model=args.model, regrade=args.regrade,
                        executor_cwd=executor_cwd, rep=rep, repeats=repeats)
            for f in fixtures for rep in range(1, repeats + 1)
        ]
        results = [fut.result() for fut in futures]
    results.sort(key=lambda r: (r["id"], r["rep"]))

    cost = sum(
        (r.get(stage) or {}).get("cost_usd", 0.0)
        for r in results for stage in ("executor", "executor_follow_up", "grader")
    )
    summary = summarize(results)

    for result in results:
        rep = f" rep{result['rep']}" if repeats > 1 else ""
        if result.get("error"):
            print(f"\nERROR f{result['id']}{rep} ({result['label']}): {result['error']}")
            continue
        rows = result["expectations"]
        good = sum(1 for r in rows if r["verdict"] == "PASS")
        print(f"\nf{result['id']}{rep} {result['label']}: {good}/{len(rows)} PASS")
        for row in rows:
            if row["verdict"] != "PASS":
                print(f"  {row['verdict']}: {row['text']}")
                print(f"    evidence: {row['evidence'][:220]}")

    if repeats > 1:
        print("\n--- per-expectation stability across repeats (worst first) ---")
        for row in stability(results):
            if row["passed"] < row["runs"]:
                print(f"  f{row['fixture']} e{row['n']}: {row['passed']}/{row['runs']} PASS"
                      f"  {row['text'][:90]}")

    print("\n" + "=" * 70)
    print(f"pass_rate={summary['pass_rate']:.2%} "
          f"({summary['passed']} PASS / {summary['failed']} FAIL / "
          f"{summary['unverifiable']} UNVERIFIABLE of {summary['total']})")
    print(f"cost=${cost:.2f}  run_dir={run_dir}")

    entry = {
        "label": args.label,
        "parent": args.parent,
        "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skill_name": evals["skill_name"],
        "fixture_set_version": evals["fixture_set_version"],
        "fixture_set_hash": set_hash,
        "skill_hash": sk_hash,
        "hashed_dir": str(hashed_dir),
        "fixture_ids": [f["id"] for f in fixtures],
        "model": args.model,
        "repeat": repeats,
        "summary": summary,
        "stability": stability(results) if repeats > 1 else None,
        "cost_usd": round(cost, 2),
        "run_dir": str(run_dir),
        "per_fixture": [
            {
                "id": r["id"],
                "rep": r["rep"],
                "label": r["label"],
                "passed": sum(1 for x in r.get("expectations", []) if x["verdict"] == "PASS"),
                "total": len(r.get("expectations", [])),
                "error": r.get("error"),
            }
            for r in results
        ],
    }
    (run_dir / "results.json").write_text(
        json.dumps({"entry": entry, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    history_path = skill_dir / "evals" / "history.json"
    if not args.no_history:
        history = read_history(history_path)
        prior = next((r for r in history.get("runs", []) if r["label"] == args.parent), None)
        entry["verdict"] = compare(prior, entry)
        append_history(history_path, entry)
        print(f"verdict={entry['verdict']} (vs parent {args.parent}) -> {history_path}")

    if summary["errored_fixtures"]:
        print(f"FAIL: {len(summary['errored_fixtures'])} fixture(s) errored: "
              f"{summary['errored_fixtures']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
