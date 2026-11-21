"""Read both finished data files independently and compare their public records."""
import json
from collections import Counter
from html.parser import HTMLParser
import re
import sqlite3
import subprocess


def ast_nodes(value):
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in value.values():
            yield from ast_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from ast_nodes(child)


def semantic_text(value, include_notes=False):
    if isinstance(value, dict):
        kind = value.get("t")
        if kind == "Note":
            return semantic_text(value["c"], True) if include_notes else ""
        if kind == "Str":
            return value["c"]
        if kind in ("Code", "CodeBlock", "Math"):
            return value["c"][-1]
        return " ".join(semantic_text(child, include_notes) for child in value.values())
    if isinstance(value, list):
        return " ".join(semantic_text(child, include_notes) for child in value)
    return ""


def source_list_items(value):
    if isinstance(value, dict):
        kind = value.get("t")
        if kind == "Note":
            return
        if kind in ("BulletList", "OrderedList"):
            items = value["c"] if kind == "BulletList" else value["c"][1]
            for item in items:
                yield [block for block in item if block["t"] not in ("BulletList", "OrderedList")]
                yield from source_list_items(item)
        else:
            for child in value.values():
                yield from source_list_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from source_list_items(child)


def validate_source_structure(data, source_html, canonical):
    source = json.loads(subprocess.check_output(["pandoc", "--from=html", "--to=json"], input=source_html, text=True))
    expected = [canonical(semantic_text(item)) for item in source_list_items(source["blocks"])]
    items = [entry for entry in data["entries"] if entry["kind"] == "list_item"]
    marker = "WISDOMLISTVALIDATIONBOUNDARY68AA81"
    assert all(marker not in entry["markdown"] for entry in items)
    markdown = "".join(f"\n\n{marker}\n\n{entry['markdown']}\n" for entry in items)
    actual_ast = json.loads(subprocess.check_output(["pandoc", "--from=gfm", "--to=json"], input=markdown, text=True))
    groups = []
    for block in actual_ast["blocks"]:
        if block == {"t": "Para", "c": [{"t": "Str", "c": marker}]}:
            groups.append([])
        else:
            assert groups, "List validation encountered content before its first record"
            groups[-1].append(block)
    actual = [canonical(semantic_text(group)) for group in groups]
    assert len(actual) == len(expected), f"Data list count differs: {len(actual)} != {len(expected)}"
    assert actual == expected, "Data list order, text, or repeated-item count differs from the source"

    footnotes = 0
    for node in ast_nodes(source["blocks"]):
        if node["t"] != "Div" or not node["c"][0][0] or "csl-entry" not in node["c"][0][1]:
            continue
        notes = [canonical(semantic_text(note["c"])) for note in ast_nodes(node) if note["t"] == "Note"]
        if notes:
            owners = [entry for entry in data["entries"] if node["c"][0][0] in entry["source_anchors"]]
            assert len(owners) == 1, "Citation footnote has no unique data owner"
            assert all(note in canonical(owners[0]["text"]) for note in notes), "Citation footnote moved to another record"
            footnotes += len(notes)
    def note_occurrences(value, owner=""):
        if isinstance(value, dict):
            if value.get("t") in ("Para", "Plain", "Header"):
                owner = canonical(semantic_text(value))
            if value.get("t") == "Note":
                yield owner, canonical(semantic_text(value["c"], True))
                return
            for child in value.values():
                yield from note_occurrences(child, owner)
        elif isinstance(value, list):
            for child in value:
                yield from note_occurrences(child, owner)

    expected_notes = Counter(note_occurrences(source["blocks"]))
    actual_notes = Counter()
    for entry in [*data["sections"], *data["entries"]]:
        references = set(re.findall(r"\[\^([^\]]+)\](?!:)", entry["markdown"]))
        definitions = re.findall(r"(?m)^\[\^([^\]]+)\]:", entry["markdown"])
        assert references == set(definitions), "A data record has an orphan footnote reference or definition"
        assert len(definitions) == len(set(definitions)), "A data record duplicates a footnote definition"
        if references:
            parsed = json.loads(subprocess.check_output(["pandoc", "--from=gfm", "--to=json"], input=entry["markdown"], text=True))
            actual_notes.update(note_occurrences(parsed["blocks"]))
    assert actual_notes == expected_notes, "Data footnote ownership or occurrence count differs from the source"
    source_text = canonical(semantic_text(source["blocks"], True))
    exported_text = " ".join(canonical(row["text"]) for row in [*data["sections"], *data["entries"]])
    for note in {text for _, text in expected_notes if text}:
        assert exported_text.count(note) == source_text.count(note), "Data plain text duplicates or omits a footnote"

    class Rules(HTMLParser):
        def __init__(self):
            super().__init__()
            self.anchors = set()
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "hr" and attrs.get("id"):
                self.anchors.add(attrs["id"])
    rules = Rules()
    rules.feed(source_html)
    anchors = {anchor for row in [*data["sections"], *data["entries"]] for anchor in row["source_anchors"]}
    assert rules.anchors <= anchors, "Data editions lost an authored separator anchor"

    metadata_spans = sum(node["t"] == "Span" and "Z3988" in node["c"][0][1] and not node["c"][1]
                         for node in ast_nodes(source["blocks"]))
    empty = [entry for entry in data["entries"] if not entry["text"]]
    assert len(empty) == metadata_spans and all(entry["kind"] == "paragraph" for entry in empty), "Unexpected empty data record"
    return {"source_list_items_checked": len(expected), "data_list_order_and_multiplicity_verified": True,
            "citation_footnotes_checked": footnotes, "separator_anchors_preserved": len(rules.anchors),
            "data_nonprinting_metadata_records": len(empty)}


