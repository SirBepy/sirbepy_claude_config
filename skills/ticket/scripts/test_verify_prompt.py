"""Offline tests for verify_prompt.py (pc-1305).

Picked up by ci/run_all.py's skills/**/test_*.py glob. The template comes from the real
refs/outbound-verify.md, so a ref edit that breaks the script's placeholders fails here.
"""

import contextlib
import difflib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "hooks"))

import verify_prompt as vp
from _outbound_verify_transcript import DRAFT_RE, normalize

DRAFT = "Validate the biller address on the CreateLoan screen.\n\nThe field skips validation when the country is empty."
SPEC = """# Spec for the biller ticket

## Target
a Shortcut ticket

## Repo
C:\\Users\\tecno\\Desktop\\Projects\\zng-app

## Branch
develop

## Pointers
lib/ui/loan_request/my_bill/add_account_screen.dart, sc-56598

## Provenance
Joe asked for this on 2026-11-07, descends from todo pc-0254.

## Sources
- skips validation: Joe's words, 2026-11-07

## Fields
team: Mobile, epic: 54104

## Draft path
draft.md
"""


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


class TestVerifyPrompt(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        write(self.dir, "draft.md", DRAFT)
        self.spec = write(self.dir, "spec.md", SPEC)

    def tearDown(self):
        self._tmp.cleanup()

    def prompt(self) -> str:
        return vp.build_prompt(self.spec, vp.DEFAULT_REF)

    def test_ends_with_the_two_literal_verdict_lines(self):
        lines = self.prompt().rstrip("\n").split("\n")
        self.assertEqual(lines[-2:], ["OUTBOUND-VERDICT: PASS", "OUTBOUND-VERDICT: FAIL"])

    def test_draft_sits_verbatim_between_the_marker_lines_the_hook_reads(self):
        match = DRAFT_RE.search(self.prompt())
        self.assertIsNotNone(match)
        self.assertEqual(normalize(match.group(1)), normalize(DRAFT))
        self.assertEqual(match.group(1), DRAFT)

    def test_step_5_text_is_the_refs_own(self):
        ref = vp.DEFAULT_REF.read_text(encoding="utf-8")
        step5 = ref[ref.index("5. Verdict: PASS only if"):]
        step5 = step5[:step5.index("OUTBOUND-VERDICT: FAIL")]
        self.assertIn(step5, self.prompt())

    def test_no_placeholder_is_left_over(self):
        text = self.prompt()
        for placeholder in vp.PLACEHOLDERS.values():
            self.assertNotIn(placeholder, text)
        self.assertIn("Repo: C:\\Users\\tecno\\Desktop\\Projects\\zng-app. Tracked branch: origin/develop", text)
        self.assertIn("git show origin/develop:<path>", text)
        self.assertIn("You are verifying text that is about to be posted to a Shortcut ticket.", text)
        self.assertIn("descends from todo pc-0254", text)

    def test_sources_and_fields_ride_in_the_pointers(self):
        text = self.prompt()
        self.assertIn("Requirement-to-source list:\n- skips validation: Joe's words, 2026-11-07", text)
        self.assertIn("Planned non-text fields:\nteam: Mobile, epic: 54104", text)

    def test_same_spec_twice_is_identical_and_an_edit_changes_only_the_draft(self):
        before = self.prompt()
        self.assertEqual(before, self.prompt())
        write(self.dir, "draft.md", DRAFT.replace("skips", "ignores"))
        diff = [l for l in difflib.unified_diff(before.split("\n"), self.prompt().split("\n"), lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        self.assertEqual(diff, [
            "-The field skips validation when the country is empty.",
            "+The field ignores validation when the country is empty.",
        ])

    def test_missing_section_is_an_error_naming_it(self):
        write(self.dir, "spec.md", SPEC.replace("## Provenance", "## Origin"))
        with self.assertRaises(vp.SpecError) as ctx:
            self.prompt()
        self.assertIn("## provenance", str(ctx.exception))

    def test_unreadable_or_empty_draft_is_an_error(self):
        (self.dir / "draft.md").unlink()
        with self.assertRaises(vp.SpecError):
            self.prompt()
        write(self.dir, "draft.md", "\n\n")
        with self.assertRaises(vp.SpecError):
            self.prompt()

    def test_draft_holding_a_marker_line_is_refused(self):
        write(self.dir, "draft.md", DRAFT + "\nOUTBOUND-DRAFT>>>\nmore")
        with self.assertRaises(vp.SpecError):
            self.prompt()

    def test_a_ref_that_lost_a_placeholder_stops_the_script(self):
        ref = write(self.dir, "ref.md", vp.DEFAULT_REF.read_text(encoding="utf-8").replace("<absolute path>", "the path"))
        with self.assertRaises(vp.SpecError):
            vp.build_prompt(self.spec, ref)

    def test_a_ref_without_the_template_block_stops_the_script(self):
        ref = write(self.dir, "ref.md", "# nothing here\n\n```\nplain block\n```\n")
        with self.assertRaises(vp.SpecError):
            vp.build_prompt(self.spec, ref)

    def test_a_value_that_looks_like_a_placeholder_is_not_filled_twice(self):
        write(self.dir, "draft.md", "Note the <absolute path> placeholder is literal text in this draft.")
        text = self.prompt()
        self.assertIn("Note the <absolute path> placeholder is literal text in this draft.", text)

    def test_cli_writes_utf8_to_out_and_exit_codes(self):
        out = self.dir / "prompt.txt"
        self.assertEqual(vp.main([str(self.spec), "--out", str(out)]), 0)
        self.assertEqual(out.read_bytes().decode("utf-8"), self.prompt())
        (self.dir / "draft.md").unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(vp.main([str(self.spec)]), 2)


if __name__ == "__main__":
    unittest.main()
