"""Verify URL preservation, retries, and stale-source handling."""
import unittest
from unittest.mock import patch
from sync_legacy import sync, updates


def entry(path, sha):
    return {"path": path, "mode": "100644", "type": "blob", "sha": sha}


class Compatibility(unittest.TestCase):
    def test_historical_files_are_preserved_and_workflows_are_excluded(self):
        old = {p: entry(p, "old") for p in ("wisdom.md", "quotes.md", ".github/workflows/books.yml")}
        new = {p: entry(p, "new") for p in ("wisdom.md", ".github/workflows/books.yml")}
        changed = updates(new, old)
        self.assertEqual(changed, [entry("wisdom.md", "new")])
        merged = old | {x["path"]: x for x in changed}
        self.assertEqual(merged["quotes.md"], old["quotes.md"])
        self.assertEqual(merged[".github/workflows/books.yml"], old[".github/workflows/books.yml"])

    @patch("sync_legacy.api", return_value={"object": {"sha": "newer"}})
    def test_stale_source_never_writes(self, api):
        sync("owner/repo", "source")
        self.assertEqual(api.call_count, 1)

    @patch("sync_legacy.read_tree", return_value={"wisdom.md": entry("wisdom.md", "same")})
    @patch("sync_legacy.api", return_value={"object": {"sha": "source"}})
    def test_retry_with_identical_files_never_writes(self, api, read_tree):
        sync("owner/repo", "source")
        self.assertTrue(all(len(call.args) == 1 for call in api.call_args_list))

    def test_complete_update_uses_parent_and_never_forces(self):
        source = {"wisdom.md": entry("wisdom.md", "new")}
        old = {"wisdom.md": entry("wisdom.md", "old"), "quotes.md": entry("quotes.md", "keep")}
        expected = old | source
        def fake(path, method="GET", payload=None):
            if path.endswith("ref/heads/main"): return {"object": {"sha": "source"}}
            if path.endswith("ref/heads/master"):
                return {"object": {"sha": "commit" if applied else "legacy"}}
            if path.endswith("git/commits/legacy"): return {"tree": {"sha": "base"}}
            if path.endswith("git/trees"):
                self.assertEqual(payload, {"base_tree": "base", "tree": list(source.values())})
                return {"sha": "tree"}
            if path.endswith("git/commits"):
                self.assertEqual(payload["parents"], ["legacy"])
                return {"sha": "commit"}
            if path.endswith("refs/heads/master"):
                self.assertEqual(payload, {"sha": "commit", "force": False})
                applied.append(True)
                return {}
            self.fail(path)
        applied = []
        with patch("sync_legacy.api", side_effect=fake), patch("sync_legacy.read_tree", side_effect=[source, old, expected, expected]):
            sync("owner/repo", "source")
        self.assertTrue(applied)


if __name__ == "__main__":
    unittest.main()
