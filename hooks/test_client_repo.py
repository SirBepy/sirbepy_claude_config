"""Self-test for _client_repo.py.

Run directly: python hooks/test_client_repo.py
End-to-end cases build throwaway git repos in a temp dir and point the client
list there, so the real refs/client-repos.txt is never read.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
lib = _testlib.load_module("_client_repo", _HOOKS_DIR / "_client_repo.py")

fails = []

# --- origin_slug: every remote URL shape the listed repos actually use ---

SLUG_CASES = [
    ("https://github.com/Revaire-Inc/revaire-mobile.git", "revaire-inc/revaire-mobile", "https with .git"),
    ("git@github-work:zirtue-corp/zng-admin.git", "zirtue-corp/zng-admin", "scp-style host alias"),
    ("ssh://git@github.com/zirtue-corp/zng-api", "zirtue-corp/zng-api", "ssh url, no .git"),
    ("https://github.com/SirBepy/foo/", "sirbepy/foo", "trailing slash"),
    ("", None, "empty url"),
    ("nonsense", None, "single segment"),
]


def check_slug(case) -> bool:
    url, expected, label = case
    got = lib.origin_slug(url)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(SLUG_CASES, check_slug)

# --- client_slug against real temp repos ---


def make_repo(root: Path, name: str, origin: str) -> Path:
    repo = root / name
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", origin], check=True, capture_output=True)
    return repo


def expect(label: str, got, expected) -> None:
    global fails
    ok = got == expected
    fails += [] if _testlib.report(ok, f"{label} (expected {expected}, got {got})") else [label]


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    client_list = tmpdir / "client-repos.txt"
    client_list.write_text("# comment line\nZirtue-Corp/ZNG-App\n", encoding="utf-8")
    lib.CLIENT_LIST_PATH = client_list

    client = make_repo(tmpdir, "zng-app-followup", "git@github-work:zirtue-corp/zng-app.git")
    personal = make_repo(tmpdir, "mine", "https://github.com/SirBepy/mine.git")

    expect("listed origin is a client repo, matched case-insensitively", lib.client_slug(client), "zirtue-corp/zng-app")
    expect("unlisted origin is personal", lib.client_slug(personal), None)

    client_list.unlink()
    expect("a missing client list makes every repo personal", lib.client_slug(client), None)

sys.exit(_testlib.summarize(fails, style="count"))
