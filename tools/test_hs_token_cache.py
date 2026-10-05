"""Self-test for the HubStaff access-token cache in
skills/clockify-reconciliator/scripts/hs_get_token.ps1 (todo 997).

Run directly: python tools/test_hs_token_cache.py
Exits 0 on all-pass, 1 on any failure.

Never calls HubStaff and never reads the real refresh token: every case
points -EnvPath at a path that does not exist, so if the cache logic ever
fails to short-circuit, the script hits "env file not found" rather than a
live network call. A fake, scratch cache file under $env:TEMP (never the real
%LOCALAPPDATA%\\claude-clockify\\ path) stands in for a real access token.
"""

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
import _testlib  # noqa: E402

SCRIPT = ROOT / "skills" / "clockify-reconciliator" / "scripts" / "hs_get_token.ps1"
TIMEOUT_SECONDS = 60
MISSING_ENV_PATH = str(Path(tempfile.gettempdir()) / "hs-token-cache-test-no-such-env.ignored")
FAKE_TOKEN = "fake-cached-access-token-xyz"


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def write_cache(path: Path, access_token: str, expires_at: datetime) -> None:
    path.write_text(json.dumps({"access_token": access_token, "expires_at": iso(expires_at)}), encoding="utf-8")


def run_script(cache_path: Path, env_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
         "-EnvPath", env_path, "-CachePath", str(cache_path)],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def main() -> int:
    fails = []

    def check(ok: bool, label: str) -> None:
        if not _testlib.report(ok, label):
            fails.append(label)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        now = datetime.now(timezone.utc)

        # Case 1: a valid, not-yet-expired cache - the script must print the cached token
        # and never reach the "env file not found" error, since it should never touch
        # -EnvPath at all when the cache is fresh.
        fresh_cache = tmp_dir / "fresh.json"
        write_cache(fresh_cache, FAKE_TOKEN, now + timedelta(hours=1))
        r1 = run_script(fresh_cache, MISSING_ENV_PATH)
        check(r1.returncode == 0, f"fresh cache: script exits 0 (stderr: {r1.stderr[:300]})")
        check(r1.stdout.strip() == FAKE_TOKEN, f"fresh cache: stdout is the cached token (got {r1.stdout!r})")
        check("env file not found" not in r1.stderr, "fresh cache: never falls through to the env-file path")

        # Case 2: an expired cache - the script must NOT reuse the stale token. Proven without
        # a network call: it should fall through to the real exchange path and fail there
        # because -EnvPath doesn't exist, not silently succeed with the stale value.
        expired_cache = tmp_dir / "expired.json"
        write_cache(expired_cache, "stale-token-should-not-be-used", now - timedelta(hours=1))
        r2 = run_script(expired_cache, MISSING_ENV_PATH)
        check(r2.returncode != 0, "expired cache: script does not exit 0")
        check("env file not found" in r2.stderr, "expired cache: falls through to the real exchange path")
        check("stale-token-should-not-be-used" not in r2.stdout, "expired cache: never prints the stale token")

        # Case 3: no cache file at all - same fall-through as an expired cache.
        missing_cache = tmp_dir / "does-not-exist.json"
        r3 = run_script(missing_cache, MISSING_ENV_PATH)
        check(r3.returncode != 0, "missing cache: script does not exit 0")
        check("env file not found" in r3.stderr, "missing cache: falls through to the real exchange path")

        # Case 4: a malformed (non-JSON) cache file - must degrade to the fall-through path,
        # not crash with an unhandled parse error.
        malformed_cache = tmp_dir / "malformed.json"
        malformed_cache.write_text("not valid json {{{", encoding="utf-8")
        r4 = run_script(malformed_cache, MISSING_ENV_PATH)
        check(r4.returncode != 0, "malformed cache: script does not exit 0")
        check("env file not found" in r4.stderr, "malformed cache: degrades to the real exchange path, not a crash")

    if fails:
        print(f"\nFAILURES: {fails}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
