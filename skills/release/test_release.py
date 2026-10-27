"""Tests for release.py (source, kit-sync, bump, version-diff). Temp git repos only.

Run: python skills/release/test_release.py   (exit 0 = all pass)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fixtures as fx  # noqa: E402


def pkg(version, extra=""):
    return f'{{\n  "name": "app",\n  "version": "{version}"{extra},\n  "private": true\n}}\n'


def cargo_toml(version, name="app"):
    return (
        f'[package]\nname = "{name}"\nversion = "{version}"\nedition = "2021"\n\n'
        f'[dependencies]\nserde = "1"\n\n[dependencies.helper]\nversion = "{version}"\n'
    )


CARGO_LOCK = (
    '# generated\nversion = 4\n\n'
    '[[package]]\nname = "app"\nversion = "0.2.0"\ndependencies = [\n "serde",\n]\n\n'
    '[[package]]\nname = "helper"\nversion = "0.2.0"\n\n'
    '[[package]]\nname = "serde"\nversion = "1.0.200"\n'
)


class ReleaseBase(unittest.TestCase):
    def setUp(self):
        self._tmp = fx.tempdir()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def release(self, *args):
        return fx.run_script(fx.RELEASE_PY, *args)

    def repo(self, files, name="r", track=True):
        return fx.make_repo(self.tmp / name, files, track=track)


class SourceTest(ReleaseBase):
    def test_precedence_package_json_then_cargo_then_pubspec(self):
        r = self.repo({"package.json": pkg("1.2.3"), "src-tauri/Cargo.toml": cargo_toml("0.9.0"),
                       "pubspec.yaml": "name: a\nversion: 5.0.0+3\n"})
        self.assertEqual(self.release("source", r)[1], {"source": "package.json", "version": "1.2.3"})

    def test_cargo_when_no_package_json(self):
        r = self.repo({"src-tauri/Cargo.toml": cargo_toml("0.9.0")})
        self.assertEqual(self.release("source", r)[1], {"source": "src-tauri/Cargo.toml", "version": "0.9.0"})

    def test_pubspec_version_drops_build_number(self):
        r = self.repo({"pubspec.yaml": "name: a\nversion: 5.0.0+3\n"})
        self.assertEqual(self.release("source", r)[1], {"source": "pubspec.yaml", "version": "5.0.0"})

    def test_none(self):
        r = self.repo({"README.md": "x\n"})
        self.assertEqual(self.release("source", r)[1], {"source": None, "version": None})


class KitSyncTest(ReleaseBase):
    def test_no_submodule(self):
        r = self.repo({"README.md": "x\n"})
        rc, out = self.release("kit-sync", r)
        self.assertEqual(rc, 0)
        self.assertEqual(out, {"changed": False, "reason": "no vendor/tauri_kit"})

    def test_submodule_with_new_upstream_commit(self):
        kit = fx.make_repo(self.tmp / "kit", {"lib.txt": "1\n"})
        first = fx.git(kit, "rev-parse", "--short=7", "HEAD")
        r = self.repo({"README.md": "x\n"})
        fx.git(r, "submodule", "add", "-q", str(kit), "vendor/tauri_kit")
        fx.commit_all(r, "add kit")
        fx.write(kit, "lib.txt", "2\n")
        fx.commit_all(kit, "kit moves on")
        second = fx.git(kit, "rev-parse", "--short=7", "HEAD")

        rc, out = self.release("kit-sync", r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"changed": True, "old": first, "new": second})
        # It never commits: the moved gitlink is left as a working-tree change.
        self.assertIn("vendor/tauri_kit", fx.git(r, "status", "--porcelain"))
        self.assertEqual(fx.git(r, "log", "-1", "--format=%s"), "add kit")

        # Until the moved gitlink is committed, `old` stays the committed sha, so a re-run still
        # reports the pending change.
        rc, pending = self.release("kit-sync", r)
        self.assertEqual(pending, {"changed": True, "old": first, "new": second})

        fx.git(r, "add", "vendor/tauri_kit")
        fx.git(r, "commit", "-q", "-m", "bump kit")
        rc, again = self.release("kit-sync", r)
        self.assertEqual(again, {"changed": False, "old": second, "new": second})

    def test_submodule_already_checked_out_ahead_of_gitlink(self):
        kit = fx.make_repo(self.tmp / "kit", {"lib.txt": "1\n"})
        first = fx.git(kit, "rev-parse", "--short=7", "HEAD")
        r = self.repo({"README.md": "x\n"})
        fx.git(r, "submodule", "add", "-q", str(kit), "vendor/tauri_kit")
        fx.commit_all(r, "add kit")
        fx.write(kit, "lib.txt", "2\n")
        fx.commit_all(kit, "kit moves on")
        second = fx.git(kit, "rev-parse", "--short=7", "HEAD")
        # Advance the checkout by hand; the remote has nothing newer, so update --remote is a no-op.
        fx.git(r / "vendor" / "tauri_kit", "pull", "-q")
        self.assertTrue(fx.git(r, "submodule", "status", "--", "vendor/tauri_kit").startswith("+"))

        rc, out = self.release("kit-sync", r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"changed": True, "old": first, "new": second})

    def test_uninitialized_submodule_is_initialised(self):
        kit = fx.make_repo(self.tmp / "kit", {"lib.txt": "1\n"})
        first = fx.git(kit, "rev-parse", "--short=7", "HEAD")
        origin = fx.make_repo(self.tmp / "origin", {"README.md": "x\n"})
        fx.git(origin, "submodule", "add", "-q", str(kit), "vendor/tauri_kit")
        fx.commit_all(origin, "add kit")
        clone = self.tmp / "clone"
        fx.git(self.tmp, "clone", "-q", str(origin), str(clone))
        self.assertTrue(fx.git(clone, "submodule", "status", "--", "vendor/tauri_kit").startswith("-"))

        rc, out = self.release("kit-sync", clone)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out, {"changed": False, "old": first, "new": first})
        self.assertTrue((clone / "vendor" / "tauri_kit" / "lib.txt").is_file())


class BumpTest(ReleaseBase):
    def bump(self, r):
        return self.release("bump", r)

    def assertUntouched(self, r, files):
        for rel, content in files.items():
            self.assertEqual(fx.read(r, rel), content.encode() if isinstance(content, str) else content, rel)

    def test_package_json_tauri_v1_and_lock_change_only_version_lines(self):
        files = {
            "package.json": pkg("1.0.5", ',\n  "build": "21"'),
            "src-tauri/tauri.conf.json": '{\n  "build": {"distDir": "../dist"},\n  "package": {\n    "productName": "app",\n    "version": "1.0.5"\n  }\n}\n',
            "package-lock.json": '{\n  "name": "app",\n  "version": "1.0.5",\n  "packages": {\n    "": {\n      "name": "app",\n      "version": "1.0.5"\n    },\n    "node_modules/dep": {\n      "version": "1.0.5"\n    }\n  }\n}\n',
            "manifest.json": '{\n  "manifest_version": 3,\n  "version": "1.0.5"\n}\n',
            "tsconfig.json": '{\n  "compilerOptions": {}\n}\n',
        }
        r = self.repo(files)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["version"], "1.0.6")
        self.assertEqual(out["build"], "21")
        self.assertEqual(out["label"], "1.0.6+21")
        self.assertEqual(sorted(out["files"]), ["manifest.json", "package-lock.json", "package.json",
                                                "src-tauri/tauri.conf.json"])
        # Byte-exact: the expected file is the original with the version strings substituted.
        self.assertEqual(fx.read(r, "package.json").decode(), files["package.json"].replace('"1.0.5"', '"1.0.6"'))
        self.assertEqual(fx.read(r, "manifest.json").decode(), files["manifest.json"].replace('"1.0.5"', '"1.0.6"'))
        self.assertEqual(fx.read(r, "src-tauri/tauri.conf.json").decode(),
                         files["src-tauri/tauri.conf.json"].replace('"1.0.5"', '"1.0.6"'))
        lock = fx.read(r, "package-lock.json").decode()
        self.assertEqual(lock, files["package-lock.json"].replace('"1.0.5",\n  "packages"', '"1.0.6",\n  "packages"')
                         .replace('"name": "app",\n      "version": "1.0.5"', '"name": "app",\n      "version": "1.0.6"'))
        self.assertIn('"node_modules/dep": {\n      "version": "1.0.5"', lock)
        self.assertUntouched(r, {"tsconfig.json": files["tsconfig.json"]})

    def test_tauri_v2_top_level_version(self):
        files = {"package.json": pkg("2.0.0"),
                 "src-tauri/tauri.conf.json": '{\n  "version": "2.0.0",\n  "build": {"frontendDist": "../dist"}\n}\n'}
        r = self.repo(files)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fx.read(r, "src-tauri/tauri.conf.json").decode(),
                         files["src-tauri/tauri.conf.json"].replace('"2.0.0"', '"2.0.1"'))

    def test_package_lock_untracked_is_left_alone(self):
        r = self.repo({"package.json": pkg("1.0.0"), ".gitignore": "package-lock.json\n"})
        lock = '{\n  "version": "1.0.0",\n  "packages": {"": {"version": "1.0.0"}}\n}\n'
        fx.write(r, "package-lock.json", lock)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["files"], ["package.json"])
        self.assertEqual(fx.read(r, "package-lock.json").decode(), lock)

    def test_cargo_toml_and_lock_touch_only_the_root_package_version_lines(self):
        files = {"src-tauri/Cargo.toml": cargo_toml("0.2.0"), "src-tauri/Cargo.lock": CARGO_LOCK}
        r = self.repo(files)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["version"], "0.2.1")
        self.assertIsNone(out["build"])
        self.assertEqual(out["label"], "0.2.1")
        # Only the [package] version changes in the manifest, not the [dependencies.helper] one.
        self.assertEqual(fx.read(r, "src-tauri/Cargo.toml").decode(),
                         files["src-tauri/Cargo.toml"].replace('name = "app"\nversion = "0.2.0"',
                                                               'name = "app"\nversion = "0.2.1"'))
        # helper shares app's version string in the lock, so a global replace would corrupt it.
        self.assertEqual(fx.read(r, "src-tauri/Cargo.lock").decode(),
                         CARGO_LOCK.replace('name = "app"\nversion = "0.2.0"', 'name = "app"\nversion = "0.2.1"'))
        diff = fx.git(r, "diff", "--unified=0", "--", "src-tauri/Cargo.lock")
        changed = [ln for ln in diff.splitlines() if ln[:1] in "+-" and ln[:3] not in ("+++", "---")]
        self.assertEqual(changed, ['-version = "0.2.0"', '+version = "0.2.1"'])

    def test_cargo_lock_in_ancestor_dir(self):
        files = {"src-tauri/Cargo.toml": cargo_toml("0.2.0"), "Cargo.lock": CARGO_LOCK}
        r = self.repo(files)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertIn("Cargo.lock", out["files"])
        self.assertIn('name = "app"\nversion = "0.2.1"', fx.read(r, "Cargo.lock").decode())

    def test_untracked_cargo_lock_is_untouched(self):
        r = self.repo({"src-tauri/Cargo.toml": cargo_toml("0.2.0"), ".gitignore": "Cargo.lock\n"})
        fx.write(r, "src-tauri/Cargo.lock", CARGO_LOCK)
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["files"], ["src-tauri/Cargo.toml"])
        self.assertEqual(fx.read(r, "src-tauri/Cargo.lock").decode(), CARGO_LOCK)

    def test_pubspec_bumps_build_number_and_keeps_crlf(self):
        text = "name: demo\r\nversion: 1.2.3+7\r\ndependencies:\r\n  http:\r\n    version: 1.2.3+7\r\n"
        r = self.repo({"pubspec.yaml": text.encode()})
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual((out["version"], out["build"], out["label"]), ("1.2.4", "8", "1.2.4+8"))
        self.assertEqual(fx.read(r, "pubspec.yaml"),
                         text.replace("\r\nversion: 1.2.3+7\r\n", "\r\nversion: 1.2.4+8\r\n").encode())

    def test_pubspec_without_build_number_stays_without(self):
        r = self.repo({"pubspec.yaml": "name: demo\nversion: 1.2.3\n"})
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fx.read(r, "pubspec.yaml"), b"name: demo\nversion: 1.2.4\n")
        self.assertIsNone(out["build"])

    def test_crlf_json_preserved(self):
        text = '{\r\n  "name": "app",\r\n  "version": "3.0.0"\r\n}\r\n'
        r = self.repo({"package.json": text.encode()})
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fx.read(r, "package.json"), text.replace("3.0.0", "3.0.1").encode())

    def test_drift_is_repaired_to_one_new_version(self):
        r = self.repo({"package.json": pkg("1.0.5"),
                       "src-tauri/tauri.conf.json": '{\n  "version": "1.0.3"\n}\n'})
        rc, out = self.bump(r)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["version"], "1.0.6")
        self.assertIn('"version": "1.0.6"', fx.read(r, "src-tauri/tauri.conf.json").decode())
        self.assertIn('"version": "1.0.6"', fx.read(r, "package.json").decode())

    def test_dirty_target_refuses_and_changes_nothing(self):
        files = {"package.json": pkg("1.0.5"), "src-tauri/tauri.conf.json": '{\n  "version": "1.0.5"\n}\n'}
        r = self.repo(files)
        peer_edit = files["src-tauri/tauri.conf.json"] + "\n"
        fx.write(r, "src-tauri/tauri.conf.json", peer_edit)
        rc, out = self.bump(r)
        self.assertEqual(rc, 2)
        self.assertIn("uncommitted", out["error"])
        self.assertEqual(fx.read(r, "package.json").decode(), files["package.json"])
        self.assertEqual(fx.read(r, "src-tauri/tauri.conf.json").decode(), peer_edit)

    def test_no_source_refuses(self):
        r = self.repo({"README.md": "x\n"})
        rc, out = self.bump(r)
        self.assertEqual(rc, 2)
        self.assertIn("no version source", out["error"])

    def test_version_sharing_a_line_with_other_content_is_refused_and_restored(self):
        # Minified JSON: the one-line edit would change a line that is not only the version line.
        text = '{"name":"app","version":"1.0.0","private":true}\n'
        r = self.repo({"package.json": text})
        rc, out = self.bump(r)
        self.assertEqual(rc, 2)
        self.assertIn("not a version line", out["error"])
        self.assertEqual(fx.read(r, "package.json").decode(), text)
        self.assertEqual(fx.git(r, "status", "--porcelain"), "")

    def test_non_semver_source_refuses(self):
        r = self.repo({"package.json": pkg("1.0.0-beta.1")})
        rc, out = self.bump(r)
        self.assertEqual(rc, 2)
        self.assertEqual(fx.git(r, "status", "--porcelain"), "")

    def test_bump_never_commits_or_stages(self):
        r = self.repo({"package.json": pkg("1.0.0")})
        head = fx.git(r, "rev-parse", "HEAD")
        self.bump(r)
        self.assertEqual(fx.git(r, "rev-parse", "HEAD"), head)
        self.assertEqual(fx.git(r, "diff", "--cached", "--name-only"), "")


class VersionDiffTest(ReleaseBase):
    def setUp(self):
        super().setUp()
        self.bare = self.tmp / "remote.git"
        self.bare.mkdir()
        fx.git(self.bare, "init", "-q", "--bare", "-b", "main")

    def clone(self, name):
        dest = self.tmp / name
        fx.git(self.tmp, "clone", "-q", str(self.bare), str(dest))
        fx.configure(dest)
        return dest

    def seed(self, files):
        seed = self.clone("seed")
        fx.git(seed, "symbolic-ref", "HEAD", "refs/heads/main")
        for rel, content in files.items():
            fx.write(seed, rel, content)
        fx.commit_all(seed, "init")
        fx.git(seed, "push", "-q", "-u", "origin", "main")

    def set_version(self, repo, version, push=False):
        fx.write(repo, "package.json", pkg(version))
        fx.commit_all(repo, f"VERSION: {version}")
        if push:
            fx.git(repo, "push", "-q", "origin", "HEAD")

    def test_teammate_bump_on_upstream_is_not_pending(self):
        self.seed({"package.json": pkg("1.0.0")})
        local, mate = self.clone("local"), self.clone("mate")
        self.set_version(mate, "1.0.1", push=True)
        rc, out = self.release("version-diff", local)
        self.assertEqual(rc, 0, out)
        self.assertFalse(out["pending"], out)
        self.assertEqual((out["base_version"], out["head_version"], out["base_ref"]), ("1.0.0", "1.0.0", "origin/main"))

    def test_local_unpushed_bump_is_pending_even_when_upstream_also_advanced(self):
        self.seed({"package.json": pkg("1.0.0")})
        local, mate = self.clone("local"), self.clone("mate")
        self.set_version(local, "1.0.1")
        self.set_version(mate, "1.0.2", push=True)
        rc, out = self.release("version-diff", local)
        self.assertEqual(rc, 0, out)
        self.assertTrue(out["pending"], out)
        self.assertEqual((out["base_version"], out["head_version"]), ("1.0.0", "1.0.1"))

    def test_source_file_absent_at_base_is_not_pending(self):
        self.seed({"README.md": "x\n"})
        local = self.clone("local")
        fx.write(local, "package.json", pkg("0.1.0"))
        fx.commit_all(local, "add package.json")
        rc, out = self.release("version-diff", local)
        self.assertEqual(rc, 0, out)
        self.assertFalse(out["pending"])
        self.assertIn("did not exist", out["reason"])

    def test_falls_back_to_origin_head_without_upstream(self):
        self.seed({"package.json": pkg("1.0.0")})
        local = self.clone("local")
        fx.git(local, "checkout", "-q", "-b", "feature")
        fx.git(local, "branch", "--unset-upstream", check=False)
        self.set_version(local, "1.0.1")
        rc, out = self.release("version-diff", local)
        self.assertEqual(rc, 0, out)
        self.assertEqual(out["base_ref"], "origin/main")
        self.assertTrue(out["pending"])

    def test_fetch_failure_is_exit_3_and_no_fetch_skips_it(self):
        self.seed({"package.json": pkg("1.0.0")})
        local = self.clone("local")
        fx.git(local, "remote", "set-url", "origin", str(self.tmp / "gone.git"))
        rc, out = self.release("version-diff", local)
        self.assertEqual(rc, 3)
        self.assertIn("fetch failed", out["error"])
        rc, out = self.release("version-diff", local, "--no-fetch")
        self.assertEqual(rc, 0, out)
        self.assertFalse(out["pending"])

    def test_no_comparable_ref_is_exit_2(self):
        r = self.repo({"package.json": pkg("1.0.0")})
        rc, out = self.release("version-diff", r, "--no-fetch")
        self.assertEqual(rc, 2)
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main(verbosity=1)
