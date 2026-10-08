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
import re
import shlex
import shutil
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
# must not trigger anything", the todo's own framing). Broader on purpose than
# skills/commit/commit-pathspec.sh's is_source_file(), which decides what must ship
# with a test file; a .css or .sql edit is still worth a fast-check run.
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


_LAUNCHED_AGENT_RE = re.compile(r"Async agent launched.*?agentId: (a[0-9a-f]+)", re.DOTALL)
_RESUMED_AGENT_RE = re.compile(r'resumedAgentId[\\"]*:\s*[\\"]*(a[0-9a-f]+)')
_NOTIFIED_TASK_RE = re.compile(r"<task-id>([A-Za-z0-9_-]+)</task-id>")
_AGENT_TOOLS = ("Agent", "Task")
_RESUME_TOOLS = ("SendMessage",)


def running_background_agents(transcript_path: str) -> set:
    """Agent ids of this session's background builders still running: the
    last event per agent wins, where a launch or a SendMessage resume
    means running and a task-notification naming it means stopped.
    Subagents write under the parent's session id, so a turn that ends
    mid-fan-out would otherwise run the floor over builders' half-written
    files (cueline 2026-10-08: a rust check timed out against a builder's
    concurrent cargo build). Only results of the session's own Agent and
    SendMessage calls count, so a Bash output quoting an agent id does not.
    An unreadable transcript means none running, so the gate keeps working.
    """
    tool_names, running = {}, {}
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if "agentId" not in line and "AgentId" not in line \
                        and "<task-notification>" not in line and '"tool_use"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                kind = entry.get("type")
                content = (entry.get("message") or {}).get("content")
                blocks = content if isinstance(content, list) else []
                if kind == "assistant":
                    for block in blocks:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_names[block.get("id")] = block.get("name")
                    continue
                results = [b for b in blocks if isinstance(b, dict) and b.get("type") == "tool_result"]
                for block in results:
                    name = tool_names.get(block.get("tool_use_id"))
                    text = json.dumps(block.get("content"))
                    if name in _AGENT_TOOLS:
                        for agent_id in _LAUNCHED_AGENT_RE.findall(text):
                            running[agent_id] = True
                    elif name in _RESUME_TOOLS:
                        for agent_id in _RESUMED_AGENT_RE.findall(text):
                            running[agent_id] = True
                # The harness records a task-notification as queue-operation
                # and attachment entries, never inside a tool result.
                if not results and "<task-notification>" in line:
                    for task_id in _NOTIFIED_TASK_RE.findall(line):
                        if task_id in running:
                            running[task_id] = False
    except (OSError, TypeError):
        return set()
    return {agent_id for agent_id, alive in running.items() if alive}


# cmd.exe's own "unrecognized command" text (the pnpm-managed-tools .cmd
# shim case) plus bash's equivalent ("bash: pnpm: command not found") so a
# check launched either way that can't actually run is still read as "not
# verified", never a failure.
_UNLAUNCHABLE_MARKERS = (
    "is not recognized as an internal or external command",
    "command not found",
)
_UNLAUNCHABLE_MARKER = _UNLAUNCHABLE_MARKERS[0]  # back-compat name some callers may still import

BASH_EXE_ENV = "TESTING_FLOOR_BASH_EXE"  # test-only override, same pattern as the other *_ENV points


def resolve_launcher(argv: list, which=shutil.which) -> list:
    """npm, pnpm and yarn are .cmd shims on Windows, which subprocess cannot
    launch by bare name without a shell, so the check never ran at all."""
    resolved = which(argv[0]) if argv else None
    return [resolved, *argv[1:]] if resolved else list(argv)


def resolve_git_bash(which=shutil.which) -> str | None:
    """Git for Windows' bash.exe, never a bare `bash` resolved from PATH -
    this machine also has WSL's bash on PATH, which would run the check
    against the wrong filesystem/toolchain entirely (todo 1139). Derived
    from git.exe's own location rather than a fixed install path, since
    Git for Windows always ships `bash.exe` as a fixed sibling of git.exe's
    own root (`<GitRoot>/bin/bash.exe`) regardless of whether git.exe
    itself resolves to `<GitRoot>/cmd/git.exe` (the common PATH entry) or
    `<GitRoot>/bin/git.exe`. The two standard install locations are a
    last-resort fallback for when `git` itself isn't on PATH.
    """
    override = os.environ.get(BASH_EXE_ENV)
    if override:
        return override if Path(override).is_file() else None

    candidates = []
    git_exe = which("git")
    if git_exe:
        git_bin_dir = Path(git_exe).resolve().parent
        candidates.append(git_bin_dir / "bash.exe")
        candidates.append(git_bin_dir.parent / "bin" / "bash.exe")
    candidates.append(Path(r"C:\Program Files\Git\bin\bash.exe"))
    candidates.append(Path(r"C:\Program Files (x86)\Git\bin\bash.exe"))

    for candidate in candidates:
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError:
            continue
    return None


