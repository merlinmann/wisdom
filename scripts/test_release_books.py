"""Exercise edition numbering boundaries and repeat publication decisions."""
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from release_books import book_inputs, choose_version, plan, publish, resume_schedule, unchanged_since_publication


class Editions(unittest.TestCase):
    def test_first_edition_aligns_with_month(self):
        self.assertEqual(choose_version([], [], "a", date(2026, 11, 20)), ("2026.11.1", False))

    def test_second_edition_same_month_advances(self):
        self.assertEqual(choose_version([], ["v2026.11.1"], "b", date(2026, 11, 20)), ("2026.11.2", False))

    def test_legacy_numbers_do_not_consume_monthly_editions(self):
        self.assertEqual(choose_version([], ["v2026.11", "v2026.18"], "b", date(2026, 11, 20)), ("2026.11.1", False))

    def test_sequences_are_numeric_and_reserved_tags_are_skipped(self):
        self.assertEqual(choose_version([], ["v2026.11.9", "v2026.11.10"], "b", date(2026, 11, 20)), ("2026.11.11", False))

    def test_new_month_resets_sequence(self):
        self.assertEqual(choose_version([], ["v2026.11.10", "v2026.12"], "b", date(2026, 12, 1)), ("2026.12.1", False))

    def test_new_year_resets_sequence(self):
        self.assertEqual(choose_version([], ["v2026.99", "v2026.12.10"], "b", date(2027, 1, 2)), ("2027.1.1", False))

    def test_published_commit_is_reused(self):
        for version in ("2026.18", "2026.11.1"):
            releases = [{"tag_name": "v" + version, "target_commitish": "a", "draft": False}]
            self.assertEqual(choose_version(releases, [], "a", date(2026, 12, 1)), (version, True))

    def test_interrupted_draft_keeps_its_number(self):
        releases = [{"tag_name": "v2026.11.1", "target_commitish": "a", "draft": True}]
        self.assertEqual(choose_version(releases, [], "a", date(2026, 12, 1)), ("2026.11.1", False))


class BatchDecisions(unittest.TestCase):
    def tree(self, manuscript="text", extra=()):
        return {"tree": [{"path": "wisdom.md", "mode": "100644", "type": "blob", "sha": manuscript}, *extra]}

    @patch("release_books.api")
    def test_documentation_only_and_reverted_edits_do_not_rebuild(self, api):
        doc = {"path": "book/README.md", "mode": "100644", "type": "blob", "sha": "docs"}
        api.side_effect = [self.tree(), self.tree(extra=[doc])]
        self.assertEqual(book_inputs("owner/repo", "published"), book_inputs("owner/repo", "new-commit"))

    @patch("release_books.api")
    def test_check_and_sync_helpers_do_not_make_editions(self, api):
        for path in ("scripts/test_release_books.py", "scripts/check_book_links.py", "scripts/sync_legacy.py", ".github/workflows/checks.yml"):
            with self.subTest(path=path):
                item = {"path": path, "mode": "100644", "type": "blob", "sha": "changed"}
                api.side_effect = [self.tree(), self.tree(extra=[item])]
                self.assertEqual(book_inputs("owner/repo", "before"), book_inputs("owner/repo", "after"))

    @patch("release_books.api")
    def test_manuscript_asset_and_build_changes_require_a_release(self, api):
        for path in ("i/cover.jpg", "book/print.css", "scripts/build_books.py", ".github/workflows/books.yml"):
            with self.subTest(path=path):
                item = {"path": path, "mode": "100644", "type": "blob", "sha": "new"}
                api.side_effect = [self.tree(), self.tree(extra=[item])]
                self.assertNotEqual(book_inputs("owner/repo", "a"), book_inputs("owner/repo", "b"))
        api.side_effect = [self.tree("before"), self.tree("after")]
        self.assertNotEqual(book_inputs("owner/repo", "a"), book_inputs("owner/repo", "b"))

    @patch("release_books.api")
    def test_deleting_an_input_is_a_change(self, api):
        item = {"path": "i/old.jpg", "mode": "100644", "type": "blob", "sha": "old"}
        api.side_effect = [self.tree(extra=[item]), self.tree()]
        self.assertNotEqual(book_inputs("owner/repo", "before"), book_inputs("owner/repo", "after"))

    @patch("release_books.api")
    def test_incomplete_input_comparison_fails_before_a_build(self, api):
        for tree in ({"truncated": True, **self.tree()}, {"tree": []}):
            api.return_value = tree
            with self.assertRaises(RuntimeError):
                book_inputs("owner/repo", "commit")

    @patch("release_books.book_inputs", return_value="same-inputs")
    def test_compare_latest_published_edition_not_a_draft(self, inputs):
        items = [
            {"tag_name": "v2026.18", "target_commitish": "old", "draft": False, "published_at": "2026-11-22T20:00:00Z"},
            {"tag_name": "v2026.11.2", "target_commitish": "draft", "draft": True},
            {"tag_name": "v2026.11.1", "target_commitish": "a" * 40, "draft": False, "published_at": "2026-11-23T02:00:00Z"},
            {"tag_name": "v2026.11.3", "target_commitish": "preview", "draft": False, "prerelease": True},
        ]
        self.assertTrue(unchanged_since_publication("owner/repo", "current", items))
        self.assertEqual([call.args[1] for call in inputs.call_args_list], ["current", "a" * 40])
        inputs.reset_mock()
        self.assertFalse(unchanged_since_publication("owner/repo", "first", []))
        inputs.assert_not_called()

    @patch("release_books.book_inputs")
    def test_moving_release_target_cannot_silently_suppress_editions(self, inputs):
        items = [{"tag_name": "v2026.15", "target_commitish": "main", "draft": False, "published_at": "2026-11-21T00:00:00Z"}]
        with self.assertRaisesRegex(RuntimeError, "immutable source commit"):
            unchanged_since_publication("owner/repo", "current", items)
        inputs.assert_not_called()


