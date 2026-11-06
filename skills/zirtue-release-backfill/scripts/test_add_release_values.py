"""Self-test for add_release_values.py. Run: python test_add_release_values.py"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import add_release_values as arv  # noqa: E402

EXISTING = [
    {"id": "a", "value": "FE 1.1.0+2", "color_key": "brass", "enabled": True, "position": 0},
    {"id": "b", "value": "Admin 1.0.0+12", "color_key": None, "enabled": True, "position": 1},
]


class FakeApi:
    def __init__(self):
        self.values = [dict(v) for v in EXISTING]
        self.put_body = None

    def __call__(self, method, token, body=None):
        if method == "PUT":
            self.put_body = body
            kept = [dict(v) for v in self.values if v["id"] in {x.get("id") for x in body["values"]}]
            self.values = kept + [
                {"id": f"new{i}", "value": x["value"], "color_key": None, "enabled": True}
                for i, x in enumerate(body["values"])
                if "id" not in x
            ]
        return {"values": [dict(v) for v in self.values]}


def run(argv, api):
    with mock.patch.object(arv, "request", api), mock.patch.object(arv, "load_token", lambda: "t"), \
            mock.patch.object(sys, "argv", ["x", *argv]):
        arv.main()


class AddReleaseValuesTest(unittest.TestCase):
    def test_apply_resends_every_existing_value_and_appends_new(self):
        api = FakeApi()
        run(["--apply", "FE 1.1.0+3", "FE 1.1.0+2"], api)
        sent = api.put_body["values"]
        self.assertEqual([v.get("id") for v in sent], ["a", "b", None])
        self.assertEqual(sent[-1], {"value": "FE 1.1.0+3"})
        self.assertNotIn("color_key", sent[1])

    def test_dry_run_never_puts(self):
        api = FakeApi()
        run(["FE 1.1.0+3"], api)
        self.assertIsNone(api.put_body)

    def test_rejects_malformed_label(self):
        api = FakeApi()
        with self.assertRaises(SystemExit):
            run(["--apply", "FE 1.1.0-3"], api)
        self.assertIsNone(api.put_body)

    def test_verify_fails_when_put_drops_an_old_value(self):
        api = FakeApi()

        def lossy(method, token, body=None):
            if method == "PUT":
                body = {"values": body["values"][1:]}
            return api(method, token, body)

        with self.assertRaises(SystemExit) as ctx:
            run(["--apply", "FE 1.1.0+3"], lossy)
        self.assertIn("VERIFY FAILED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
