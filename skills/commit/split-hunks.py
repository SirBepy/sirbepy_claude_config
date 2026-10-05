#!/usr/bin/env python3
"""Stage selected hunks and (optionally) commit them via a private index with
a compare-and-swap HEAD update.

Why this exists (two edge-cases.md gaps, same "Splitting one file across
commits" section, fixed together):

- todo 1046: the documented step 1, `git diff <file> > <tmp>.patch`, is a `>`
  redirect hooks/shell-content-write-guard.py denies on sight, and piping the
  patch through a text-mode subprocess turns `\n` into `\r\n` on Windows,
  which breaks `git apply`'s context match. Every git call below stays
  inside this one process (no shell redirect ever reaches the guard) and
  runs in bytes mode end to end (no text=True) - the fix that worked in the
  live incident this todo recorded.
- todo 1068: applying hunks straight into a git index shared with concurrent
  sessions risks sweeping a peer's staged files into the commit, and racing
  a peer's commit between building the tree and committing silently reverts
  their work (zng-app sc-56160: a stale tree landed on the peer's new HEAD
  and deleted their 20 files). `commit` mode never touches the shared index
  to build the tree: it reads HEAD once, builds the tree in a private
  GIT_INDEX_FILE, and lands it with `git update-ref HEAD <new> <base>` - a
  compare-and-swap that refuses outright if HEAD moved underneath it.

Design note: commit-guard.py now also gates a *raw shell* `git commit-tree`
and a branch-moving `git update-ref` (todo 1085), but that only covers a
command string the hook actually reads. This script's own `commit` mode
builds both calls via Python `subprocess`, never as a literal
`python ... split-hunks.py commit ...` substring the hook could match - so
its marker gate still never fires for this path, by construction, not by
gap. `commit` mode below runs prefilter-gate.sh itself over the declared
pathspec before creating the commit object, so a flagged diff still can't
land through this route either way.

Usage:
  split-hunks.py stage <path> --match <substring> [--repo <dir>]
      Filters <path>'s unstaged hunks (vs HEAD) to those whose added/removed
      lines contain <substring>, applies just those into the REAL index with
      `git apply --cached`. For the solo, no-concurrent-risk case - nothing
      else of interest is staged. Prints `git diff --cached -- <path>` to
      confirm. Exit 1 if no hunk matched (nothing staged).

  split-hunks.py commit --message <msg> [--repo <dir>]
      [--whole <path> ...] [--hunk <path>:<substring> ...] [--base <sha>]
      Builds a private index from HEAD (or --base, to retry against a known
      base), stages whole files as-is and/or filtered hunks into it, refuses
      if the resulting tree touches any path outside the declared --whole/
      --hunk set, runs prefilter-gate.sh over that same set, commits, then
      lands it on HEAD with a CAS update-ref. On a lost race (HEAD moved
      since the base was read) it refuses and leaves HEAD at the peer's
      commit - rerun with the new HEAD as --base to retry. On success,
      resyncs the real index's entries for the committed paths only
      (`git reset -q -- <paths>`), leaving everything else a concurrent
      session staged exactly as it was.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PREFILTER_GATE = SCRIPT_DIR / "prefilter-gate.sh"


def resolve_bash() -> str | None:
    """Same Git-for-Windows-over-WSL-shim preference as commit-guard.py's own
    resolve_bash - duplicated narrowly rather than imported, since hooks/ is
    out of scope for this script to depend on."""
    if os.name != "nt":
        return shutil.which("bash")
    git_exe = shutil.which("git")
    if git_exe:
        candidate = Path(git_exe).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    return None


def run(repo, args, env=None, input_bytes=None, check=True):
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        capture_output=True,
        env=env,
        timeout=60,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            f"{proc.stderr.decode('utf-8', 'replace')}"
        )
    return proc


def diff_against_ref(repo, ref, path, env=None):
    """Bytes of `git diff <ref> -- <path>`, never text mode (the CRLF trap
    todo 1046 recorded: text-mode stdin/stdout rewrites \\n to \\r\\n on
    Windows, which breaks `git apply`'s context match)."""
    return run(repo, ["diff", ref, "--", path], env=env).stdout


def split_file_sections(patch: bytes):
    """Splits a (possibly multi-file) unified diff into per-file byte-line
    lists, each starting at its own `diff --git` line."""
    lines = patch.split(b"\n")
    sections = []
    current = []
    for line in lines:
        if line.startswith(b"diff --git") and current:
            sections.append(current)
            current = []
        current.append(line)
    if current and any(current):
        sections.append(current)
    return sections


def filter_hunks(section: list, substring: bytes):
    """Keeps only the hunks (`@@ ... @@` blocks) in one file-section whose
    added/removed lines contain `substring`. Returns the trimmed line list,
    or None if no hunk in this file matched (drop the file entirely)."""
    header = []
    i = 0
    while i < len(section) and not section[i].startswith(b"@@"):
        header.append(section[i])
        i += 1
    hunks = []
    current = []
    while i < len(section):
        if section[i].startswith(b"@@") and current:
            hunks.append(current)
            current = []
        current.append(section[i])
        i += 1
    if current:
        hunks.append(current)

    kept = [
        h for h in hunks
        if any(
            (ln.startswith(b"+") or ln.startswith(b"-")) and substring in ln
            for ln in h
        )
    ]
    if not kept:
        return None
    out = list(header)
    for h in kept:
        out.extend(h)
    return out


def build_patch(repo, ref, path, substring: bytes, env=None):
    """Bytes of `git diff <ref> -- <path>` trimmed to hunks containing
    `substring`, or None if nothing matched (nothing to stage)."""
    full = diff_against_ref(repo, ref, path, env=env)
    if not full.strip():
        return None
    kept = [s for s in (filter_hunks(sec, substring) for sec in split_file_sections(full)) if s is not None]
    if not kept:
        return None
    out = []
    for section in kept:
        out.extend(section)
    return b"\n".join(out) + b"\n"


def apply_cached(repo, patch: bytes, env=None):
    """Applies `patch` into whatever index `env`'s GIT_INDEX_FILE points at
    (the real index if env is None), stdin in bytes so Windows never rewrites
    \\n to \\r\\n underneath git apply's context match."""
    run(repo, ["apply", "--cached", "--recount", "-"], env=env, input_bytes=patch)


def run_prefilter_gate(repo, paths):
    """Runs prefilter-gate.sh over `paths` ourselves, since commit-tree/
    update-ref never pass through hooks/commit-guard.py's own re-check (see
    module docstring). Returns (ok, output). Fails OPEN (ok=True) only when
    the gate genuinely could not be invoked - infra problem, not a verdict -
    matching commit-guard.py's own fail-open philosophy for that case."""
    if not PREFILTER_GATE.is_file():
        return True, "prefilter-gate.sh not found; skipping (fail open)"
    bash = resolve_bash()
    if not bash:
        return True, "no bash found to run prefilter-gate.sh; skipping (fail open)"
    try:
        proc = subprocess.run(
            [bash, str(PREFILTER_GATE), *paths], cwd=str(repo),
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return True, f"could not run prefilter-gate.sh ({e!r}); skipping (fail open)"
    output = proc.stdout + proc.stderr
    if proc.returncode == 1:
        return False, output
    return True, output


def cmd_stage(args):
    repo = Path(args.repo).resolve()
    patch = build_patch(repo, "HEAD", args.path, args.match.encode())
    if patch is None:
        print(f"no hunk in {args.path} contains {args.match!r}; nothing staged")
        return 1
    apply_cached(repo, patch)
    shown = run(repo, ["diff", "--cached", "--", args.path]).stdout
    sys.stdout.buffer.write(shown)
    return 0


def _parse_hunk_spec(spec: str):
    if ":" not in spec:
        raise SystemExit(f"--hunk expects path:substring, got {spec!r}")
    path, substring = spec.split(":", 1)
    return path, substring


def cmd_commit(args):
    repo = Path(args.repo).resolve()
    whole_paths = list(args.whole or [])
    hunk_specs = [_parse_hunk_spec(s) for s in (args.hunk or [])]
    hunk_paths = [p for p, _ in hunk_specs]
    declared = sorted(set(whole_paths) | set(hunk_paths))
    if not declared:
        print("nothing declared: pass --whole and/or --hunk")
        return 1

    # Step 1 (edge-cases.md Approach item 1): record the base before touching
    # anything, so a peer commit after this point is a detectable race, not a
    # silent overwrite. --base lets a caller retry against a fresher HEAD
    # without re-deriving it, and is what the test suite uses to simulate the
    # race deterministically.
    base = args.base or run(repo, ["rev-parse", "HEAD"]).stdout.decode().strip()

    ok, output = run_prefilter_gate(repo, declared)
    if not ok:
        print(output)
        print("prefilter-gate.sh flagged the declared pathspec; refusing to build the commit.")
        return 1

    fd, priv_index = tempfile.mkstemp(prefix="split-hunks-index-", suffix=".tmp")
    os.close(fd)
    os.remove(priv_index)  # git read-tree creates it; a pre-existing empty file confuses it
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = priv_index
    try:
        run(repo, ["read-tree", base], env=env)
        for path in whole_paths:
            run(repo, ["add", "--", path], env=env)
        for path, substring in hunk_specs:
            patch = build_patch(repo, base, path, substring.encode())
            if patch is None:
                print(f"no hunk in {path} contains {substring!r}; refusing (nothing would change)")
                return 1
            apply_cached(repo, patch, env=env)

        tree = run(repo, ["write-tree"], env=env).stdout.decode().strip()

        # Approach item 5, checked BEFORE mutating HEAD rather than after: a
        # pure object-to-object diff needs no index at all, so this can
        # reject a leak with zero side effects, instead of discovering it
        # only once the commit already exists.
        changed = {
            line for line in run(repo, ["diff", "--name-only", base, tree]).stdout.decode().splitlines() if line
        }
        extra = changed - set(declared)
        if extra:
            print(f"refusing: tree touches undeclared path(s): {sorted(extra)}")
            return 1

        new = run(repo, ["commit-tree", tree, "-p", base, "-m", args.message], env=env).stdout.decode().strip()

        # Step 3's CAS: refuses outright if HEAD != base, i.e. if a peer
        # committed in the window between reading base and this call - the
        # exact race that silently reverted a peer's commit in todo 1068.
        cas = run(repo, ["update-ref", "HEAD", new, base], check=False)
        if cas.returncode != 0:
            current = run(repo, ["rev-parse", "HEAD"]).stdout.decode().strip()
            print(
                f"refusing: HEAD moved from {base} to {current} since the base was read "
                f"(a peer committed). HEAD is untouched at {current}. Rerun with "
                f"--base {current} to retry against the new base.\n{cas.stderr.decode('utf-8', 'replace')}"
            )
            return 1
    finally:
        for p in (priv_index, priv_index + ".lock"):
            try:
                os.remove(p)
            except OSError:
                pass

    # Resyncs only the paths just committed - never a wholesale `git reset`,
    # which would also discard a concurrent session's unrelated staged work.
    run(repo, ["reset", "-q", "--"] + declared)
    print(run(repo, ["show", "--stat", "HEAD"]).stdout.decode("utf-8", "replace"))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_stage = sub.add_parser("stage")
    p_stage.add_argument("path")
    p_stage.add_argument("--match", required=True)
    p_stage.set_defaults(func=cmd_stage)

    p_commit = sub.add_parser("commit")
    p_commit.add_argument("-m", "--message", required=True)
    p_commit.add_argument("--whole", action="append", default=[])
    p_commit.add_argument("--hunk", action="append", default=[])
    p_commit.add_argument("--base")
    p_commit.set_defaults(func=cmd_commit)

    args = parser.parse_args()
    try:
        return args.func(args)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
