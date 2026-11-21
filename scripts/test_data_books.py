"""Check structural preservation, cross-references, and portable data files."""
import json
import copy
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from data_books import dataset, export, write_sqlite, yaml_metadata
from validate_books import canonical
from validate_data_books import validate_source_structure


@unittest.skipUnless(shutil.which("pandoc"), "Pandoc is installed before building books")
class DataEditionTests(unittest.TestCase):
    def test_separator_anchors_and_list_validation(self):
        source = '''<h1 id="book">Book</h1><ul><li>One.</li><li>Two.</li><li>One.</li></ul>
<hr id="old-point" /><p>See <a href="#old-point">the old point</a>.</p>
<span class="Z3988" title="bibliography"></span>'''
        with tempfile.TemporaryDirectory() as folder:
            data = export(source, {"identifier": "edition:test", "source_commit": "a" * 40}, Path(folder))
            separator = next(row for row in data["entries"] if "old-point" in row["source_anchors"])
            self.assertEqual(separator["kind"], "separator")
            link = next(link for row in data["entries"] for link in row["links"] if link["url"] == "#old-point")
            self.assertEqual(link["target_id"], separator["id"])
            result = validate_source_structure(data, source, canonical)
            self.assertEqual(result["source_list_items_checked"], 3)
            self.assertEqual(result["data_nonprinting_metadata_records"], 1)
            for mutation in ("drop", "reorder", "replace"):
                broken = copy.deepcopy(data)
                items = [row for row in broken["entries"] if row["kind"] == "list_item"]
                if mutation == "drop":
                    broken["entries"].remove(items[-1])
                elif mutation == "reorder":
                    items[0]["markdown"], items[1]["markdown"] = items[1]["markdown"], items[0]["markdown"]
                else:
                    items[2]["markdown"] = items[1]["markdown"]
                with self.subTest(mutation=mutation), self.assertRaisesRegex(AssertionError, "Data list"):
                    validate_source_structure(broken, source, canonical)
            broken = copy.deepcopy(data)
            next(row for row in broken["entries"] if "old-point" in row["source_anchors"])["source_anchors"] = []
            with self.assertRaisesRegex(AssertionError, "separator anchor"):
                validate_source_structure(broken, source, canonical)

    def test_footnote_stays_with_its_citation(self):
        source = '''# Book

<div class="csl-entry" id="dante">

Dante's line.[^lowell]

</div>

The final paragraph is separate.

[^lowell]: Learned through Lowell. See [the book](#book).
'''
        html = subprocess.check_output(["pandoc", "--from=markdown", "--to=html5"], input=source, text=True)
        doc = json.loads(subprocess.check_output(["pandoc", "--from=html", "--to=json"], input=html, text=True))
        data = dataset(doc, {"identifier": "edition:test", "source_commit": "a" * 40})
        citation = next(row for row in data["entries"] if "dante" in row["source_anchors"])
        final = next(row for row in data["entries"] if row["text"].startswith("The final"))
        self.assertIn("Learned through Lowell", citation["text"])
        self.assertIn("Learned through Lowell", citation["markdown"])
        self.assertNotIn("Lowell", final["text"])
        self.assertNotIn("Lowell", final["markdown"])
        self.assertEqual(citation["links"][0]["target_id"], data["sections"][0]["id"])
        self.assertEqual(validate_source_structure(data, html, canonical)["citation_footnotes_checked"], 1)
        broken = copy.deepcopy(data)
        next(row for row in broken["entries"] if "dante" in row["source_anchors"])["text"] = "Dante's line."
        with self.assertRaisesRegex(AssertionError, "footnote moved"):
            validate_source_structure(broken, html, canonical)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "book.sqlite"
            write_sqlite(data, path)
            with sqlite3.connect(path) as db:
                hits = db.execute("SELECT id FROM entries_fts WHERE entries_fts MATCH 'Lowell'").fetchall()
                self.assertEqual(hits, [(citation["id"],)])

    def test_structure_references_search_and_determinism(self):
        source = '''<section id="book"><h1>The Book</h1><section id="advice"><h2>Advice</h2>
<ul><li>Drink a glass of <em>water</em>.<ul><li>Related: be kind.</li></ul></li><li>Drink a glass of <em>water</em>.</li></ul>
<p>Read <a href="#citation">the source</a>.</p><img src="i/cover.jpg" alt="A cover">
</section><section id="sources"><h2>Sources</h2><div id="citation" class="csl-entry">Author. <em>A Book</em>.</div></section></section>'''
        doc = json.loads(subprocess.check_output(["pandoc", "--from=html", "--to=json"], input=source, text=True))
        metadata = {"identifier": "urn:wisdom.limo:edition:2026.15", "source_commit": "a" * 40}
        data = dataset(doc, metadata)
        items = [row for row in data["entries"] if row["kind"] == "list_item"]
        self.assertEqual(len(items), 3)
        self.assertEqual(items[1]["parent_id"], items[0]["id"])
        self.assertEqual(items[0]["text"], items[2]["text"])
        self.assertNotEqual(items[0]["id"], items[2]["id"])
        self.assertIn("*water*", items[0]["markdown"])
        self.assertNotIn("Related", items[0]["text"])
        citation = next(row for row in data["entries"] if row["kind"] == "citation")
        links = [link for row in data["entries"] for link in row["links"]]
        self.assertEqual(next(link for link in links if link["url"] == "#citation")["target_id"], citation["id"])
        self.assertEqual(next(link for link in links if link["kind"] == "image")["url"], f"https://raw.githubusercontent.com/merlinmann/wisdom/{'a' * 40}/i/cover.jpg")
        self.assertEqual(data, dataset(doc, metadata))
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / "a.sqlite", Path(folder) / "b.sqlite"
            write_sqlite(data, a)
            write_sqlite(data, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with sqlite3.connect(a) as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
                hits = db.execute("SELECT id FROM entries_fts WHERE entries_fts MATCH ?", ('"glass of water"',)).fetchall()
                self.assertEqual({row[0] for row in hits}, {items[0]["id"], items[2]["id"]})

    def test_yaml_preserves_ambiguous_values(self):
        values = {"title": 'A: "Book"\nNext', "date": "2026-11-20", "edition": "2026.15", "author": "Merlin Mann"}
        front = yaml_metadata(values)
        parsed = json.loads(subprocess.check_output(["pandoc", "--from=markdown+yaml_metadata_block", "--to=json"], input=front + "Text.\n", text=True))
        self.assertEqual(parsed["meta"]["edition"]["c"], [{"t": "Str", "c": "2026.15"}])
        self.assertEqual(parsed["blocks"], [{"t": "Para", "c": [{"t": "Str", "c": "Text."}]}])


if __name__ == "__main__":
    unittest.main()
