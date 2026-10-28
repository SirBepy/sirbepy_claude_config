"""One-shot migration of legacy bare-numeric todo ids to device-prefixed ids.

    python tools/migrate-todo-ids.py                  # dry run over every repo (default)
    python tools/migrate-todo-ids.py --repo <path>    # limit to one repo root
    python tools/migrate-todo-ids.py --apply          # actually rename/rewrite
    python tools/migrate-todo-ids.py --apply --log out.json

For every repo root that has `.claude/todos/` (each child of ~/Desktop/Projects plus
~/.claude, or just --repo), this turns the pre-label scheme into `pc-<NNNN>`: every todo
made before device labels existed was made on this PC, so the label is always `pc`
(hooks/_todo_ids.py LEGACY_LABEL), not the label of whichever machine runs this.

  * backlog and done/ files `1407-slug.md` / `07-x.md` -> `pc-1407-slug.md` / `pc-0007-x.md`
    (`git mv` when git tracks the file, a plain rename otherwise: opt-in repos track their
    todos, the rest keep them git-excluded);
  * PLAN.md lines `- [ ] 1407 ...` (also bold / underscore / backtick wrapped, with its
    ` - label` and `[P]` kept) -> `- [ ] pc-1407 ...`, line-scoped, re-read before write;
  * `.claims/1407.claim`, `.claims/1407-slug.claim` -> `pc-1407...claim`;
  * `1407-.reserved` markers -> `pc-1407-.reserved`.

Left alone: names that already carry a label, prefix-less files, and prose references
inside todo bodies ("todo 1211"): a bare id keeps resolving to this device's `pc-1211`.

Safety: the whole repo is planned first and REFUSED (nothing touched) if any target name
already exists or two sources map to the same target. Idempotent: a second run finds no
legacy name left and does nothing. Dry run is the default; `--apply` writes a JSON log of
every rename and PLAN line change (default `~/.claude/.for_bepy/`, override with --log)
so a run can be undone by hand.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from _todo_ids import LEGACY_LABEL, format_todo_id, parse_todo_name, todo_key  # noqa: E402

HOME = Path.home()
CLAUDE_HOME = HOME / ".claude"
DEFAULT_PROJECTS_ROOT = HOME / "Desktop" / "Projects"
DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / ".for_bepy"

# The id at the start of a PLAN list item, optionally wrapped (hand-edits use all three
# wrappings, same set complete-todo.ps1 prunes). The wrapper must close with what opened.
PLAN_LINE_RE = re.compile(
    r"^(?P<head>\s*-\s*\[[ xX]?\]\s*)(?P<open>\*\*|__|`)?(?P<num>[0-9]{1,15})"
    r"(?P<close>\*\*|__|`)?(?P<tail>(?:\s.*)?)$"
)


class RepoPlan:
    def __init__(self, repo: Path):
        self.repo = repo
        self.renames = []  # dicts: kind, src, dst, git
        self.plan_changes = []  # dicts: line, before, after
        self.plan_path: Optional[Path] = None
        self.refusals = []
        self.duplicate_ids = []
        self.skipped = 0

    def count(self, kind: str) -> int:
        return sum(1 for r in self.renames if r["kind"] == kind)

    @property
    def empty(self) -> bool:
        return not self.renames and not self.plan_changes


def tracked_set(repo: Path) -> set:
    """Repo-relative posix paths git tracks under .claude/todos; empty when this is not a
    git repo or git fails (everything is then a plain rename)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", ".claude/todos"],
            capture_output=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    if out.returncode != 0:
        return set()
    return {p for p in out.stdout.decode("utf-8", errors="replace").split("\0") if p}


def legacy_target(name: str) -> Optional[str]:
    """New name for a legacy bare-numeric todo/claim/marker name, else None."""
    info = parse_todo_name(name)
    if info is None or not info.legacy:
        return None
    ext = name.rsplit(".", 1)[1]
    new_id = format_todo_id(LEGACY_LABEL, info.number)
    if ext.lower() == "reserved":
        return f"{new_id}-.reserved"
    if info.slug:
        return f"{new_id}-{info.slug}.{ext}"
    return f"{new_id}.{ext}"


