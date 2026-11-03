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

    # --- is-client --list: a second list file answered by the same slug algorithm ---
    other_list = tmpdir / "local-only-tests.txt"
    other_list.write_text("# comment\n  SirBepy/Mine  \n", encoding="utf-8")

    def cli(path: Path, *extra: str) -> str:
        proc = subprocess.run(
            [sys.executable, "-I", str(_HOOKS_DIR / "_client_repo.py"), "is-client", str(path), *extra],
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or f"rc={proc.returncode} {proc.stderr.strip()[-80:]}"

    expect("--list: origin on the given list is reported", cli(personal, "--list", str(other_list)), "client")
    expect("--list: origin absent from the given list is not", cli(client, "--list", str(other_list)), "personal")
    expect("--list: a missing list file matches nothing", cli(personal, "--list", str(tmpdir / "nope.txt")), "personal")
    expect("client_slug(list_path=...) reads that list", lib.client_slug(personal, other_list), "sirbepy/mine")
    # Dangerous shape: without --list the real client list still decides, so a repo on the
    # custom list only does not become a client repo.
    expect("no --list: default list unchanged by the option existing", lib.client_slug(personal), None)

sys.exit(_testlib.summarize(fails, style="count"))
