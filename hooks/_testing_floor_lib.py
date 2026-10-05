"""Shared helper for the (unwired, todo 427) testing-floor Stop-hook pair:
`testing-floor-flag.py` (PostToolUse, sets a session-scoped "source file was
edited" flag) and `testing-floor-guard.py` (Stop, blocks turn-end while the
project's fast checks fail).

Everything here is pure or dependency-injected on purpose - see this todo's
dispatch instructions: "Your tests must be deterministic and must not depend
on this repo's real state." Every path the real hooks touch (state dir, skip
flag, retry cap, and the check-runner itself) has an env-var override or a
function parameter a test can point at a scratch location, the same
injection-point technique `skills/commit/commit-pathspec.sh` uses for its own
session-marker dir.

NOT wired into settings.json by this dispatch. See the todo for why: a Stop
hook that misfires blocks every live session's turn from ending, with no
in-session way to flip it off.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# --- env-var injection points (test-only overrides; real hooks use the defaults) ---
STATE_DIR_ENV = "TESTING_FLOOR_STATE_DIR"
SKIP_FLAG_ENV = "TESTING_FLOOR_SKIP_FLAG"
CAP_ENV = "TESTING_FLOOR_CAP"
# Test-only fault/result injection so a suite never has to install real npm/
# cargo/flutter toolchains or depend on this repo's own ci/run_all.py result:
# "pass", "fail", or "raise" (to exercise the fail-open path). Unset in real use.
FAKE_CHECK_ENV = "TESTING_FLOOR_FAKE_CHECK"

# The real, documented escape hatch (see testing-floor-guard.py's module
# docstring): a dev sets this env var, or drops the skip-flag file, to make
# the Stop hook exit 0 unconditionally. Neither requires touching
# settings.json or the session having seen a magic phrase - the hook checks
# for both, every time, regardless of what the conversation said.
ESCAPE_ENV_VAR = "CLAUDE_TESTING_FLOOR_SKIP"

# Conservative on purpose: docs and a reference implementation
# (`refs/harvest-2026-08-20-oss-claude-repos.md`'s brain-bootstrap citation)
# disagree on the harness's real consecutive-Stop-block ceiling (8 vs 25), and
# this dispatch is banned from wiring the hook to measure it live. 3 sits
# comfortably under either candidate number, so this hook's own cap always
# binds first regardless of which is true - Joe re-checks the real ceiling
# empirically when he wires this and watches the first few turns (see the
# dispatch report).
DEFAULT_CAP = 3

# "Fast checks" per CLAUDE.md's testing floor; a hang past this is treated as
# a failed check (bounded by DEFAULT_CAP below), not a hook bug. Never runs
# e2e/Playwright here - that suite class is explicitly out of scope (todo).
DEFAULT_TIMEOUT_SECONDS = 300

EDIT_TOOL_SUFFIXES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Config/doc-shaped suffixes stay excluded even if a future stack's source
# extension were to collide - defense in depth alongside the inclusion list
# below, and the explicit place a reviewer expects to find "why not .toml".
EXCLUDED_SUFFIXES = {
    ".md", ".mdx", ".json", ".yaml", ".yml", ".lock", ".toml",
    ".txt", ".ini", ".cfg", ".env",
}

# Deliberately an allowlist, not a denylist: an unrecognised extension stays
# OFF (activation gate biases toward silence - "most turns edit prose and
# must not trigger anything", the todo's own framing).
SOURCE_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx",
    ".rs", ".dart", ".lua", ".luau", ".go", ".rb",
    ".java", ".kt", ".kts", ".swift",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php",
    ".sh", ".ps1", ".css", ".scss", ".less", ".vue", ".svelte", ".sql",
}

# This repo's own prose/backlog directories, plus generic build/vendor noise.
# Path-segment match (case-insensitive), not a substring match, so a real
# source dir that happens to contain "test" as a substring is unaffected.
EXCLUDED_DIR_SEGMENTS = {
    "todos", "skills", "refs", "done", ".claims",
    "node_modules", "__pycache__", ".git",
    ".session-markers", ".testing-floor-pending", ".for_bepy",
    "dist", "build", ".venv", "venv",
}


def resolve_state_dir() -> Path:
    override = os.environ.get(STATE_DIR_ENV)
    if override:
        return Path(override)
    return _HOOKS_DIR / ".testing-floor-pending"


def resolve_skip_flag_path() -> Path:
    override = os.environ.get(SKIP_FLAG_ENV)
    if override:
        return Path(override)
    return _HOOKS_DIR / ".testing-floor-skip"


def resolve_cap() -> int:
    override = os.environ.get(CAP_ENV)
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    return DEFAULT_CAP


def is_source_file(path: str) -> bool:
    """True only for an extension this hook actively recognises as "source
    for a known fast-check stack", outside an excluded (prose/backlog/vendor)
    directory. Everything else - unknown extensions included - is False, so
    the activation gate never over-fires on a stack this hook doesn't know
    how to verify.
    """
    normalized = (path or "").replace("\\", "/")
    if not normalized:
        return False
    segments = {seg.lower() for seg in normalized.split("/") if seg}
    if segments & EXCLUDED_DIR_SEGMENTS:
        return False
    suffix = Path(normalized).suffix.lower()
    if suffix in EXCLUDED_SUFFIXES:
        return False
    return suffix in SOURCE_SUFFIXES


_is_agent_call_fn = None


def is_agent_call(payload: dict) -> bool:
    """Reuses `agent-todo-write-guard.py`'s own `is_agent_call` (the
    mechanical test the dispatch names: `agent_id` present means the call
    came from a dispatched agent) rather than re-deriving the same check, the
    same by-path-import technique that hook's own module docstring uses for
    `todos_target_dir`. Loaded lazily and cached so importing this module
    never has a side effect at import time.
    """
    global _is_agent_call_fn
    if _is_agent_call_fn is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "agent_todo_write_guard", _HOOKS_DIR / "agent-todo-write-guard.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _is_agent_call_fn = module.is_agent_call
    return _is_agent_call_fn(payload)


def npm_cmd(root: Path) -> str:
    if (root / "pnpm-lock.yaml").is_file():
        return "pnpm"
    if (root / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def detect_stack(root: Path):
    """Marker-file stack detection mirroring `skills/test/SKILL.md`'s table
    (same rows, same markers) so this hook's notion of "the project's fast
    checks" doesn't drift from what `/test` would run by hand. Returns a
    LIST of every `(label, argv)` row `root` matches, per that SKILL.md's
    Step 1: "A repo can match more than one row (a Tauri app matches Rust
    *and* Node); run every row it matches." An empty list means "nothing
    recognised" ("nothing to verify", not "verification failed"), so
    callers must not block on it.
    """
    matches = []

    if (root / "ci" / "run_all.py").is_file():
        matches.append(("scripts repo", [sys.executable, "ci/run_all.py"]))

    pubspec = root / "pubspec.yaml"
    if pubspec.is_file():
        try:
            text = pubspec.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        if "flutter:" in text:
            matches.append(("flutter", ["fvm", "flutter", "test"]))

    # Root Cargo.toml takes precedence over a src-tauri/ one so a Tauri repo
    # (which has both) is counted as a single "rust" match, not two.
    cargo_root = root / "Cargo.toml"
    cargo_tauri = root / "src-tauri" / "Cargo.toml"
    if cargo_root.is_file():
        matches.append(("rust", ["cargo", "test", "--lib", "--manifest-path", str(cargo_root)]))
    elif cargo_tauri.is_file():
        matches.append(("rust", ["cargo", "test", "--lib", "--manifest-path", str(cargo_tauri)]))

    # Roblox/Luau: /test hands this to /jest-lua, a natural-language skill a
    # hook cannot invoke. Detected (so it's never silently mistaken for "no
    # stack") but never executed here - see run_stack_check's "roblox" arm.
    # Same single-match precedence reasoning as rust above.
    if (root / "test.project.json").is_file() or (root / "testing" / "wally.toml").is_file():
        matches.append(("roblox", []))
    else:
        try:
            if any(root.glob("*.rbxlx")):
                matches.append(("roblox", []))
        except OSError:
            pass

    if (root / "package.json").is_file():
        matches.append(("node", [npm_cmd(root), "test"]))

    return matches


def run_stack_check(label: str, argv: list, root: Path, timeout: int, runner):
    """Runs one detected stack's fast-check command. `runner` defaults to
    `subprocess.run` in production; tests inject a fake to stay deterministic.

    Flutter special-case: `fvm flutter test` returns exit 0 on a genuinely
    failing run (confirmed 2026-08-13, see skills/test/SKILL.md and
    skills/flutter-bump/references/fvm-landmines.md bug 3) - the real verdict
    has to come from stdout, never the exit code, for that one stack.
    """
    if label == "roblox":
        return True, "roblox/Luau stack detected; this hook does not run /jest-lua - verify manually"

    try:
        proc = runner(argv, cwd=str(root), capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        # The checker tool itself isn't on PATH - an environment gap, not a
        # code failure. Blocking a turn for that would trap the session over
        # something the dev, not the edit, would have to fix.
        return True, f"{label}: check command not found ({e}); nothing to verify"
    except subprocess.TimeoutExpired:
        return False, f"{label}: check timed out after {timeout}s"

    output = "\n".join(s for s in (proc.stdout, proc.stderr) if s)
    if label == "flutter":
        ok = "All tests passed!" in output
    else:
        ok = proc.returncode == 0
    tail = output.strip()[-800:]
    verdict = "passed" if ok else "failed"
    return ok, f"{label} check {verdict} (exit {proc.returncode}): ...{tail}"


def sweep_node_orphans() -> None:
    """Best-effort orphan sweep after a Node-based check run (process-hygiene
    doctrine's Layer 3). Deliberately does not append concurrency flags to
    the detected `npm test` (etc.) invocation itself - the underlying script
    is framework-unknown from here (vitest, jest, something custom), and a
    blindly-injected flag can break an invocation that a real Node runner
    would have accepted as-is. This sweep is the safety net instead. Must
    never raise: a failure here is not a check failure.
    """
    try:
        subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
                "Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
            ],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        pass


def run_checks(root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS, runner=subprocess.run):
    """(ok, summary) aggregated across EVERY stack `detect_stack` matches
    under `root`, not just the first - a dual-stack repo (Tauri: Rust +
    Node; Roblox + Node) must have both checked, per `skills/test/
    SKILL.md`'s "run every row it matches" rule this hook exists to
    enforce (todo 427 Notes item 4). `ok` is True only if every matched
    stack's own check passed; `summary` joins each stack's own summary
    (each already names its own label) so a failure is traceable to the
    stack that caused it. `runner` defaults to a real `subprocess.run`;
    tests always inject a fake so a suite never needs a real npm/cargo/
    flutter toolchain installed.

    TESTING_FLOOR_FAKE_CHECK, if set, short-circuits everything below it
    (including stack detection) - the one deliberate exception to "no test
    reads the real repo": some cases (escape hatch, cap, activation gate)
    care only about the DECISION logic around a check result, not the
    detection/execution machinery, and stubbing here keeps those tests from
    also having to fabricate a fake project on disk.
    """
    fake = os.environ.get(FAKE_CHECK_ENV)
    if fake is not None:
        if fake == "raise":
            raise RuntimeError("TESTING_FLOOR_FAKE_CHECK=raise (test-only fault injection)")
        if fake == "pass":
            return True, "stubbed pass (TESTING_FLOOR_FAKE_CHECK)"
        return False, f"stubbed fail (TESTING_FLOOR_FAKE_CHECK={fake})"

    stacks = detect_stack(root)
    if not stacks:
        return True, f"no recognised fast-check stack detected under {root}; nothing to verify"

    results = [run_stack_check(label, argv, root, timeout, runner) for label, argv in stacks]
    ok = all(stack_ok for stack_ok, _summary in results)
    summary = " | ".join(stack_summary for _ok, stack_summary in results)
    if any(label == "node" for label, _argv in stacks):
        sweep_node_orphans()
    return ok, summary


def read_state(flag_path: Path) -> dict:
    try:
        return json.loads(flag_path.read_text(encoding="utf-8") or "{}")
    except (OSError, ValueError):
        return {}


def write_state(flag_path: Path, state: dict) -> None:
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(json.dumps(state), encoding="utf-8")


def clear_state(flag_path: Path) -> None:
    try:
        flag_path.unlink()
    except OSError:
        pass
