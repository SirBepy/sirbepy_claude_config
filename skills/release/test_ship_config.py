"""Tests for ship-config.py. Temp git repos only; the real client list and config home are never
read (SHIP_CONFIG_CLIENT_LIST / SHIP_CONFIG_HOME point into the temp dir).

Run: python skills/release/test_ship_config.py   (exit 0 = all pass)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fixtures as fx  # noqa: E402

CLIENT_LIST = "# test list\nzirtue-corp/zng-app\nRevaire-Inc/revaire-server\n"
PKG = '{\n  "name": "x",\n  "version": "1.0.0"\n}\n'


class ShipConfigTest(unittest.TestCase):
    def setUp(self):
        self._tmp = fx.tempdir()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self.home.mkdir()
        (self.tmp / "clients.txt").write_text(CLIENT_LIST, encoding="utf-8")
        self.env = fx.base_env(
            SHIP_CONFIG_HOME=str(self.home),
            SHIP_CONFIG_CLIENT_LIST=str(self.tmp / "clients.txt"),
        )
        self.addCleanup(self._tmp.cleanup)

    def repo(self, name, origin, files=None):
        return fx.make_repo(self.tmp / name, files if files is not None else {"README.md": "hi\n"}, origin=origin)

    def get(self, repo):
        return fx.run_script(fx.SHIP_CONFIG_PY, "get", repo, env=self.env)

    def set(self, repo, *pairs):
        return fx.run_script(fx.SHIP_CONFIG_PY, "set", repo, *pairs, env=self.env)

    # ---- get

    def test_personal_with_version_source_defaults_to_patch(self):
        r = self.repo("p", "https://github.com/someone/tool.git", {"package.json": PKG})
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "personal")
        self.assertEqual(out["release"], "patch")
        self.assertIs(out["todo_sweep"], False)
        self.assertEqual(out["source"], "default")
        self.assertEqual(out["slug"], "someone/tool")

    def test_personal_without_version_source_defaults_to_none(self):
        r = self.repo("p", "git@github.com:someone/tool.git")
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["release"], "none")
        self.assertIn("no version source", out["reason"])

    def test_client_forces_sweep_and_leaves_release_unset(self):
        r = self.repo("c", "git@github-work:Zirtue-Corp/ZNG-App.git", {"package.json": PKG})
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "client")
        self.assertIs(out["todo_sweep"], True)
        self.assertIsNone(out["release"])
        self.assertEqual(out["slug"], "zirtue-corp/zng-app")

    def test_unlisted_repo_of_client_owner_is_unknown(self):
        r = self.repo("u", "https://github.com/Zirtue-Corp/new-repo.git")
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "unknown")
        self.assertIs(out["todo_sweep"], True)
        self.assertIsNone(out["release"])

    def test_missing_client_list_fails_closed_to_unknown(self):
        r = self.repo("c", "git@github-work:Zirtue-Corp/ZNG-App.git", {"package.json": PKG})
        missing = self.tmp / "nope" / "clients.txt"
        self.env["SHIP_CONFIG_CLIENT_LIST"] = str(missing)
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "unknown")
        self.assertIs(out["todo_sweep"], True)
        self.assertIsNone(out["release"])
        self.assertIn(str(missing), out["reason"])
        rc, err = self.set(r, "release=patch")
        self.assertEqual(rc, 2)
        self.assertIn(str(missing), err["error"])

    def test_empty_client_list_fails_closed_to_unknown(self):
        r = self.repo("c", "https://github.com/someone/tool.git", {"package.json": PKG})
        empty = self.tmp / "empty.txt"
        empty.write_text("# only a comment\n\n", encoding="utf-8")
        self.env["SHIP_CONFIG_CLIENT_LIST"] = str(empty)
        rc, out = self.get(r)
        self.assertEqual(out["class"], "unknown")
        self.assertIn(str(empty), out["reason"])

    def test_no_origin_is_unknown(self):
        r = self.repo("n", None)
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "unknown")
        self.assertIsNone(out["slug"])
        self.assertIn("no resolvable origin", out["reason"])

    def test_not_a_git_repo_is_unknown(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        rc, out = self.get(plain)
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "unknown")

    def test_personal_override_applies(self):
        r = self.repo("p", "https://github.com/someone/tool.git", {"package.json": PKG})
        fx.write(r, ".claude/ship.md", "# mine\nrelease: none\n\ntodo_sweep: yes\n")
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["release"], "none")
        self.assertIs(out["todo_sweep"], True)
        self.assertEqual(out["source"], "override:" + str(r / ".claude" / "ship.md"))

    def test_client_override_sets_release_but_cannot_disable_sweep(self):
        r = self.repo("c", "https://github.com/zirtue-corp/zng-app.git")
        fx.write(self.home, "refs/ship-config/zirtue-corp__zng-app.md", "release: patch\ntodo_sweep: no\n")
        rc, out = self.get(r)
        self.assertEqual(rc, 0)
        self.assertEqual(out["release"], "patch")
        self.assertIs(out["todo_sweep"], True)
        self.assertTrue(out["source"].startswith("override:"))
        self.assertIn("ignored", out["reason"])

    def test_bad_key_is_exit_2(self):
        r = self.repo("p", "https://github.com/someone/tool.git")
        fx.write(r, ".claude/ship.md", "colour: blue\n")
        rc, out = self.get(r)
        self.assertEqual(rc, 2)
        self.assertIn("unknown key", out["error"])

    def test_bad_value_is_exit_2(self):
        r = self.repo("p", "https://github.com/someone/tool.git")
        fx.write(r, ".claude/ship.md", "release: major\n")
        rc, out = self.get(r)
        self.assertEqual(rc, 2)
        self.assertIn("error", out)

    # ---- set

    def test_set_writes_file_and_keeps_unrelated_lines(self):
        r = self.repo("p", "https://github.com/someone/tool.git", {"package.json": PKG})
        fx.write(r, ".claude/ship.md", "# keep me\nrelease: none\n")
        rc, out = self.set(r, "release=patch", "todo_sweep=yes")
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "personal")
        self.assertEqual(Path(out["path"]), r / ".claude" / "ship.md")
        self.assertEqual(fx.read(r, ".claude/ship.md").decode(), "# keep me\nrelease: patch\ntodo_sweep: yes\n")
        _, got = self.get(r)
        self.assertEqual((got["release"], got["todo_sweep"]), ("patch", True))
        self.assertEqual(fx.git(r, "status", "--porcelain", "--", ".claude/ship.md"), "?? .claude/ship.md")

    def test_set_creates_client_override_under_config_home(self):
        r = self.repo("c", "https://github.com/zirtue-corp/zng-app.git")
        rc, out = self.set(r, "release=patch")
        self.assertEqual(rc, 0)
        self.assertEqual(out["class"], "client")
        self.assertEqual(Path(out["path"]), self.home / "refs" / "ship-config" / "zirtue-corp__zng-app.md")
        self.assertEqual(Path(out["path"]).read_text(), "release: patch\n")

    def test_set_refuses_unknown_class_under_client_owner(self):
        r = self.repo("u", "https://github.com/zirtue-corp/new-repo.git")
        rc, out = self.set(r, "release=patch")
        self.assertEqual(rc, 2)
        self.assertIn("unlisted repo under client owner zirtue-corp", out["error"])
        self.assertIn("add zirtue-corp/new-repo to refs/client-repos.txt", out["error"])
        self.assertFalse((self.home / "refs").exists())

    def test_set_refuses_when_no_origin(self):
        r = self.repo("n", None)
        rc, out = self.set(r, "release=patch")
        self.assertEqual(rc, 2)
        self.assertIn("no resolvable origin remote", out["error"])

    def test_set_refuses_todo_sweep_no_for_client(self):
        r = self.repo("c", "https://github.com/zirtue-corp/zng-app.git")
        rc, out = self.set(r, "todo_sweep=no")
        self.assertEqual(rc, 2)
        self.assertIn("error", out)
        self.assertFalse((self.home / "refs").exists())

    def test_set_rejects_bad_pair(self):
        r = self.repo("p", "https://github.com/someone/tool.git")
        rc, out = self.set(r, "release=major")
        self.assertEqual(rc, 2)
        self.assertFalse((r / ".claude").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