def validate_data(folder, edition, canonical, source_units):
    data = json.loads((folder / "wisdom.json").read_text())
    assert data["schema_version"] == 1
    metadata = data["metadata"]
    assert metadata["source_commit"] == edition["source_commit"]
    assert metadata["edition"] == edition["version"] and metadata["date"] == edition["source_date"]
    records = sorted([*data["sections"], *data["entries"]], key=lambda row: row["position"])
    identifiers = {row["id"] for row in records}
    assert len(identifiers) == len(records), "Data IDs must be unique"
    assert [row["position"] for row in records] == list(range(1, len(records) + 1))
    assert all(row["id"].startswith(metadata["identifier"] + ":") for row in records)
    text = canonical("\n".join(row["text"] for row in records))
    assert all(unit in text for unit in source_units), "Data editions omitted manuscript text"
    header = (folder / "wisdom.md").read_text().split("---\n", 2)
    assert len(header) == 3 and not header[0], "Markdown needs YAML metadata"
    yaml_values = {key: json.loads(value.strip()) for key, value in (line.split(":", 1) for line in header[1].splitlines())}
    assert yaml_values == metadata, "Markdown metadata differs from data editions"
    with sqlite3.connect(f"{(folder / 'wisdom.sqlite').resolve().as_uri()}?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        assert db.execute("PRAGMA user_version").fetchone() == (1,)
        assert {key: json.loads(value) for key, value in db.execute("SELECT key, value_json FROM metadata")} == {"schema_version": 1, **metadata}
        for table in ("sections", "entries"):
            db.row_factory = sqlite3.Row
            rows = list(db.execute(f"SELECT * FROM {table} ORDER BY position"))
            assert len(rows) == len(data[table]), f"SQLite {table} count differs"
            for actual, expected in zip(rows, data[table]):
                actual = dict(actual)
                actual["source_anchors"] = json.loads(actual.pop("source_anchors_json"))
                assert actual == {key: value for key, value in expected.items() if key != "links"}
        db.row_factory = None
        expected_links = [(entry["id"], position, link["kind"], link["url"], link["title"], link["target_id"])
                          for entry in data["entries"] for position, link in enumerate(entry["links"], 1)]
        assert sorted(db.execute("SELECT * FROM links")) == sorted(expected_links)
        assert all(link[-1] is None or link[-1] in identifiers for link in expected_links)
        assert dict(db.execute("SELECT id, text FROM entries_fts")) == {row["id"]: row["text"] for row in data["entries"]}
        assert db.execute("SELECT count(*) FROM entries_fts WHERE entries_fts MATCH ?", ('"glass of water"',)).fetchone()[0] > 0
        assert db.execute("SELECT count(*) FROM entries_fts WHERE entries_fts MATCH ?", ("wisdomzzznosuchword",)).fetchone()[0] == 0
    structure = validate_source_structure(data, (folder / "Supporting files/source.html").read_text(), canonical)
    return {**structure, "json_content_preserved": True, "sqlite_content_preserved": True,
            "data_sections": len(data["sections"]), "data_entries": len(data["entries"]),
            "data_list_items": sum(row["kind"] == "list_item" for row in data["entries"]),
            "sqlite_integrity": "ok", "sqlite_search_verified": True, "markdown_yaml_verified": True}
