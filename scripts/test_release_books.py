"""Exercise edition numbering boundaries and repeat publication decisions."""
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from release_books import book_inputs, choose_version, publish, unchanged_since_publication


class Editions(unittest.TestCase):
    def test_first_edition_aligns_with_month(self):
        self.assertEqual(choose_version([], [], "a", date(2026, 11, 20)), ("2026.11", False))

    def test_second_edition_same_month_advances(self):
        self.assertEqual(choose_version([], ["v2026.11"], "b", date(2026, 11, 20)), ("2026.12", False))

    def test_can_skip_forward_but_never_backward(self):
        self.assertEqual(choose_version([], ["v2026.2"], "b", date(2026, 11, 20)), ("2026.11", False))
        self.assertEqual(choose_version([], ["v2026.20"], "b", date(2026, 11, 20)), ("2026.21", False))

    def test_new_year_resets_sequence(self):
        self.assertEqual(choose_version([], ["v2026.99"], "b", date(2027, 1, 2)), ("2027.1", False))

    def test_published_commit_is_reused(self):
        releases = [{"tag_name": "v2026.11", "target_commitish": "a", "draft": False}]
        self.assertEqual(choose_version(releases, ["v2026.11"], "a", date(2026, 12, 1)), ("2026.11", True))

    def test_interrupted_draft_keeps_its_number(self):
        releases = [{"tag_name": "v2026.11", "target_commitish": "a", "draft": True}]
        self.assertEqual(choose_version(releases, ["v2026.11"], "a", date(2026, 12, 1)), ("2026.11", False))


class BatchDecisions(unittest.TestCase):
    def tree(self, manuscript="text", extra=()):
        return {"tree": [{"path": "wisdom.md", "mode": "100644", "type": "blob", "sha": manuscript}, *extra]}

    @patch("release_books.api")
    def test_documentation_only_and_reverted_edits_do_not_rebuild(self, api):
        doc = {"path": "book/README.md", "mode": "100644", "type": "blob", "sha": "docs"}
        api.side_effect = [self.tree(), self.tree(extra=[doc])]
        self.assertEqual(book_inputs("owner/repo", "published"), book_inputs("owner/repo", "new-commit"))

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
            {"tag_name": "v2026.13", "target_commitish": "old", "draft": False},
            {"tag_name": "v2026.16", "target_commitish": "draft", "draft": True},
            {"tag_name": "v2026.15", "target_commitish": "latest", "draft": False},
            {"tag_name": "v2026.17", "target_commitish": "preview", "draft": False, "prerelease": True},
        ]
        self.assertTrue(unchanged_since_publication("owner/repo", "current", items))
        self.assertEqual([call.args[1] for call in inputs.call_args_list], ["current", "latest"])
        inputs.reset_mock()
        self.assertFalse(unchanged_since_publication("owner/repo", "first", []))
        inputs.assert_not_called()


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