class Planning(unittest.TestCase):
    def planned(self, items, *, unchanged=False, verify_only=False, now=None):
        with TemporaryDirectory() as folder:
            path, output = Path(folder) / "plan.json", Path(folder) / "outputs"
            with patch("release_books.subprocess.check_output", return_value="c" * 40), \
                    patch("release_books.datetime") as clock, \
                    patch("release_books.releases", return_value=items), \
                    patch("release_books.gh", return_value="[[]]"), \
                    patch("release_books.unchanged_since_publication", return_value=unchanged), \
                    patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}):
                clock.now.return_value = now or datetime(2026, 11, 23, 2, tzinfo=timezone.utc)
                plan("owner/repo", path, verify_only)
            return json.loads(path.read_text()), output.read_text()

    def test_untagged_old_draft_reserves_its_number_before_conversion(self):
        items = [{"tag_name": "v2026.11.1", "target_commitish": "a" * 40, "draft": False},
                 {"tag_name": "v2026.11.2", "target_commitish": "b" * 40, "draft": True}]
        result, output = self.planned(items)
        self.assertEqual(result["version"], "2026.11.3")
        self.assertTrue(result["build"])
        self.assertIn("version=2026.11.3\nbuild=true\n", output)

    def test_month_uses_publication_planning_time_in_pacific(self):
        before, _ = self.planned([], now=datetime(2026, 12, 1, 7, 59, tzinfo=timezone.utc))
        after, _ = self.planned([], now=datetime(2026, 12, 1, 8, tzinfo=timezone.utc))
        self.assertEqual(before["version"], "2026.11.1")
        self.assertEqual(after["version"], "2026.12.1")

    def test_same_source_untagged_draft_is_reused(self):
        result, _ = self.planned([{"tag_name": "v2026.16", "target_commitish": "c" * 40, "draft": True}])
        self.assertEqual(result["version"], "2026.16")
        self.assertTrue(result["build"])

    def test_unchanged_inputs_skip_the_entire_build(self):
        result, output = self.planned([], unchanged=True)
        self.assertFalse(result["build"])
        self.assertIn("build=false\n", output)

    def test_explicit_review_builds_even_an_already_published_source(self):
        result, output = self.planned([{"tag_name": "v2026.15", "target_commitish": "c" * 40, "draft": False}], verify_only=True)
        self.assertTrue(result["already_published"])
        self.assertTrue(result["build"])
        self.assertTrue(result["verify_only"])
        self.assertIn("build=true\n", output)


class ScheduleRecovery(unittest.TestCase):
    @patch("release_books.gh")
    @patch("release_books.api", side_effect=[{"state": "disabled_inactivity"}, {"state": "active"}])
    def test_only_inactivity_disables_are_resumed(self, api, gh):
        resume_schedule("owner/repo")
        gh.assert_called_once_with("api", "repos/owner/repo/actions/workflows/books.yml/enable", "--method", "PUT")
        self.assertEqual(api.call_count, 2)

    @patch("release_books.gh")
    @patch("release_books.api")
    def test_active_and_intentionally_disabled_schedules_are_preserved(self, api, gh):
        for state in ("active", "disabled_manually", "disabled_fork", "deleted"):
            api.return_value = {"state": state}
            resume_schedule("owner/repo")
        gh.assert_not_called()


class PublicationSafety(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        support = self.folder / "Supporting files"
        support.mkdir()
        (support / "release-plan.json").write_text(json.dumps({"sha": "source", "version": "2026.11"}))
        (self.folder / "edition.json").write_text(json.dumps({"source_commit": "source", "version": "2026.11"}))

    @patch("release_books.api")
    @patch("release_books.gh")
    def test_review_build_cannot_publish_even_if_called_directly(self, gh, api):
        path = self.folder / "Supporting files/release-plan.json"
        path.write_text(json.dumps({"sha": "source", "version": "2026.11", "verify_only": True}))
        with self.assertRaisesRegex(AssertionError, "review-only"):
            publish("owner/repo", self.folder)
        api.assert_not_called()
        gh.assert_not_called()

    @patch("release_books.gh")
    @patch("release_books.releases")
    @patch("release_books.api", return_value={"commit": {"sha": "newer"}})
    def test_stale_build_does_not_write_a_release(self, api, releases, gh):
        publish("owner/repo", self.folder)
        releases.assert_not_called()
        gh.assert_not_called()
        self.assertEqual(api.call_count, 1)

    @patch("release_books.gh")
    @patch("release_books.releases", return_value=[])
    @patch("release_books.api", return_value={"commit": {"sha": "source"}})
    def test_missing_books_cannot_create_a_draft(self, api, releases, gh):
        with self.assertRaises(AssertionError):
            publish("owner/repo", self.folder)
        gh.assert_not_called()
        self.assertEqual(api.call_count, 1)

    @patch("release_books.gh")
    @patch("release_books.releases", return_value=[{"tag_name": "v2026.11", "target_commitish": "source", "draft": False}])
    @patch("release_books.api", return_value={"commit": {"sha": "source"}})
    def test_published_edition_is_never_overwritten(self, api, releases, gh):
        publish("owner/repo", self.folder)
        gh.assert_not_called()
        self.assertEqual(api.call_count, 1)


if __name__ == "__main__":
    unittest.main()
