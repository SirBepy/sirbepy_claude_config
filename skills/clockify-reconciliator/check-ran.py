#!/usr/bin/env python3
"""Pre-fire guard for the scheduled Clockify run: exit 0 when the skill already ran for the date.

Conductor runs a schedule item's guard command just before a firing would open its chat; exit 0
skips the firing and the first stdout line becomes the skip reason, any other exit code fires
normally. So this script must never exit 0 unless a marker for the date really exists: every
error path (unknown project, ambiguous cwd, unreadable folder, bad date) exits 1 and prints
nothing, because a wrong run costs one extra card and a wrong skip costs unlogged hours.

Markers are written by SKILL.md step 3 at `.runs/<project>/<YYYY-MM-DD>` next to this file. Only
that marker counts: chat history or prompt text must not, or a manual `yesterday` run would
suppress tonight's run.

Usage: check-ran.py [project]
  project  config name under projects/ (e.g. zirtue). Omitted: resolved from the cwd, the folder
           Conductor runs the guard in, against every config's `repos:` list; exactly one config
           must match.
Environment:
  CC_SCHEDULE_DATE  local YYYY-MM-DD of the firing (set by Conductor); default is today's date in
                    Europe/Zagreb, falling back to the machine's local date.
  CLOCKIFY_SKILL_DIR  overrides the skill folder (tests only).
"""
import datetime
import os
import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Project names become a path segment, so anything with a separator or dot is refused outright.
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def skill_dir() -> Path:
    return Path(os.environ.get("CLOCKIFY_SKILL_DIR") or Path(__file__).resolve().parent)


# The schedule fires at 23:55, so the day it covers ends at that firing. A firing delayed past
# midnight (PC asleep, app closed) is still that day's run: before this hour the "day" is yesterday,
# otherwise a manual run's yesterday marker would not match and the run would repeat.
NEW_DAY_FROM_HOUR = 6


def day_for(now: datetime.datetime) -> str:
    if now.hour < NEW_DAY_FROM_HOUR:
        now = now - datetime.timedelta(days=1)
    return now.strftime("%Y-%m-%d")


def today() -> str:
    try:
        from zoneinfo import ZoneInfo
        return day_for(datetime.datetime.now(ZoneInfo("Europe/Zagreb")))
    except Exception:
        # No tzdata on some Windows Pythons: the machine is in the dev's timezone anyway.
        return day_for(datetime.datetime.now())


def norm(p: str) -> str:
    return os.path.normcase(os.path.normpath(p.strip().strip("\"'")))


def config_repos(cfg: Path) -> list:
    repos, in_repos = [], False
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if re.match(r"^repos\s*:", line):
            in_repos = True
        elif in_repos:
            m = re.match(r"^\s+-\s+(.+?)\s*(#.*)?$", line)
            if m:
                repos.append(norm(m.group(1)))
            elif line.strip() and not line.lstrip().startswith("#"):
                break
    return repos


def project_from_cwd(skill: Path):
    cwd = norm(os.getcwd())
    hits = []
    for cfg in sorted((skill / "projects").glob("*.md")):
        for repo in config_repos(cfg):
            if cwd == repo or cwd.startswith(repo + os.sep):
                hits.append(cfg.stem)
                break
    return hits[0] if len(hits) == 1 else None


def main(argv) -> int:
    skill = skill_dir()
    project = argv[1] if len(argv) > 1 else project_from_cwd(skill)
    date = os.environ.get("CC_SCHEDULE_DATE") or today()
    if not project or not NAME_RE.fullmatch(project) or not DATE_RE.fullmatch(date):
        return 1
    marker = skill / ".runs" / project / date
    if not marker.is_file():
        return 1
    print(f"already ran for {date}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        sys.exit(1)
