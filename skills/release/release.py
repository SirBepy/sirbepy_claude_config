"""Version mechanics for the /release flow: truth-source lookup, tauri_kit sync, patch bump,
and "is a bump already pending in the push range".

Every subcommand prints exactly one JSON object; a non-zero exit always prints {"error": ...}.
  source [repo]                    {"source", "version"}
  kit-sync [repo]                  {"changed", "old", "new"} | {"changed": false, "reason"}
  bump [repo]                      {"version", "build", "label", "files"}   (never commits)
  version-diff [repo] [--no-fetch] {"pending", "base_version", "head_version", "base_ref", "reason"}
Exit codes: 2 = refused / bad input, 3 = network (fetch or submodule update failed).

Stdlib only; runs under `python -I`.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

GIT_TIMEOUT_SECONDS = 60
NET_TIMEOUT_SECONDS = 180
# Precedence matters: package.json outranks the Rust crate, which outranks pubspec.
SOURCE_FILES = ("package.json", "src-tauri/Cargo.toml", "pubspec.yaml")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# A changed line in a bumped file must be the version line and nothing else.
PURE_LINE = {
    "json": re.compile(r'^\s*"version"\s*:\s*"[^"]*"\s*,?\s*$'),
    "toml": re.compile(r'^version\s*=\s*"[^"]*"\s*(#.*)?$'),
    "pubspec": re.compile(r"^version:\s*\S+\s*(#.*)?$"),
}


class Fail(Exception):
    def __init__(self, message, code=2):
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------- git plumbing

def git(root, *args, timeout=GIT_TIMEOUT_SECONDS):
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(args, 128, "", f"git could not run: {e!r}")


def repo_root(repo, need_git=True):
    path = Path(repo or ".").resolve()
    proc = git(path, "rev-parse", "--show-toplevel")
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip())
    if need_git:
        raise Fail(f"not a git repository: {path}")
    return path


def tracked_among(root, rels):
    if not rels:
        return set()
    proc = git(root, "ls-files", "-z", "--", *rels)
    return {p for p in proc.stdout.split("\0") if p}


# ---------------------------------------------------------------- JSON spans
# Bumping edits the version string in place by character span, because a json.dump round trip
# would reformat the whole file and bury the one-line change in the diff.

_WS = re.compile(r"[\s﻿]*")
_STR = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
_ATOM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null")


class Node:
    __slots__ = ("start", "end", "kind", "kids", "value")

    def __init__(self, start, end, kind, kids=None, value=None):
        self.start, self.end, self.kind, self.kids, self.value = start, end, kind, kids, value


def parse_json_spans(text):
    def ws(i):
        return _WS.match(text, i).end()

    def val(i):
        i = ws(i)
        start = i
        c = text[i]
        if c == "{":
            kids = {}
            i = ws(i + 1)
            if text[i] == "}":
                return Node(start, i + 1, "obj", kids), i + 1
            while True:
                i = ws(i)
                m = _STR.match(text, i)
                if not m:
                    raise ValueError("object key expected")
                key = json.loads(m.group())
                i = ws(m.end())
                if text[i] != ":":
                    raise ValueError("colon expected")
                node, i = val(i + 1)
                kids[key] = node
                i = ws(i)
                if text[i] == ",":
                    i += 1
                    continue
                if text[i] == "}":
                    return Node(start, i + 1, "obj", kids), i + 1
                raise ValueError("object end expected")
        if c == "[":
            i = ws(i + 1)
            if text[i] == "]":
                return Node(start, i + 1, "arr"), i + 1
            while True:
                _, i = val(i)
                i = ws(i)
                if text[i] == ",":
                    i += 1
                    continue
                if text[i] == "]":
                    return Node(start, i + 1, "arr"), i + 1
                raise ValueError("array end expected")
        if c == '"':
            m = _STR.match(text, i)
            if not m:
                raise ValueError("bad string")
            return Node(start, m.end(), "str", value=json.loads(m.group())), m.end()
        m = _ATOM.match(text, i)
        if not m:
            raise ValueError("bad value")
        return Node(start, m.end(), "other", value=m.group()), m.end()

    try:
        root, end = val(0)
        if ws(end) != len(text):
            raise ValueError("trailing content")
    except (IndexError, ValueError):
        return None
    return root


def json_node(text, path):
    root = parse_json_spans(text)
    node = root
    for key in path:
        if node is None or node.kind != "obj" or key not in node.kids:
            return None
        node = node.kids[key]
    return node


def json_string_at(text, path):
    node = json_node(text, path)
    return node.value if node is not None and node.kind == "str" else None


def json_set_string(text, path, new):
    """Returns (new_text, old_value), or None when `path` is not a string value."""
    node = json_node(text, path)
    if node is None or node.kind != "str":
        return None
    return text[:node.start] + json.dumps(new) + text[node.end:], node.value


# ---------------------------------------------------------------- TOML / pubspec lines

_SECTION = re.compile(r"^[ \t]*\[", re.M)


def _section_bodies(text, header_re):
    """(body_start, body_end) of every section whose header line matches `header_re`."""
    for m in re.finditer(header_re, text, re.M):
        nxt = _SECTION.search(text, m.end())
        yield m.end(), (nxt.start() if nxt else len(text))


def _toml_key(text, lo, hi, key):
    m = re.compile(rf'^{key}[ \t]*=[ \t]*"([^"\r\n]*)"', re.M).search(text, lo, hi)
    return m


def cargo_package(text):
    """(name, version, version_span) of the [package] table, or None."""
    for lo, hi in _section_bodies(text, r"^\[package\][ \t]*(?:#[^\r\n]*)?\r?$"):
        v = _toml_key(text, lo, hi, "version")
        n = _toml_key(text, lo, hi, "name")
        if v:
            return (n.group(1) if n else None), v.group(1), v.span(1)
    return None


def cargo_lock_packages(text):
    """[(name, version, version_span)] for every [[package]] block."""
    out = []
    for lo, hi in _section_bodies(text, r"^\[\[package\]\][ \t]*(?:#[^\r\n]*)?\r?$"):
        v = _toml_key(text, lo, hi, "version")
        n = _toml_key(text, lo, hi, "name")
        if v and n:
            out.append((n.group(1), v.group(1), v.span(1)))
    return out


_PUBSPEC = re.compile(r"^version:[ \t]*([0-9]+\.[0-9]+\.[0-9]+)(?:\+([0-9]+))?[ \t]*(?:#[^\r\n]*)?(?=\r?$)", re.M)


def pubspec_version(text):
    """(version, build_or_None, span_of_version_and_build) or None."""
    m = _PUBSPEC.search(text)
    if not m:
        return None
    end = m.end(2) if m.group(2) is not None else m.end(1)
    return m.group(1), m.group(2), (m.start(1), end)


# ---------------------------------------------------------------- truth source

def parse_source_version(rel, text):
    if rel == "package.json":
        return json_string_at(text, ("version",))
    if rel == "src-tauri/Cargo.toml":
        pkg = cargo_package(text)
        return pkg[1] if pkg else None
    if rel == "pubspec.yaml":
        pv = pubspec_version(text)
        return pv[0] if pv else None
    return None


def find_source(get_text):
    """First SOURCE_FILES entry yielding a version: (relpath, version), else (None, None)."""
    for rel in SOURCE_FILES:
        text = get_text(rel)
        if text is None:
            continue
        ver = parse_source_version(rel, text)
        if ver:
            return rel, ver
    return None, None


def read_working(root, rel):
    try:
        return (Path(root) / rel).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def find_source_in_tree(root):
    return find_source(lambda rel: read_working(root, rel))


def git_show(root, rev, rel):
    proc = git(root, "show", f"{rev}:{rel}")
    return proc.stdout if proc.returncode == 0 else None


def cmd_source(repo):
    root = repo_root(repo, need_git=False)
    rel, ver = find_source_in_tree(root)
    return {"source": rel, "version": ver}


# ---------------------------------------------------------------- kit-sync

def _kit_status(root):
    """(prefix, checked-out sha) from `git submodule status`; prefix is ' ', '+', '-' or 'U'.
    None when vendor/tauri_kit is not a submodule."""
    proc = git(root, "submodule", "status", "--", "vendor/tauri_kit")
    line = proc.stdout.rstrip()
    if proc.returncode != 0 or not line.strip():
        return None
    return line[0], line[1:].split()[0][:7]


def _kit_gitlink(root):
    """The sha committed at HEAD for vendor/tauri_kit, or None when HEAD has no such gitlink."""
    proc = git(root, "ls-tree", "HEAD", "--", "vendor/tauri_kit")
    fields = proc.stdout.split()
    if proc.returncode != 0 or len(fields) < 3 or fields[0] != "160000":
        return None
    return fields[2][:7]


def cmd_kit_sync(repo):
    root = repo_root(repo)
    status = _kit_status(root)
    if status is None:
        return {"changed": False, "reason": "no vendor/tauri_kit"}
    prefix, checked_out = status
    # `old` is the committed gitlink, not the checkout: a checkout already ahead of HEAD (status '+')
    # must still report changed, or its uncommitted gitlink never gets a commit.
    old = _kit_gitlink(root) or checked_out
    args = ["submodule", "update", "--init", "--remote"] if prefix == "-" else ["submodule", "update", "--remote"]
    proc = git(root, *args, "vendor/tauri_kit", timeout=NET_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        raise Fail(f"submodule update failed: {proc.stderr.strip()}", 3)
    after = _kit_status(root)
    new = after[1] if after else checked_out
    return {"changed": new != old, "old": old, "new": new}


# ---------------------------------------------------------------- bump

class FileEdit:
    def __init__(self, rel, kind, original, new_bytes, changes):
        self.rel, self.kind, self.original, self.new_bytes, self.changes = rel, kind, original, new_bytes, changes


def _json_paths(rel, text):
    paths = []
    for path in (("version",), ("package", "version")):
        if path[0] == "package" and Path(rel).name != "tauri.conf.json":
            continue
        val = json_string_at(text, path)
        # A root-level "version" that is not x.y.z (a schema or API version, say) is not ours.
        if val is not None and SEMVER.match(val):
            paths.append(path)
    return paths


def _read_build(root):
    """An existing build field, reported in the VERSION label but never changed. tauri.conf.json
    carries `build` as a config object, so only a scalar counts."""
    for rel in ("package.json", "src-tauri/tauri.conf.json", "tauri.conf.json"):
        text = read_working(root, rel)
        node = json_node(text, ("build",)) if text is not None else None
        if node is None:
            continue
        if node.kind == "str" and node.value:
            return node.value
        if node.kind == "other" and re.fullmatch(r"\d+", node.value):
            return node.value
    return None


def _plan_edits(root, tracked, new_version):
    """Every version location that exists and is git-tracked, with its rewritten bytes."""
    edits = []
    build = None
    root = Path(root)

    def load(rel):
        if rel not in tracked:
            return None
        text = read_working(root, rel)
        return text

    def add(rel, kind, text, new_text, changes):
        if new_text != text:
            edits.append(FileEdit(rel, kind, text.encode("utf-8"), new_text.encode("utf-8"), changes))

    json_rels = sorted(
        p.name for p in root.glob("*.json")
        if p.is_file() and p.name != "package-lock.json" and p.name in tracked
    )
    if "src-tauri/tauri.conf.json" in tracked:
        json_rels.append("src-tauri/tauri.conf.json")
    for rel in json_rels:
        text = load(rel)
        if text is None:
            continue
        new_text, changes = text, 0
        for path in _json_paths(rel, text):
            new_text, _ = json_set_string(new_text, path, new_version)
            changes += 1
        # Drifted-ahead files already at the target count zero edits, so changes is a ceiling here.
        add(rel, "json", text, new_text, changes)

    lock = load("package-lock.json")
    if lock is not None:
        new_text, changes = lock, 0
        for path in (("version",), ("packages", "", "version")):
            hit = json_set_string(new_text, path, new_version)
            if hit:
                new_text, changes = hit[0], changes + 1
        add("package-lock.json", "json", lock, new_text, changes)

    cargo_rel = "src-tauri/Cargo.toml"
    cargo = load(cargo_rel)
    if cargo is not None and cargo_package(cargo):
        name, old_ver, (a, b) = cargo_package(cargo)
        add(cargo_rel, "toml", cargo, cargo[:a] + new_version + cargo[b:], 1)
        for lock_rel in _cargo_lock_candidates(cargo_rel):
            if not (root / lock_rel).is_file():
                continue
            # The nearest lock is the workspace's lock; an untracked one is left alone rather
            # than falling through to a farther ancestor's unrelated lock.
            locktext = load(lock_rel)
            if locktext is not None and name:
                pkgs = [p for p in cargo_lock_packages(locktext) if p[0] == name]
                exact = [p for p in pkgs if p[1] == old_ver]
                pick = exact[0] if len(exact) == 1 else (pkgs[0] if len(pkgs) == 1 else None)
                if pick is None:
                    raise Fail(f"{lock_rel}: cannot pick a unique [[package]] block for '{name}'")
                a, b = pick[2]
                add(lock_rel, "toml", locktext, locktext[:a] + new_version + locktext[b:], 1)
            break

    pub = load("pubspec.yaml")
    if pub is not None and pubspec_version(pub):
        _, old_build, (a, b) = pubspec_version(pub)
        if old_build is not None:
            build = str(int(old_build) + 1)
            replacement = f"{new_version}+{build}"
        else:
            replacement = new_version
        add("pubspec.yaml", "pubspec", pub, pub[:a] + replacement + pub[b:], 1)

    return edits, build


def _cargo_lock_candidates(cargo_rel):
    parent = Path(cargo_rel).parent
    out = [(parent / "Cargo.lock").as_posix()]
    while str(parent) not in (".", ""):
        parent = parent.parent
        out.append((parent / "Cargo.lock").as_posix())
    return out


def _parse_diff(diff_text):
    """{path: ([removed lines], [added lines])} from a --unified=0 diff."""
    files, cur, in_hunk = {}, None, False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", line)
            cur = m.group(2) if m else None
            if cur is not None:
                files[cur] = ([], [])
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and cur is not None:
            if line.startswith("-"):
                files[cur][0].append(line[1:])
            elif line.startswith("+"):
                files[cur][1].append(line[1:])
    return files


def _restore(root, edits):
    for e in edits:
        (Path(root) / e.rel).write_bytes(e.original)


def cmd_bump(repo):
    root = repo_root(repo)
    candidates = ["package.json", "package-lock.json", "src-tauri/tauri.conf.json", "src-tauri/Cargo.toml",
                  "pubspec.yaml"]
    candidates += [p.name for p in root.glob("*.json") if p.is_file()]
    candidates += _cargo_lock_candidates("src-tauri/Cargo.toml")
    tracked = tracked_among(root, sorted(set(candidates)))

    src_rel, old_version = find_source_in_tree(root)
    if src_rel is None:
        raise Fail("no version source (package.json, src-tauri/Cargo.toml or pubspec.yaml with a version)")
    if src_rel not in tracked:
        raise Fail(f"{src_rel} is not tracked by git")
    m = SEMVER.match(old_version)
    if not m:
        raise Fail(f"{src_rel}: version '{old_version}' is not x.y.z, bump it by hand")
    new_version = f"{m.group(1)}.{m.group(2)}.{int(m.group(3)) + 1}"

    edits, build = _plan_edits(root, tracked, new_version)
    if not edits:
        raise Fail("nothing to edit")

    rels = [e.rel for e in edits]
    # A peer's uncommitted edit in a version file would ride into the VERSION commit.
    status = git(root, "status", "--porcelain", "--", *rels).stdout.strip()
    if status:
        raise Fail("refusing to bump, version files already have uncommitted changes:\n" + status)

    try:
        for e in edits:
            (root / e.rel).write_bytes(e.new_bytes)
        diff = git(root, "diff", "--unified=0", "--no-color", "--no-ext-diff", "--", *rels)
        parsed = _parse_diff(diff.stdout)
        problem = None
        for e in edits:
            removed, added = parsed.get(e.rel, ([], []))
            if not removed or len(removed) != len(added) or len(removed) > e.changes:
                problem = f"{e.rel}: unexpected diff shape ({len(removed)} removed, {len(added)} added)"
            elif not all(PURE_LINE[e.kind].match(ln) for ln in removed + added):
                problem = f"{e.rel}: a changed line is not a version line"
            if problem:
                break
        if problem is None and set(parsed) - set(rels):
            problem = "diff touches unexpected files: " + ", ".join(sorted(set(parsed) - set(rels)))
    except BaseException:
        _restore(root, edits)
        raise
    if problem:
        _restore(root, edits)
        raise Fail(f"bump aborted, files restored: {problem}")

    if build is None:
        build = _read_build(root)
    label = new_version + (f"+{build}" if build else "")
    return {"version": new_version, "build": build, "label": label, "files": rels}


# ---------------------------------------------------------------- version-diff

def _base_ref(root):
    up = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if up.returncode == 0 and up.stdout.strip():
        return up.stdout.strip(), "@{u}"
    sym = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    candidates = []
    if sym.returncode == 0 and sym.stdout.strip():
        candidates.append(sym.stdout.strip())
    candidates += ["origin/main", "origin/master"]
    for ref in candidates:
        if git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").returncode == 0:
            return ref, ref
    return None, None


def cmd_version_diff(repo, fetch=True):
    root = repo_root(repo)
    if fetch:
        proc = git(root, "fetch", "origin", timeout=NET_TIMEOUT_SECONDS)
        if proc.returncode != 0:
            raise Fail(f"fetch failed: {proc.stderr.strip()}", 3)
    name, rev = _base_ref(root)
    if name is None:
        raise Fail("no upstream and no origin/HEAD, origin/main or origin/master to compare against")

    # Compare against the merge-base, never the upstream tip: a teammate's newer bump already on
    # upstream differs from our HEAD too, and must not read as a bump we still have to push.
    mb = git(root, "merge-base", "HEAD", rev)
    if mb.returncode != 0 or not mb.stdout.strip():
        raise Fail(f"no merge-base between HEAD and {name} (unrelated history)")
    base = mb.stdout.strip()

    head_rel, head_ver = find_source(lambda rel: git_show(root, "HEAD", rel))
    result = {"pending": False, "base_version": None, "head_version": head_ver, "base_ref": name}
    if head_rel is None:
        result["reason"] = "no version source at HEAD"
        return result
    base_text = git_show(root, base, head_rel)
    if base_text is None:
        result["reason"] = f"{head_rel} did not exist at the merge-base"
        return result
    base_ver = parse_source_version(head_rel, base_text)
    result["base_version"] = base_ver
    if base_ver is None:
        result["reason"] = f"{head_rel} had no version at the merge-base"
        return result
    result["pending"] = base_ver != head_ver
    result["reason"] = (
        f"{head_rel} went {base_ver} -> {head_ver} since the merge-base with {name}"
        if result["pending"] else f"{head_rel} is {head_ver} at both HEAD and the merge-base with {name}"
    )
    return result


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(prog="release.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("source", "kit-sync", "bump", "version-diff"):
        p = sub.add_parser(name)
        p.add_argument("repo", nargs="?", default=".")
        if name == "version-diff":
            p.add_argument("--no-fetch", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        if e.code not in (0, None):
            print(json.dumps({"error": "bad arguments"}))
            return 2
        raise
    try:
        if args.cmd == "source":
            out = cmd_source(args.repo)
        elif args.cmd == "kit-sync":
            out = cmd_kit_sync(args.repo)
        elif args.cmd == "bump":
            out = cmd_bump(args.repo)
        else:
            out = cmd_version_diff(args.repo, fetch=not args.no_fetch)
    except Fail as e:
        print(json.dumps({"error": e.message}))
        return e.code
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
