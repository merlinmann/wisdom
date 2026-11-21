"""Exercise edition numbering boundaries and repeat publication decisions."""
from datetime import date
import unittest
from release_books import choose_version


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


if __name__ == "__main__":
    unittest.main()
