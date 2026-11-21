"""Export the visible manuscript as JSON and a searchable SQLite document."""
import copy
import json
from pathlib import Path
import sqlite3
import subprocess
from urllib.parse import urljoin


def nodes(value):
    if isinstance(value, dict):
        if "t" in value:
            yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def pandoc(document, writer):
    return subprocess.check_output(["pandoc", "--from=json", f"--to={writer}", "--wrap=none"],
                                   input=json.dumps(document), text=True)


def render_units(document, units, writer):
    # Markers delimit whole blocks, so punctuation and authored newlines survive.
    marker = "WISDOMEXPORTBOUNDARY8DB6F82DB702"
    assert marker not in json.dumps(document), "Export separator occurs in manuscript"
    blocks = []
    for unit in units:
        blocks.append({"t": "Para", "c": [{"t": "Str", "c": marker}]})
        blocks.extend(unit)
    rendered = pandoc({**document, "meta": {}, "blocks": blocks}, writer).split(marker)
    assert len(rendered) == len(units) + 1
    return [part.strip() for part in rendered[1:]]


def dataset(document, metadata):
    document = copy.deepcopy(document)
    base = f"https://raw.githubusercontent.com/merlinmann/wisdom/{metadata['source_commit']}/"
    for node in nodes(document["blocks"]):
        if node["t"] in ("Link", "Image"):
            url = node["c"][-1][0]
            if url and not url.startswith("#"):
                node["c"][-1][0] = urljoin(base, url.lstrip("/") if url.startswith("/i/") else url)
    result = {"schema_version": 1, "metadata": metadata, "sections": [], "entries": []}
    sections, entries, stack, units = result["sections"], result["entries"], [], []
    sequence = 0

    def add(blocks, kind, parent_id=None, anchors=()):
        nonlocal sequence
        sequence += 1
        record = {"id": f"{metadata['identifier']}:entry:{len(entries) + 1}",
                  "position": sequence, "section_id": stack[-1][1] if stack else None,
                  "parent_id": parent_id, "kind": kind, "source_anchors": list(anchors), "links": []}
        for node in nodes(blocks):
            if node["t"] in ("Link", "Image"):
                record["links"].append({"kind": node["t"].lower(), "url": node["c"][-1][0],
                                        "title": node["c"][-1][1]})
            elif node["t"] in ("Span", "Div") and node["c"][0][0]:
                if node["c"][0][0] not in record["source_anchors"]:
                    record["source_anchors"].append(node["c"][0][0])
        entries.append(record)
        units.append((record, blocks))
        return record["id"]

    def walk(blocks, parent_id=None, anchors=()):
        nonlocal sequence
        pending = list(anchors)
        for block in blocks:
            kind, value = block["t"], block.get("c")
            if kind == "Div":
                attrs, children = value
                ids = [*pending, *([attrs[0]] if attrs[0] else [])]
                if "csl-entry" in attrs[1]:
                    add([block], "citation", parent_id, ids)
                else:
                    walk(children, parent_id, ids)
            elif kind == "Header":
                level, attrs, title = value
                while stack and stack[-1][0] >= level:
                    stack.pop()
                sequence += 1
                record = {"id": f"{metadata['identifier']}:section:{len(sections) + 1}",
                          "position": sequence, "level": level, "parent_id": stack[-1][1] if stack else None,
                          "source_anchors": list(dict.fromkeys([*pending, *([attrs[0]] if attrs[0] else [])]))}
                sections.append(record)
                units.append((record, [{"t": "Plain", "c": title}]))
                stack.append((level, record["id"]))
            elif kind in ("BulletList", "OrderedList"):
                items = value if kind == "BulletList" else value[1]
                for item in items:
                    own = [b for b in item if b["t"] not in ("BulletList", "OrderedList")]
                    nested = [b for b in item if b["t"] in ("BulletList", "OrderedList")]
                    identifier = add(own, "list_item", parent_id, pending)
                    walk(nested, identifier)
                    pending = []
            else:
                add([block], {"BlockQuote": "quotation", "Figure": "figure", "HorizontalRule": "separator"}.get(kind, "paragraph"), parent_id, pending)
            pending = []

    walk(document["blocks"])
    blocks = [blocks for _, blocks in units]
    for (record, _), text, markdown in zip(units, render_units(document, blocks, "plain"), render_units(document, blocks, "gfm-raw_html")):
        record.update(text=text, markdown=markdown)
    targets = {anchor: record["id"] for record in [*sections, *entries] for anchor in record["source_anchors"]}
    for entry in entries:
        for link in entry["links"]:
            link["target_id"] = targets.get(link["url"][1:]) if link["url"].startswith("#") else None
            assert not link["url"].startswith("#") or link["target_id"], f"Unresolved data link: {link['url']}"
    return result


def write_sqlite(data, path):
    path = Path(path)
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA user_version=1")
        db.executescript('''
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE sections (id TEXT PRIMARY KEY, position INTEGER NOT NULL UNIQUE, level INTEGER NOT NULL,
                parent_id TEXT REFERENCES sections(id), text TEXT NOT NULL, markdown TEXT NOT NULL, source_anchors_json TEXT NOT NULL);
            CREATE TABLE entries (id TEXT PRIMARY KEY, position INTEGER NOT NULL UNIQUE,
                section_id TEXT REFERENCES sections(id), parent_id TEXT REFERENCES entries(id), kind TEXT NOT NULL,
                text TEXT NOT NULL, markdown TEXT NOT NULL, source_anchors_json TEXT NOT NULL);
            CREATE TABLE links (entry_id TEXT NOT NULL REFERENCES entries(id), position INTEGER NOT NULL,
                kind TEXT NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL, target_id TEXT,
                PRIMARY KEY(entry_id, position));
            CREATE INDEX entries_section ON entries(section_id, position);
            CREATE INDEX entries_parent ON entries(parent_id);
            CREATE VIRTUAL TABLE entries_fts USING fts5(id UNINDEXED, text, tokenize='unicode61');
        ''')
        for key, value in sorted({"schema_version": data["schema_version"], **data["metadata"]}.items()):
            db.execute("INSERT INTO metadata VALUES (?, ?)", (key, json.dumps(value, ensure_ascii=False)))
        for row in data["sections"]:
            db.execute("INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (row["id"], row["position"], row["level"], row["parent_id"], row["text"], row["markdown"], json.dumps(row["source_anchors"])))
        for row in data["entries"]:
            db.execute("INSERT INTO entries VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (row["id"], row["position"], row["section_id"], row["parent_id"], row["kind"], row["text"], row["markdown"], json.dumps(row["source_anchors"])))
            db.execute("INSERT INTO entries_fts(id, text) VALUES (?, ?)", (row["id"], row["text"]))
            for number, link in enumerate(row["links"], 1):
                db.execute("INSERT INTO links VALUES (?, ?, ?, ?, ?, ?)",
                           (row["id"], number, link["kind"], link["url"], link["title"], link["target_id"]))
        db.execute("INSERT INTO entries_fts(entries_fts) VALUES ('optimize')")
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not db.execute("PRAGMA foreign_key_check").fetchall()


def export(source_html, metadata, output):
    document = json.loads(subprocess.check_output(["pandoc", "--from=html", "--to=json"], input=source_html, text=True))
    data = dataset(document, metadata)
    (output / "wisdom.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write_sqlite(data, output / "wisdom.sqlite")
    return data


def yaml_metadata(metadata):
    """JSON scalar notation is also valid YAML and quotes every ambiguous value."""
    return "---\n" + "".join(f"{key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in metadata.items()) + "---\n\n"
