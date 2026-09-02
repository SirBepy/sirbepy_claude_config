"""Self-test for shortcut-mutation-guard.py.

Run directly: python hooks/test_shortcut_mutation_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers the three pure decisions this guard makes (claim-bearing, Release-only
bypass, story-id extraction) plus load_env_file's BOM handling, which pins the
2026-08-18 bug where a BOM in ~/.claude/.env made the owner check fail closed
on every mutation. The network-bound owner check (fetch_story) is never hit.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import _testlib
from _hooklib import oldest_fresh_marker

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "shortcut-mutation-guard.py"
)

# --- is_claim_bearing: a rewrite of ticket text is a claim, a bare state/owner move is not ---

CLAIM_CASES = [
    ("Bash", {"name": "New title"}, True, "name key is a claim"),
    ("Bash", {"description": "New body"}, True, "description key is a claim"),
    ("Bash", {"text": "a comment body"}, True, "text key is a claim"),
    ("mcp__shortcut__stories-create-comment", {}, True, "any create-comment tool is a claim"),
    ("Bash", {"workflow_state_id": "500"}, False, "bare workflow_state_id move asserts nothing"),
    ("Bash", {"owner_ids": ["abc"]}, False, "bare owner_ids move asserts nothing"),
    ("Bash", {"name": ""}, False, "empty string name is falsy, not a claim"),
]


def check_claim(case) -> bool:
    tool_name, tool_input, expected, label = case
    got = guard.is_claim_bearing(tool_name, tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected claim_bearing={expected}, got {got})")
    return ok


fails = _testlib.run_cases(CLAIM_CASES, check_claim)

# --- is_release_only_mutation: only the Release custom field, nothing else ---

RELEASE_CASES = [
    (
        {"storyPublicId": 1, "custom_fields": [{"field_id": guard.RELEASE_FIELD_ID, "value": "1.2.3"}]},
        True,
        "lone Release field write",
    ),
    (
        {"storyPublicId": 1, "custom_fields": [{"field_id": guard.RELEASE_FIELD_ID}], "name": "x"},
        False,
        "Release field plus another top-level key",
    ),
    (
        {"storyPublicId": 1, "custom_fields": [{"field_id": "some-other-field-uuid"}]},
        False,
        "a different custom field is not Release",
    ),
    (
        {"storyPublicId": 1, "custom_fields": [{"field_id": guard.RELEASE_FIELD_ID}, {"field_id": "other-uuid"}]},
        False,
        "Release plus another custom field",
    ),
    ({"storyPublicId": 1}, False, "no custom_fields at all"),
]


def check_release(case) -> bool:
    tool_input, expected, label = case
    got = guard.is_release_only_mutation(tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected release_only={expected}, got {got})")
    return ok


fails += _testlib.run_cases(RELEASE_CASES, check_release)

# --- extract_story_ids: every recognized key, plus a fail-closed deny on a non-int ---

STORY_ID_CASES = [({key: 42}, [42], f"{key} extracted") for key in guard.STORY_ID_KEYS]


def check_story_ids(case) -> bool:
    tool_input, expected, label = case
    got = guard.extract_story_ids(tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(STORY_ID_CASES, check_story_ids)

try:
    guard.extract_story_ids({"storyId": "not-a-number"})
    deny_ok = False
except SystemExit as e:
    deny_ok = e.code == 2
if not _testlib.report(deny_ok, "non-int story id denies fail-closed"):
    fails.append("non-int story id denies fail-closed")

# --- load_env_file: the 2026-08-18 bug. A BOM on the first line must not break parsing. ---

with tempfile.TemporaryDirectory() as tmp:
    env_path = Path(tmp) / ".env"
    env_path.write_bytes(
        b"\xef\xbb\xbf" + b'SHORTCUT_API_TOKEN=abc123\nSHORTCUT_OWNER_UUID="owner-uuid"\n'
    )

    saved = {k: os.environ.pop(k, None) for k in ("SHORTCUT_API_TOKEN", "SHORTCUT_OWNER_UUID")}
    try:
        guard.load_env_file(env_path)
        loaded_ok = (
            os.environ.get("SHORTCUT_API_TOKEN") == "abc123"
            and os.environ.get("SHORTCUT_OWNER_UUID") == "owner-uuid"
        )
    finally:
        os.environ.pop("SHORTCUT_API_TOKEN", None)
        os.environ.pop("SHORTCUT_OWNER_UUID", None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    if not _testlib.report(loaded_ok, "BOM-prefixed .env parses SHORTCUT_API_TOKEN"):
        fails.append("BOM-prefixed .env parses SHORTCUT_API_TOKEN")

    env_path2 = Path(tmp) / ".env2"
    env_path2.write_text("SHORTCUT_API_TOKEN=untouched\n", encoding="utf-8")
    os.environ["SHORTCUT_API_TOKEN"] = "already-set"
    try:
        guard.load_env_file(env_path2)
        preserved_ok = os.environ.get("SHORTCUT_API_TOKEN") == "already-set"
    finally:
        os.environ.pop("SHORTCUT_API_TOKEN", None)
    if not _testlib.report(preserved_ok, "load_env_file never overwrites an existing env var"):
        fails.append("load_env_file never overwrites an existing env var")

# --- marker freshness, same MARKER_GLOBS shape as shortcut-create-guard.py ---

MARKER_NAMES = {".outbound-marker*": ".outbound-marker-abc", ".shortcut-marker*": ".shortcut-marker-abc"}

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    for glob in guard.MARKER_GLOBS:
        fresh = tmpdir / MARKER_NAMES[glob]
        fresh.touch()
        label = f"fresh {fresh.name} is found"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is not None, label
        ):
            fails.append(label)

        stale_time = time.time() - (guard.FRESHNESS_SECONDS + 60)
        os.utime(fresh, (stale_time, stale_time))
        label = f"{fresh.name} older than {guard.FRESHNESS_SECONDS}s is ignored"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)
        fresh.unlink()

    (tmpdir / ".commit-marker-session-xyz").touch()
    for glob in guard.MARKER_GLOBS:
        label = f"a commit marker never satisfies {glob}"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
