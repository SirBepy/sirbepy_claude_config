"""Offline test suite for shortcut_triage.py (todo 1096).

No network call: every fixture here is small hand-written JSON, never real
ticket content. Picked up by ci/run_all.py's discover_skill_tests() glob for
skills/**/test_*.py beside its script.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shortcut_triage as st


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

REFS = {
    "members": {"m1": "alice", "m2": "bob"},
    "epics": {"e1": "Widgets"},
    "states": {500: ("ENG - Core Workflow", "To Do")},
    "cf_values": {"v1": "Frontend"},
    "cf_names": {"f1": "Skill Set"},
}

STORY = {
    "id": 101,
    "name": "Fix the thing",
    "story_type": "bug",
    "workflow_state_id": 500,
    "archived": False,
    "owner_ids": ["m1"],
    "requested_by_id": "m2",
    "epic_id": "e1",
    "labels": [{"name": "frontend"}],
    "custom_fields": [{"field_id": "f1", "value_id": "v1"}],
    "created_at": "2026-09-01T00:00:00Z",
    "updated_at": "2026-09-05T00:00:00Z",
    "started_at": "2026-09-02T00:00:00Z",
    "deadline": None,
    "story_links": [{"verb": "relates to", "subject_id": 101, "object_id": 202}],
    "pull_requests": [{"url": "https://github.com/x/y/pull/1"}],
    "branches": [],
    "commits": [],
    "tasks": [{"complete": True, "description": "write tests"}],
    "description": "Something is broken.",
    "comments": [
        {"author_id": "m1", "created_at": "2026-09-03T00:00:00Z", "text": "repro confirmed", "deleted": False},
        {"author_id": "m2", "created_at": "2026-09-04T00:00:00Z", "text": "ghost comment", "deleted": True},
    ],
}


class TestApiCallIsReadOnly(unittest.TestCase):
    def test_get_allowed_shape(self):
        # Doesn't hit the network: urlopen itself is mocked.
        fake_response = mock.MagicMock()
        fake_response.read.return_value = b'{"ok": true}'
        fake_response.__enter__.return_value = fake_response
        with mock.patch("urllib.request.urlopen", return_value=fake_response):
            result = st.api_call("GET", "/api/v3/x", "tok")
        self.assertEqual(result, {"ok": True})

    def test_write_verbs_rejected(self):
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            with self.assertRaises(ValueError):
                st.api_call(method, "/api/v3/stories/1", "tok", body={"x": 1})


class TestReadToken(unittest.TestCase):
    def test_strips_bom_crlf_and_quotes(self):
        raw = "﻿SOME_OTHER=1\r\nSHORTCUT_API_TOKEN=\"abc123\"\r\n"
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".env")
            with open(path, "w", encoding="utf-8") as f:
                f.write(raw)
            self.assertEqual(st.read_token(path), "abc123")

    def test_missing_token_raises(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, ".env")
            with open(path, "w", encoding="utf-8") as f:
                f.write("OTHER=1\n")
            with self.assertRaises(RuntimeError):
                st.read_token(path)


class TestSearch(unittest.TestCase):
    def test_single_query_paginates(self):
        pages = [
            {"data": [{"id": 1, "name": "a"}], "next": "/api/v3/search/stories?page=2"},
            {"data": [{"id": 2, "name": "b"}], "next": None},
        ]
        with mock.patch.object(st, "api_call", side_effect=pages):
            result = st._search_one("owner:x", "tok", 250, None)
        self.assertEqual([s["id"] for s in result], [1, 2])

    def test_split_types_dedupes_by_id(self):
        # Same story id 1 shows up under two type queries - split_types must
        # merge, not double-count, since that's the 1000-result-cap fix.
        responses = {
            "owner:x type:feature": [{"data": [{"id": 1, "name": "a"}], "next": None}],
            "owner:x type:bug": [{"data": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}], "next": None}],
        }
        calls = {"owner:x type:feature": 0, "owner:x type:bug": 0}

        def fake_search_one(query, token, page_size, detail):
            calls[query] += 1
            return [d for page in responses[query] for d in page["data"]]

        with mock.patch.object(st, "_search_one", side_effect=fake_search_one):
            result = st.search_stories("owner:x", "tok", split_types=["feature", "bug"])
        self.assertEqual(sorted(s["id"] for s in result), [1, 2])

    def test_shape_candidate_trims_fields(self):
        c = st.shape_candidate(STORY)
        self.assertEqual(
            c,
            {
                "id": 101,
                "name": "Fix the thing",
                "story_type": "bug",
                "workflow_state_id": 500,
                "updated_at": "2026-09-05T00:00:00Z",
                "archived": False,
            },
        )


class TestLoadRefs(unittest.TestCase):
    def test_missing_dir_returns_empty_refs(self):
        refs = st.load_refs(None)
        self.assertEqual(refs["members"], {})
        self.assertEqual(refs["epics"], {})

    def test_loads_from_fixture_files(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "members.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "m1", "profile": {"mention_name": "alice"}}], f)
            with open(os.path.join(d, "epics.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "e1", "name": "Widgets"}], f)
            with open(os.path.join(d, "workflows.json"), "w", encoding="utf-8") as f:
                json.dump([{"name": "ENG", "states": [{"id": 500, "name": "To Do"}]}], f)
            with open(os.path.join(d, "custom-fields.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "f1", "name": "Skill Set", "values": [{"id": "v1", "value": "Frontend"}]}], f)
            refs = st.load_refs(d)
        self.assertEqual(refs["members"]["m1"], "alice")
        self.assertEqual(refs["epics"]["e1"], "Widgets")
        self.assertEqual(refs["states"][500], ("ENG", "To Do"))
        self.assertEqual(refs["cf_names"]["f1"], "Skill Set")
        self.assertEqual(refs["cf_values"]["v1"], "Frontend")


class TestBuildDossier(unittest.TestCase):
    def test_shapes_expected_fields(self):
        d = st.build_dossier(STORY, REFS)
        self.assertEqual(d["id"], 101)
        self.assertEqual(d["owners"], ["alice"])
        self.assertEqual(d["requester"], "bob")
        self.assertEqual(d["epic"], "Widgets")
        self.assertEqual(d["workflow"], "ENG - Core Workflow")
        self.assertEqual(d["state"], "To Do")
        self.assertEqual(d["custom_fields"], [{"field": "Skill Set", "value": "Frontend"}])
        self.assertEqual(d["story_links"], [{"verb": "relates to", "other_id": 202, "direction": "out"}])
        self.assertIn("https://github.com/x/y/pull/1", d["pr_refs"])
        self.assertEqual(d["tasks"], [{"complete": True, "description": "write tests"}])

    def test_drops_deleted_comments(self):
        d = st.build_dossier(STORY, REFS)
        self.assertEqual(len(d["comments"]), 1)
        self.assertEqual(d["comments"][0]["text"], "repro confirmed")

    def test_truncates_long_description(self):
        story = dict(STORY, description="x" * 9000)
        d = st.build_dossier(story, REFS)
        self.assertTrue(d["description_truncated"])
        self.assertEqual(len(d["description"]), st.DESCRIPTION_CHAR_CAP)

    def test_match_reasons_carried_when_given(self):
        d = st.build_dossier(STORY, REFS, reasons=["label:frontend"])
        self.assertEqual(d["match_reasons"], ["label:frontend"])

    def test_missing_refs_fall_back_to_raw_ids(self):
        empty_refs = st.load_refs(None)
        d = st.build_dossier(STORY, empty_refs)
        self.assertEqual(d["owners"], ["m1"])
        self.assertIsNone(d["workflow"])


class TestRenderMarkdown(unittest.TestCase):
    def test_contains_header_and_comments(self):
        d = st.build_dossier(STORY, REFS)
        md = st.render_markdown(d)
        self.assertIn("## sc-101: Fix the thing", md)
        self.assertIn("### Comments (1)", md)
        self.assertIn("repro confirmed", md)
        self.assertNotIn("ghost comment", md)

    def test_truncation_note_appended(self):
        story = dict(STORY, description="y" * 9000)
        d = st.build_dossier(story, REFS)
        md = st.render_markdown(d)
        self.assertIn("truncated at 8000 chars", md)


class TestBatchItems(unittest.TestCase):
    def test_single_batch_under_cap(self):
        batches = st.batch_items(["aaa", "bbb"], target_chars=100)
        self.assertEqual(batches, [["aaa", "bbb"]])

    def test_splits_when_cap_exceeded(self):
        batches = st.batch_items(["a" * 50, "b" * 50, "c" * 50], target_chars=80)
        self.assertEqual(batches, [["a" * 50], ["b" * 50], ["c" * 50]])

    def test_oversized_single_item_gets_its_own_batch(self):
        batches = st.batch_items(["x" * 500], target_chars=100)
        self.assertEqual(batches, [["x" * 500]])

    def test_empty_input(self):
        self.assertEqual(st.batch_items([], target_chars=100), [])


class TestConsensusVote(unittest.TestCase):
    def test_unanimous(self):
        j1 = [{"id": 1, "verdict": "close"}]
        j2 = [{"id": 1, "verdict": "close"}]
        j3 = [{"id": 1, "verdict": "close"}]
        result = st.tally_vote([j1, j2, j3])
        self.assertEqual(result["agreed"], {"close": [1]})
        self.assertEqual(result["disputed"], {})
        self.assertEqual(result["incomplete"], {})

    def test_disputed_with_full_coverage(self):
        j1 = [{"id": 1, "verdict": "close"}]
        j2 = [{"id": 1, "verdict": "keep"}]
        j3 = [{"id": 1, "verdict": "close"}]
        result = st.tally_vote([j1, j2, j3])
        self.assertEqual(result["agreed"], {})
        self.assertEqual(result["disputed"], {1: ["close", "keep", "close"]})

    def test_partial_coverage_is_incomplete_not_agreed(self):
        j1 = [{"id": 1, "verdict": "close"}]
        j2 = []
        j3 = [{"id": 1, "verdict": "close"}]
        result = st.tally_vote([j1, j2, j3])
        self.assertEqual(result["agreed"], {})
        self.assertEqual(result["incomplete"], {1: ["close", "close"]})

    def test_judge_count_recorded(self):
        result = st.tally_vote([[], [], []])
        self.assertEqual(result["judge_count"], 3)


class TestConsensusMedian(unittest.TestCase):
    def test_median_of_three(self):
        j1 = [{"key": "sc-1", "estimate": 2}]
        j2 = [{"key": "sc-1", "estimate": 5}]
        j3 = [{"key": "sc-1", "estimate": 3}]
        result = st.tally_median([j1, j2, j3], field="estimate")
        self.assertEqual(result["sc-1"]["median"], 3)
        self.assertEqual(result["sc-1"]["values"], [2, 3, 5])
        self.assertEqual(result["sc-1"]["judge_count"], 3)

    def test_multiple_keys_kept_separate(self):
        j1 = [{"key": "sc-1", "estimate": 2}, {"key": "sc-2", "estimate": 8}]
        j2 = [{"key": "sc-1", "estimate": 4}, {"key": "sc-2", "estimate": 6}]
        result = st.tally_median([j1, j2], field="estimate")
        self.assertEqual(set(result.keys()), {"sc-1", "sc-2"})


class TestArgumentParsing(unittest.TestCase):
    def test_search_subcommand(self):
        args = st.build_parser().parse_args(["search", "owner:x", "--page-size", "50"])
        self.assertEqual(args.command, "search")
        self.assertEqual(args.query, "owner:x")
        self.assertEqual(args.page_size, 50)
        self.assertEqual(args.func, st.cmd_search)

    def test_dossier_subcommand_requires_story_dir(self):
        with self.assertRaises(SystemExit):
            st.build_parser().parse_args(["dossier", "--out", "/tmp/out"])

    def test_dossier_subcommand_ids_optional(self):
        args = st.build_parser().parse_args(
            ["dossier", "101", "102", "--story-dir", "/tmp/in", "--out", "/tmp/out"]
        )
        self.assertEqual(args.ids, ["101", "102"])
        self.assertEqual(args.func, st.cmd_dossier)

    def test_batch_subcommand_defaults(self):
        args = st.build_parser().parse_args(["batch", "--in-dir", "/tmp/in", "--out", "/tmp/out"])
        self.assertEqual(args.prefix, "batch")
        self.assertEqual(args.target_chars, 120000)

    def test_consensus_subcommand_mode_default(self):
        args = st.build_parser().parse_args(["consensus", "--verdicts", "a.json", "b.json"])
        self.assertEqual(args.mode, "vote")
        self.assertEqual(args.verdicts, ["a.json", "b.json"])

    def test_consensus_subcommand_median_mode(self):
        args = st.build_parser().parse_args(
            ["consensus", "--verdicts", "a.json", "--mode", "median", "--field", "estimate_hours"]
        )
        self.assertEqual(args.mode, "median")
        self.assertEqual(args.field, "estimate_hours")

    def test_no_command_errors(self):
        with self.assertRaises(SystemExit):
            st.build_parser().parse_args([])


class TestCmdDossierIntegration(unittest.TestCase):
    """End-to-end over the CLI entry point, still fully offline."""

    def test_writes_one_json_per_ticket(self):
        with tempfile.TemporaryDirectory() as d:
            story_dir = os.path.join(d, "stories")
            refs_dir = os.path.join(d, "refs")
            out_dir = os.path.join(d, "out")
            os.makedirs(story_dir)
            os.makedirs(refs_dir)
            with open(os.path.join(story_dir, "101.json"), "w", encoding="utf-8") as f:
                json.dump(STORY, f)
            with open(os.path.join(refs_dir, "members.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "m1", "profile": {"mention_name": "alice"}}], f)
            with open(os.path.join(refs_dir, "epics.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "e1", "name": "Widgets"}], f)
            with open(os.path.join(refs_dir, "workflows.json"), "w", encoding="utf-8") as f:
                json.dump([{"name": "ENG", "states": [{"id": 500, "name": "To Do"}]}], f)
            with open(os.path.join(refs_dir, "custom-fields.json"), "w", encoding="utf-8") as f:
                json.dump([{"id": "f1", "name": "Skill Set", "values": [{"id": "v1", "value": "Frontend"}]}], f)

            rc = st.main(["dossier", "--story-dir", story_dir, "--refs", refs_dir, "--out", out_dir])
            self.assertEqual(rc, 0)
            out_path = os.path.join(out_dir, "101.json")
            self.assertTrue(os.path.isfile(out_path))
            with open(out_path, encoding="utf-8") as f:
                written = json.load(f)
            self.assertEqual(written["owners"], ["alice"])


if __name__ == "__main__":
    unittest.main()