def bash_launch_argv(argv: list, bash_exe: str) -> list:
    """`bash -lc "<cmd>"` - the same shell Claude's own Bash tool uses, and
    the reason it already runs pnpm's managed-tools shim fine (todo 1139's
    Notes: Git bash executes the shim's extensionless target script
    directly; cmd.exe cannot). A login shell (`-l`) so PATH is built the
    same way an interactive Git-bash session's would be, not whatever
    subprocess's own minimal env happens to pass through."""
    return [bash_exe, "-lc", shlex.join(str(a) for a in argv)]


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

    The "node" row's `argv` is a placeholder label only - `run_stack_check`
    never actually dispatches it blindly. The row is added only when
    `package.json` parses and `scripts.test` is a real, non-placeholder
    command (todo 427 defect 2): a package with no test script would make
    `npm test` exit 1 with "Missing script: test", blocking a turn for a
    project that genuinely has no tests. npm's own default placeholder
    (`echo "Error: no test specified" && exit 1`) counts as no test script.

    The "scripts repo" row's `argv` (the full `ci/run_all.py` suite) is
    likewise never run as-is by `run_stack_check` - see
    `build_scripts_repo_commands` for why (todo 427 defect 1).
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

    package_json = root / "package.json"
    if package_json.is_file():
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            pkg = {}
        test_script = str((pkg.get("scripts") or {}).get("test") or "").strip()
        # npm's own default placeholder ("Error: no test specified") means the
        # project genuinely has no test script; running it is a guaranteed
        # false failure, not a missed check.
        is_placeholder = "no test specified" in test_script.lower()
        if test_script and not is_placeholder:
            matches.append(("node", [npm_cmd(root), "test"]))

    return matches


def _scripts_repo_self_test(py_path: Path):
    """Maps an edited `hooks/<name>.py` to its `hooks/test_<norm>.py`
    self-test, per todo 427 defect 1's matching rule: strip a leading
    underscore, turn `-` into `_`. Returns None when no such file exists
    (py_compile-only - e.g. `hooks/_hooklib.py` or
    `hooks/_destructive_guard_shared.py`, neither has a direct pair).
    An edited `hooks/test_*.py` runs itself instead of looking for a pair.
    """
    if py_path.parent.name.lower() != "hooks":
        return None
    name = py_path.stem
    if name.startswith("test_"):
        return py_path if py_path.is_file() else None
    norm = name.lstrip("_").replace("-", "_")
    candidate = py_path.parent / f"test_{norm}.py"
    return candidate if candidate.is_file() else None


def build_scripts_repo_commands(root: Path, paths):
    """Targeted replacement (todo 427 defect 1) for running the whole
    `ci/run_all.py` suite - that suite serially runs all `hooks/test_*.py`
    files and takes roughly 10 minutes, far past `DEFAULT_TIMEOUT_SECONDS`,
    so every turn that edits a hook `.py` here would time out and block.

    Builds, from this turn's own accumulated edited-paths list: one
    `python -m py_compile` call over every edited `.py` path, plus one
    self-test invocation per matched `hooks/test_<norm>.py` pair (deduped,
    order preserved). `paths` entries may be absolute or repo-relative
    (`testing-floor-flag.py` records them as given); relative ones are
    resolved against `root`. No `.py` paths (including an old state file
    with no "paths" key at all) -> an empty command list, which callers
    read as "nothing targeted to verify" - never a fall-back to the full
    suite.
    """
    py_paths = []
    test_cmds = []
    seen_tests = set()
    for raw in paths or []:
        if not raw or not str(raw).lower().endswith(".py"):
            continue
        p = Path(raw)
        if not p.is_absolute():
            p = root / p
        py_paths.append(str(p))
        self_test = _scripts_repo_self_test(p)
        if self_test is not None:
            key = str(self_test)
            if key not in seen_tests:
                seen_tests.add(key)
                test_cmds.append([sys.executable, str(self_test)])

    commands = []
    if py_paths:
        commands.append([sys.executable, "-m", "py_compile", *py_paths])
    commands.extend(test_cmds)
    return commands