def rewrite_plan_line(line: str) -> str:
    """The PLAN list item with a bare number swapped for the pc-prefixed id; unchanged
    when it is not an id line or already carries a label."""
    body = line.rstrip("\r\n")
    eol = line[len(body):]
    m = PLAN_LINE_RE.match(body)
    if not m or m.group("open") != m.group("close"):
        return line
    new_id = format_todo_id(LEGACY_LABEL, int(m.group("num")))
    wrap = m.group("open") or ""
    return f"{m.group('head')}{wrap}{new_id}{wrap}{m.group('tail')}{eol}"


def read_plan(path: Path) -> str:
    """Raw text with line endings untouched (Path.read_text would fold CRLF to LF) and any
    BOM dropped, so the rewrite is BOM-less and byte-faithful everywhere else."""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def split_lines_keep_eol(raw: str) -> list:
    return re.split(r"(?<=\n)", raw) if raw else []


def plan_repo(repo: Path) -> RepoPlan:
    plan = RepoPlan(repo)
    todos = repo / ".claude" / "todos"
    tracked = tracked_set(repo)
    sources = {}  # target path -> source path, for the two-sources-one-target check

    for sub, kind, pattern in (
        (todos, "backlog", "*.md"),
        (todos / "done", "done", "*.md"),
        (todos / ".claims", "claim", "*.claim"),
        (todos, "reserved", "*.reserved"),
    ):
        if not sub.is_dir():
            continue
        for src in sorted(sub.glob(pattern)):
            if not src.is_file():
                continue
            new_name = legacy_target(src.name)
            if new_name is None:
                plan.skipped += 1
                continue
            dst = src.with_name(new_name)
            if dst in sources:
                plan.refusals.append(f"{src.name} and {sources[dst].name} both map to {new_name}")
                continue
            sources[dst] = src
            if dst.exists():
                plan.refusals.append(f"target {dst.relative_to(repo).as_posix()} already exists (from {src.name})")
                continue
            rel = src.relative_to(repo).as_posix()
            plan.renames.append({
                "kind": kind, "src": src, "dst": dst, "git": rel in tracked,
            })

    # Ids that end up shared by two files (a pre-existing duplicate, now visible under one key).
    seen = {}
    for sub in (todos, todos / "done"):
        if not sub.is_dir():
            continue
        for f in sorted(sub.glob("*.md")):
            target = legacy_target(f.name)
            info = parse_todo_name(target or f.name)
            if info is None:
                continue
            key = todo_key(info.label, info.number)
            seen.setdefault(key, []).append(f.name)
    plan.duplicate_ids = sorted(k for k, v in seen.items() if len(v) > 1)

    plan_path = todos / "PLAN.md"
    if plan_path.is_file():
        plan.plan_path = plan_path
        plan.plan_changes = plan_changes(plan_path)
    return plan


def plan_changes(plan_path: Path) -> list:
    raw = read_plan(plan_path)
    changes = []
    for n, line in enumerate(split_lines_keep_eol(raw), start=1):
        new = rewrite_plan_line(line)
        if new != line:
            changes.append({"line": n, "before": line.rstrip("\r\n"), "after": new.rstrip("\r\n")})
    return changes


