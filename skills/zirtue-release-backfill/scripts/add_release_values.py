"""Add missing values to the Shortcut Release custom field (enum).

Usage:
    python add_release_values.py "FE 1.1.0+3" "Admin 1.0.0+13"           # dry run
    python add_release_values.py --apply "FE 1.1.0+3" "Admin 1.0.0+13"   # write

PUT /custom-fields/{id} treats `values` as the COMPLETE enum: an entry without an
id is created, and any existing value left out is DELETED (which would strip it off
every ticket using it). So this script always resends every existing value
unchanged, appends the new ones last, and refuses to run if the payload would drop
an id. After the PUT it re-reads the field and checks every old id survived.

Labels must match ^(FE|Admin|API|Biller) \\d+\\.\\d+\\.\\d+(\\+\\d+)?$ so a typo can't
land in the shared workspace. Labels already present are skipped.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

API = "https://api.app.shortcut.com/api/v3"
RELEASE_FIELD_ID = "68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb"
LABEL_RE = re.compile(r"^(FE|Admin|API|Biller) \d+\.\d+\.\d+(\+\d+)?$")
ENV_FILE = Path.home() / ".claude" / ".env"


def load_token() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "SHORTCUT_API_TOKEN":
            return value.strip().strip('"').strip("'")
    sys.exit("SHORTCUT_API_TOKEN not found in ~/.claude/.env")


def request(method: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}/custom-fields/{RELEASE_FIELD_ID}",
        method=method,
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Shortcut-Token": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} failed: HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")


def main() -> None:
    args = sys.argv[1:]
    apply = "--apply" in args
    labels = [a for a in args if a != "--apply"]
    if not labels:
        sys.exit(__doc__)
    bad = [label for label in labels if not LABEL_RE.match(label)]
    if bad:
        sys.exit(f"refusing labels that don't match {LABEL_RE.pattern}: {bad}")

    token = load_token()
    field = request("GET", token)
    existing = field["values"]
    existing_labels = {v["value"] for v in existing}
    to_add = [label for label in dict.fromkeys(labels) if label not in existing_labels]
    already = [label for label in labels if label in existing_labels]

    print(f"existing values: {len(existing)}")
    if already:
        print(f"already present, skipped: {already}")
    if not to_add:
        print("nothing to add")
        return
    print(f"to add (appended last): {to_add}")

    # Values created by this script have color_key null; echoing null back is untested, so drop it.
    values = [
        {k: v[k] for k in ("id", "value", "color_key", "enabled") if v.get(k) is not None} for v in existing
    ] + [{"value": label} for label in to_add]

    old_ids = {v["id"] for v in existing}
    sent_ids = {v["id"] for v in values if "id" in v}
    if sent_ids != old_ids or len(values) != len(existing) + len(to_add):
        sys.exit("payload would drop or duplicate an existing value, aborting")

    if not apply:
        print("dry run, pass --apply to write")
        return

    request("PUT", token, {"values": values})

    after = request("GET", token)["values"]
    after_ids = {v["id"] for v in after}
    after_labels = {v["value"] for v in after}
    lost = old_ids - after_ids
    missing = [label for label in to_add if label not in after_labels]
    if lost or missing:
        sys.exit(f"VERIFY FAILED: lost ids {sorted(lost)}, labels not created {missing}")
    print(f"ok: {len(after)} values, added {to_add}")
    for v in after:
        if v["value"] in to_add:
            print(f"  {v['value']} -> {v['id']}")


if __name__ == "__main__":
    main()
