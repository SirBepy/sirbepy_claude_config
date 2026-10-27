"""Per-repo ship config for the /release flow: which class a repo is, whether the pre-push todo
sweep runs, and whether a push bumps the version.

Prints one JSON object; a non-zero exit prints {"error": ...}.
  ship-config.py get [repo]                  {"class","todo_sweep","release","slug","source","reason"}
  ship-config.py set [repo] key=value ...    {"path","class"}   (writes the override file, never commits)

Classes: client (origin slug listed in refs/client-repos.txt), unknown (git failed, no origin, or an
unlisted repo under a client owner, which is probably a client repo nobody listed yet), personal.
Overrides, plain `key: value` lines (`#` comments ok), keys `release` (patch|none) and
`todo_sweep` (yes|no):
  personal         <repo root>/.claude/ship.md
  client, unknown  <config home>/refs/ship-config/<owner>__<repo>.md
Test hooks: env SHIP_CONFIG_HOME (config home), SHIP_CONFIG_CLIENT_LIST (client list file).

Stdlib only; runs under `python -I`.
"""

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CONFIG_HOME = _HERE.parents[1]  # skills/release -> repo root

# Resolved from __file__, never cwd: this runs from inside whichever repo is being shipped.
sys.path.insert(0, str(_CONFIG_HOME / "hooks"))
import _client_repo  # noqa: E402


def _load_release():
    spec = importlib.util.spec_from_file_location("release_mech", _HERE / "release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ALLOWED = {
    "release": {"patch", "none"},
    "todo_sweep": {"yes", "no"},
}


class Fail(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.message = message
        self.code = code


def config_home():
    return Path(os.environ.get("SHIP_CONFIG_HOME") or _CONFIG_HOME)


def client_list_path():
    override = os.environ.get("SHIP_CONFIG_CLIENT_LIST")
    return Path(override) if override else _client_repo.CLIENT_LIST_PATH


def client_slugs():
    return _client_repo.load_client_slugs(client_list_path())


def classify(repo):
    """(class, slug_or_None, repo_root_or_None, why)."""
    root = _client_repo._git(repo, "rev-parse", "--show-toplevel")
    if root is None:
        return "unknown", None, None, "not a git repo or git failed"
    slug = _client_repo.origin_slug(_client_repo._git(repo, "remote", "get-url", "origin") or "")
    if slug is None:
        return "unknown", None, Path(root), "no resolvable origin remote"
    listed = client_slugs()
    if not listed:
        # load_client_slugs returns an empty set on a read error; trusting that would resolve every
        # client repo as personal (sweep off, patch bump), so an empty list means we cannot classify.
        return "unknown", slug, Path(root), f"client list {client_list_path()} is missing, unreadable or empty"
    if slug in listed:
        return "client", slug, Path(root), f"{slug} is in client-repos.txt"
    owner = slug.split("/")[0]
    if owner in {s.split("/")[0] for s in listed}:
        return "unknown", slug, Path(root), f"unlisted repo under client owner {owner}"
    return "personal", slug, Path(root), f"{slug} is not in client-repos.txt"


def override_path(cls, slug, root):
    if cls == "personal":
        return root / ".claude" / "ship.md"
    if slug is None:
        return None
    return config_home() / "refs" / "ship-config" / (slug.replace("/", "__") + ".md")


def _split_line(line):
    key, sep, value = line.partition(":")
    return (key.strip(), value.strip()) if sep else (None, None)


def _check_pair(key, value, where):
    if key not in ALLOWED:
        raise Fail(f"{where}: unknown key '{key}' (allowed: {', '.join(sorted(ALLOWED))})")
    if value not in ALLOWED[key]:
        raise Fail(f"{where}: bad value '{value}' for {key} (allowed: {'|'.join(sorted(ALLOWED[key]))})")


def read_override(path):
    values = {}
    if path is None or not path.is_file():
        return values
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, value = _split_line(line)
        if key is None:
            raise Fail(f"{path}:{n}: expected 'key: value'")
        _check_pair(key, value, f"{path}:{n}")
        values[key] = value
    return values


def cmd_get(repo):
    cls, slug, root, why = classify(repo)
    path = override_path(cls, slug, root)
    values = read_override(path)

    notes = [why]
    if cls == "personal":
        todo_sweep = values.get("todo_sweep") == "yes"
        src, _ver = _load_release().find_source_in_tree(root)
        if "release" in values:
            release = values["release"]
        elif src:
            release = "patch"
            notes.append(f"release defaults to patch (version source {src})")
        else:
            release = "none"
            notes.append("release defaults to none: no version source")
    else:
        todo_sweep = True
        release = values.get("release")
        if values.get("todo_sweep") == "no":
            notes.append("todo_sweep=no override ignored, always on here")
        if release is None:
            notes.append("release unset: ask before bumping")
    return {
        "class": cls,
        "todo_sweep": todo_sweep,
        "release": release,
        "slug": slug,
        "source": f"override:{path}" if values else "default",
        "reason": "; ".join(notes),
    }


def _write_override(path, assignments):
    raw = path.read_bytes().decode("utf-8") if path.is_file() else ""
    eol = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    pending = dict(assignments)
    out = []
    for line in lines:
        key, _ = _split_line(line.strip()) if not line.strip().startswith("#") else (None, None)
        if key in pending:
            out.append(f"{key}: {pending.pop(key)}")
        elif key in assignments:
            continue  # duplicate of a key just rewritten
        else:
            out.append(line)
    out += [f"{k}: {v}" for k, v in pending.items()]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((eol.join(out) + eol).encode("utf-8"))


def cmd_set(tokens):
    repo = "."
    assignments = {}
    positional = [t for t in tokens if "=" not in t]
    if len(positional) > 1:
        raise Fail("expected at most one repo path plus key=value pairs")
    if positional:
        repo = positional[0]
    for t in tokens:
        if "=" in t:
            key, _, value = t.partition("=")
            _check_pair(key.strip(), value.strip(), "set")
            assignments[key.strip()] = value.strip()
    if not assignments:
        raise Fail("no key=value given")

    cls, slug, root, why = classify(repo)
    if cls == "unknown":
        if slug is None:
            raise Fail("no resolvable origin remote: cannot place an override for this repo")
        if "client list" in why:
            raise Fail(f"{why}: cannot place an override until the client list is readable")
        owner = slug.split("/")[0]
        raise Fail(f"unlisted repo under client owner {owner}: add {slug} to refs/client-repos.txt "
                   "if it is a client repo")
    if cls == "client" and assignments.get("todo_sweep") == "no":
        raise Fail("client repos always run the todo sweep: todo_sweep=no refused")
    path = override_path(cls, slug, root)
    _write_override(path, assignments)
    return {"path": str(path), "class": cls}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ship-config.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_get = sub.add_parser("get")
    p_get.add_argument("repo", nargs="?", default=".")
    p_set = sub.add_parser("set")
    p_set.add_argument("tokens", nargs="*")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        if e.code not in (0, None):
            print(json.dumps({"error": "bad arguments"}))
            return 2
        raise
    try:
        out = cmd_get(args.repo) if args.cmd == "get" else cmd_set(args.tokens)
    except Fail as e:
        print(json.dumps({"error": e.message}))
        return e.code
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
