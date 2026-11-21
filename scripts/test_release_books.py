"""Exercise edition numbering boundaries and repeat publication decisions."""
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from release_books import choose_version, publish


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


class PublicationSafety(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        support = self.folder / "Supporting files"
        support.mkdir()
        (support / "release-plan.json").write_text(json.dumps({"sha": "source", "version": "2026.11"}))
        (self.folder / "edition.json").write_text(json.dumps({"source_commit": "source", "version": "2026.11"}))

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