def run_scripts_repo_check(root: Path, timeout: int, runner, paths):
    """Runs the targeted command list from `build_scripts_repo_commands`
    (py_compile + matched self-tests), never the full `ci/run_all.py`
    suite - see that function's docstring for why. `ok` is True only if
    every targeted command exits 0 (or is skipped as "nothing to verify");
    an empty command list (no edited `.py` paths this turn) is itself a
    pass, not a failure.
    """
    commands = build_scripts_repo_commands(root, paths)
    if not commands:
        return True, "scripts repo: no edited .py paths recorded this turn; nothing targeted to verify"

    ok_all = True
    summaries = []
    for argv in commands:
        rendered = " ".join(str(a) for a in argv)
        try:
            proc = runner(argv, cwd=str(root), capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError as e:
            summaries.append(f"scripts repo ({rendered}): check command not found ({e}); nothing to verify")
            continue
        except subprocess.TimeoutExpired:
            ok_all = False
            summaries.append(f"scripts repo ({rendered}): timed out after {timeout}s")
            continue
        output = "\n".join(s for s in (proc.stdout, proc.stderr) if s)
        ok = proc.returncode == 0
        ok_all = ok_all and ok
        tail = output.strip()[-800:]
        verdict = "passed" if ok else "failed"
        summaries.append(f"scripts repo ({rendered}) {verdict} (exit {proc.returncode}): ...{tail}")
    return ok_all, " | ".join(summaries)


def run_stack_check(label: str, argv: list, root: Path, timeout: int, runner, paths=None, resolve_bash=resolve_git_bash):
    """Runs one detected stack's fast-check command. `runner` defaults to
    `subprocess.run` in production; tests inject a fake to stay deterministic.

    Flutter special-case: `fvm flutter test` returns exit 0 on a genuinely
    failing run (confirmed 2026-08-13, see skills/test/SKILL.md and
    skills/flutter-bump/references/fvm-landmines.md bug 3) - the real verdict
    has to come from stdout, never the exit code, for that one stack.

    "scripts repo" is its own special case too (todo 427 defect 1): `argv`
    is ignored and `run_scripts_repo_check` builds a targeted command list
    from `paths` instead, so this never runs the full `ci/run_all.py` suite.

    "node" launcher choice (todo 1139): the row's `argv[0]` is npm/pnpm/
    yarn, shipped on Windows as a `.cmd` shim that pnpm 12's own
    managed-tools install can break (see `resolve_git_bash`'s and
    `bash_launch_argv`'s docstrings). When a Git-bash executable resolves,
    the node row runs through it instead of the plain cmd.exe-launched
    `.cmd`, so the check actually executes rather than falling straight to
    "not verified". `resolve_bash` is a parameter (defaulting to the real
    `resolve_git_bash`) purely so a test can inject a fixed path or `None`
    without touching this machine's real Git install.
    """
    if label == "roblox":
        return True, "roblox/Luau stack detected; this hook does not run /jest-lua - verify manually"

    if label == "scripts repo":
        return run_scripts_repo_check(root, timeout, runner, paths)

    launch_argv = resolve_launcher(argv)
    if label == "node":
        bash_exe = resolve_bash()
        if bash_exe:
            launch_argv = bash_launch_argv(argv, bash_exe)

    try:
        proc = runner(launch_argv, cwd=str(root), capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        # The checker tool itself isn't on PATH - an environment gap, not a
        # code failure. Blocking a turn for that would trap the session over
        # something the dev, not the edit, would have to fix.
        return True, f"{label}: check command not found ({e}); nothing to verify"
    except subprocess.TimeoutExpired:
        # A timeout says nothing about the edit (a concurrent build holding the
        # target dir is the usual cause), and blocking on it cost up to 3 x 300s.
        return True, f"{label}: check timed out after {timeout}s; not verified"

    output = "\n".join(s for s in (proc.stdout, proc.stderr) if s)
    if proc.returncode != 0 and any(marker in output for marker in _UNLAUNCHABLE_MARKERS):
        # Either cmd.exe couldn't run a .cmd shim, or (bash launch) the
        # resolved shell itself reported the package manager missing -
        # neither says anything about the edit under test.
        return True, f"{label}: check command could not launch ({output.strip()[:200]}); not verified"
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


def run_checks(root: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS, runner=subprocess.run, paths=None, resolve_bash=resolve_git_bash):
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

    `paths` (optional, new in todo 427 defect 1) is this turn's own
    accumulated edited-source-paths list, forwarded to the "scripts repo"
    row only - every other row's command is unaffected. Omitting it (the
    pre-defect-1 call shape) is still valid: the scripts-repo row then has
    nothing targeted to verify and passes, it never falls back to running
    the full suite.

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

    results = [
        run_stack_check(label, argv, root, timeout, runner, paths=paths, resolve_bash=resolve_bash)
        for label, argv in stacks
    ]
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