def apply_plan_rewrite(plan_path: Path, attempts: int = 3) -> list:
    """Line-scoped PLAN.md rewrite. Re-reads immediately before writing and retries from
    scratch if the file moved underneath (another session, a hand edit): never writes a
    result computed from stale content. BOM-less UTF-8 out, line endings kept."""
    for _ in range(attempts):
        before = read_plan(plan_path)
        lines = split_lines_keep_eol(before)
        rewritten = [rewrite_plan_line(l) for l in lines]
        changes = [
            {"line": i + 1, "before": a.rstrip("\r\n"), "after": b.rstrip("\r\n")}
            for i, (a, b) in enumerate(zip(lines, rewritten)) if a != b
        ]
        if not changes:
            return []
        after = "".join(rewritten)
        if read_plan(plan_path) != before:
            continue
        with open(plan_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(after)
        return changes
    raise RuntimeError(f"{plan_path} kept changing underneath the migration; re-run it")


def apply_repo(plan: RepoPlan) -> dict:
    entry = {"repo": str(plan.repo), "renames": [], "plan": None}
    for r in plan.renames:
        src, dst = r["src"], r["dst"]
        if r["git"]:
            proc = subprocess.run(
                ["git", "-C", str(plan.repo), "mv", "--",
                 src.relative_to(plan.repo).as_posix(), dst.relative_to(plan.repo).as_posix()],
                capture_output=True, text=True, timeout=60,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"git mv {src.name} failed: {proc.stderr.strip()}")
        else:
            src.rename(dst)
        entry["renames"].append({"kind": r["kind"], "from": str(src), "to": str(dst), "git": r["git"]})
    if plan.plan_path is not None and plan.plan_changes:
        entry["plan"] = {"path": str(plan.plan_path), "changes": apply_plan_rewrite(plan.plan_path)}
    return entry


def discover_repos(projects_root: Path, claude_home: Path) -> list:
    repos = []
    if projects_root.is_dir():
        repos += [d for d in sorted(projects_root.iterdir()) if (d / ".claude" / "todos").is_dir()]
    if (claude_home / ".claude" / "todos").is_dir():
        repos.append(claude_home)
    return repos


def summary_line(plan: RepoPlan, applied: bool) -> str:
    if plan.refusals:
        return f"{plan.repo}: REFUSED, nothing touched ({len(plan.refusals)} collision(s))"
    if plan.empty:
        return f"{plan.repo}: nothing to migrate" + (f" (skipped {plan.skipped} non-legacy)" if plan.skipped else "")
    git_n = sum(1 for r in plan.renames if r["git"])
    verb = "renamed" if applied else "would rename"
    line = (
        f"{plan.repo}: {verb} {plan.count('backlog')} backlog + {plan.count('done')} done todos "
        f"({git_n} via git mv), {plan.count('claim')} claims, {plan.count('reserved')} reserved markers; "
        f"{len(plan.plan_changes)} PLAN line(s)"
    )
    if plan.duplicate_ids:
        line += f"; WARNING duplicate ids already present: {', '.join(plan.duplicate_ids)}"
    return line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="act (default is a dry run)")
    ap.add_argument("--repo", type=Path, help="limit to this one repo root")
    ap.add_argument("--log", type=Path, help="JSON rename log path (with --apply)")
    ap.add_argument("--projects-root", type=Path, default=DEFAULT_PROJECTS_ROOT)
    ap.add_argument("--claude-home", type=Path, default=CLAUDE_HOME,
                    help="the ~/.claude repo (its own backlog is migrated too)")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every change")
    args = ap.parse_args(argv)

    if args.repo:
        repos = [args.repo.resolve()]
        if not (repos[0] / ".claude" / "todos").is_dir():
            sys.stderr.write(f"{repos[0]} has no .claude/todos\n")
            return 2
    else:
        repos = discover_repos(args.projects_root, args.claude_home)

    plans = [plan_repo(r) for r in repos]
    totals = {"repos": len(plans), "refused": 0, "todos": 0, "claims": 0, "reserved": 0, "plan": 0}
    log = {
        "tool": "migrate-todo-ids",
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "applied": args.apply,
        "repos": [],
    }
    exit_code = 0

    print(("APPLYING" if args.apply else "DRY RUN (pass --apply to act)") + f": {len(plans)} repo(s)")
    try:
        for plan in plans:
            if plan.refusals:
                totals["refused"] += 1
                exit_code = 1
                print(summary_line(plan, args.apply))
                for why in plan.refusals:
                    print(f"    - {why}")
                continue
            if args.apply and not plan.empty:
                log["repos"].append(apply_repo(plan))
            print(summary_line(plan, args.apply))
            if args.verbose:
                for r in plan.renames:
                    print(f"    {r['kind']}: {r['src'].name} -> {r['dst'].name}{' (git mv)' if r['git'] else ''}")
                for c in plan.plan_changes:
                    print(f"    PLAN:{c['line']}: {c['before']!r} -> {c['after']!r}")
            totals["todos"] += plan.count("backlog") + plan.count("done")
            totals["claims"] += plan.count("claim")
            totals["reserved"] += plan.count("reserved")
            totals["plan"] += len(plan.plan_changes)
    except Exception as e:  # keep what was done in the log so a partial run can be undone
        sys.stderr.write(f"ERROR: {e}\n")
        exit_code = 1
    finally:
        if args.apply and log["repos"]:
            log_path = args.log or (DEFAULT_LOG_DIR / f"migrate-todo-ids-{datetime.datetime.now():%Y%m%d-%H%M%S}.json")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(log, fh, indent=2)
                fh.write("\n")
            print(f"log: {log_path}")

    label = "renamed" if args.apply else "would rename"
    print(
        f"TOTAL: {totals['repos']} repo(s), {totals['refused']} refused; {label} {totals['todos']} todo files, "
        f"{totals['claims']} claims, {totals['reserved']} reserved markers; {totals['plan']} PLAN line(s)"
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
