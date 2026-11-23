"""Exercise producing-attempt identity through the actual publication boundary."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from build_provenance import build_identity, publication_build, validate_build_identity
from release_books import ASSETS, publish

SOURCE = "a" * 40
ENV = {
    "GITHUB_ACTIONS": "true", "GITHUB_SHA": SOURCE,
    "GITHUB_REPOSITORY": "owner/repo", "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_RUN_ID": "45103974334", "GITHUB_RUN_NUMBER": "34", "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/books.yml@refs/heads/main",
    "GITHUB_WORKFLOW_SHA": SOURCE,
}


class BuildIdentity(unittest.TestCase):
    def test_local_build_has_no_invented_official_number(self):
        self.assertEqual(build_identity(SOURCE, {}), {"provider": "local"})
        validate_build_identity({"provider": "local"})

    def test_ci_build_and_rerun_share_run_but_not_attempt(self):
        original = build_identity(SOURCE, ENV)
        rerun = build_identity(SOURCE, ENV | {"GITHUB_RUN_ATTEMPT": "2"})
        self.assertEqual(original["run_id"], rerun["run_id"])
        self.assertEqual(original["run_number"], rerun["run_number"])
        self.assertEqual((original["run_attempt"], rerun["run_attempt"]), (1, 2))

    def test_incomplete_or_malformed_ci_context_fails_closed(self):
        for key in ENV:
            if key == "GITHUB_ACTIONS":
                continue
            with self.subTest(missing=key):
                env = ENV.copy()
                del env[key]
                with self.assertRaises(ValueError):
                    build_identity(SOURCE, env)
        for key, value in [("GITHUB_RUN_ATTEMPT", "0"), ("GITHUB_RUN_NUMBER", "-1"),
                           ("GITHUB_RUN_ID", "123/bad"), ("GITHUB_SHA", "b" * 40),
                           ("GITHUB_SERVER_URL", "https://github.com?other"),
                           ("GITHUB_WORKFLOW_REF", "other/repo/.github/workflows/books.yml@refs/heads/main")]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                build_identity(SOURCE, ENV | {key: value})

    def test_publish_retry_preserves_original_producing_identity(self):
        producer = build_identity(SOURCE, ENV)
        before = copy.deepcopy(producer)
        link = publication_build(producer, "owner/repo", SOURCE, ENV | {"GITHUB_RUN_ATTEMPT": "3"})
        self.assertIn("Build 34 (attempt 1)", link)
        self.assertTrue(link.endswith("/attempts/1)"))
        self.assertEqual(producer, before)

    def test_wrong_run_repository_workflow_or_future_attempt_cannot_publish(self):
        original = build_identity(SOURCE, ENV)
        for updates in [{"GITHUB_RUN_ID": "99"}, {"GITHUB_RUN_NUMBER": "35"},
                        {"GITHUB_REPOSITORY": "other/repo"},
                        {"GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/other.yml@refs/heads/main"},
                        {"GITHUB_WORKFLOW_SHA": "b" * 40}, {}]:
            producer = original if updates else original | {"run_attempt": 2}
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                publication_build(producer, "owner/repo", SOURCE, ENV | updates)
        with self.assertRaisesRegex(ValueError, "another repository"):
            publication_build(original, "other/repo", SOURCE, ENV)

    def test_local_build_or_local_publisher_cannot_claim_official_publication(self):
        for producer, env in [({"provider": "local"}, ENV), (build_identity(SOURCE, ENV), {})]:
            with self.subTest(producer=producer), self.assertRaisesRegex(ValueError, "requires a GitHub"):
                publication_build(producer, "owner/repo", SOURCE, env)


class PublicationProvenance(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        support = self.folder / "Supporting files"
        support.mkdir()
        (support / "release-plan.json").write_text(json.dumps({"sha": SOURCE, "version": "2026.11.2"}))
        for name in ASSETS:
            (self.folder / name).write_text("verified " + name)
        self.notes = []

    def manifest(self, build):
        (self.folder / "edition.json").write_text(json.dumps({"source_commit": SOURCE, "version": "2026.11.2", "build": build}))
        (self.folder / "SHA256SUMS").write_text("".join(
            f"{hashlib.sha256((self.folder / name).read_bytes()).hexdigest()}  {name}\n"
            for name in ASSETS if name != "SHA256SUMS"))

    def api(self, path, method="GET", payload=None):
        if path.endswith("branches/main"):
            return {"commit": {"sha": SOURCE}}
        if path.endswith("releases") and method == "POST":
            self.assertTrue(payload["draft"])
            self.assertEqual(payload["name"], "Wisdom — 2026.11.2")
            self.notes.append(payload["body"])
            return {"id": 123}
        if path.endswith("releases/123") and method == "PATCH":
            self.notes.append(payload["body"])
            return {"id": 123}
        if "matching-refs" in path:
            return [{"ref": "refs/tags/v2026.11.2", "object": {"type": "commit", "sha": SOURCE}}]
        if path.endswith("releases/tags/v2026.11.2"):
            return {"draft": False, "assets": [{"name": name} for name in ASSETS], "html_url": "https://github.com/owner/repo/releases/tag/v2026.11.2"}
        if path.endswith("releases/latest"):
            return {"tag_name": "v2026.11.2"}
        self.fail((path, method, payload))

    def gh(self, *args):
        if args[:2] == ("release", "download"):
            for name in ASSETS:
                shutil.copyfile(self.folder / name, self.folder / "Supporting files/published-assets" / name)

    def run_publish(self, *, attempt="1", existing=None):
        with patch.dict(os.environ, ENV | {"GITHUB_RUN_ATTEMPT": attempt}, clear=True), \
                patch("release_books.api", side_effect=self.api), \
                patch("release_books.gh", side_effect=self.gh), \
                patch("release_books.releases", return_value=existing or []):
            publish("owner/repo", self.folder)

    def test_complete_publish_retry_keeps_original_metadata_and_public_edition(self):
        self.manifest(build_identity(SOURCE, ENV))
        before = (self.folder / "edition.json").read_bytes()
        self.run_publish(attempt="2")
        self.assertIn("Build 34 (attempt 1)", self.notes[0])
        self.assertNotIn("Build 34 (attempt 2)", self.notes[0])
        self.assertEqual((self.folder / "edition.json").read_bytes(), before)
        self.assertEqual((self.folder / "Supporting files/published-assets/edition.json").read_bytes(), before)

    def test_rebuilt_draft_notes_follow_new_producing_attempt(self):
        self.manifest(build_identity(SOURCE, ENV | {"GITHUB_RUN_ATTEMPT": "2"}))
        self.run_publish(attempt="2", existing=[{"id": 123, "tag_name": "v2026.11.2", "target_commitish": SOURCE, "draft": True}])
        self.assertIn("Build 34 (attempt 2)", self.notes[0])

    def test_wrong_producer_stops_before_any_release_write(self):
        self.manifest(build_identity(SOURCE, ENV | {"GITHUB_RUN_ID": "99"}))
        with patch.dict(os.environ, ENV, clear=True), patch("release_books.api", side_effect=self.api) as api, \
                patch("release_books.gh") as gh, patch("release_books.releases", return_value=[]):
            with self.assertRaisesRegex(ValueError, "this publishing workflow"):
                publish("owner/repo", self.folder)
            self.assertTrue(all(len(call.args) == 1 for call in api.call_args_list))
            gh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
