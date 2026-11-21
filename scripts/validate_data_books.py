"""Read both finished data files independently and compare their public records."""
import json
import sqlite3


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
    return {"json_content_preserved": True, "sqlite_content_preserved": True,
            "data_sections": len(data["sections"]), "data_entries": len(data["entries"]),
            "data_list_items": sum(row["kind"] == "list_item" for row in data["entries"]),
            "sqlite_integrity": "ok", "sqlite_search_verified": True, "markdown_yaml_verified": True}
