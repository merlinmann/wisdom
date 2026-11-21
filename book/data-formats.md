# The Wisdom Project as Data

Prepared by Codex for Merlin Mann

`wisdom.json` and `wisdom.sqlite` contain the visible manuscript from the same source commit as the reading editions. They preserve reading order, headings, authored text, emphasis in Markdown, list nesting where present, citations, source anchors, and links. They exclude hidden manuscript comments and generated contents/copyright pages; publication and rights information is carried in their metadata. Image references point to the exact source commit. The data files contain image references rather than image bytes.

## JSON

The root object has `schema_version`, `metadata`, `sections`, and `entries`. Schema version 1 uses these records:

| Field | Meaning |
| --- | --- |
| `id` | Unique identifier within this edition, shared by JSON and SQLite |
| `position` | One-based reading order across both sections and entries |
| `parent_id` | Parent section, or parent list entry when the source actually nests a list |
| `source_anchors` | Existing manuscript anchors, retained for citation and navigation |
| `text` | Plain text for display and search |
| `markdown` | Text with authored emphasis and links |
| `level` | Section heading level; sections only |
| `section_id` | Containing section; entries only |
| `kind` | Entry type: `paragraph`, `list_item`, `quotation`, `citation`, `figure`, or `separator` |
| `links` | Entry links and image references, with `kind`, `url`, `title`, and optional resolved `target_id` |

Sort combined sections and entries by `position` to reconstruct reading order. Filter `entries` by a section ID and `kind == "list_item"` to retrieve its authored bullets. Labels such as “Related” remain in the text; they do not create inferred relationships. Internal fragment links retain their original URL and include a `target_id` pointing to the exported section or entry.

Footnotes belong to the record containing their reference; their text and Markdown definition travel with that record. Anchors on horizontal rules are retained on `separator` records. The image-free Markdown edition maps those internal links to the containing heading because it does not retain HTML anchor markup. Empty paragraph records correspond to the source’s nonprinting bibliography metadata; separators and those existing positions remain in the data. Applications displaying prose can skip records whose `text` is empty.

## SQLite

The database uses `metadata`, `sections`, `entries`, and `links` tables, with an FTS5 `entries_fts` search index. `metadata.value_json` contains a JSON scalar. `source_anchors_json` contains a JSON array. The remaining record fields use ordinary columns; entry links are rows in `links`, ordered by their per-entry `position`. The SQLite `user_version` equals the JSON schema version.

Search for an exact phrase:

```sql
SELECT e.id, e.text
FROM entries_fts AS f
JOIN entries AS e ON e.id = f.id
WHERE entries_fts MATCH '"glass of water"'
ORDER BY rank;
```

Read the main section's bullets in order:

```sql
SELECT e.id, e.text
FROM entries AS e
JOIN sections AS s ON s.id = e.section_id
WHERE s.text = 'The Wisdom So Far' AND e.kind = 'list_item'
ORDER BY e.position;
```

The files use SQLite's documented [portable application format](https://www.sqlite.org/appfileformat.html) and [FTS5 search](https://www.sqlite.org/fts5.html). They need no running server. The bundled search index reflects the published snapshot; an application that edits its own copy must maintain or rebuild that index.

## Metadata and IDs

The Markdown download begins with YAML containing the title, author, language, edition, date, identifier, license, rights statement, project URL, source commit, source URL, and `id_scope`. JSON and SQLite carry the same values. Values are quoted so dates and edition numbers retain their intended strings.

Record IDs currently take the form `urn:wisdom.limo:edition:2026.15:entry:49`. They identify a record in one immutable edition. They are deterministic within that edition and distinguish repeated identical text. They are not permanent identities across edits or editions; applications must retain the full ID and edition, rather than treating the trailing number as permanent. Merlin's request to consider durable cross-edition IDs remains a separate design question. Existing public URLs and manuscript anchors are unchanged.

The original text uses CC BY-NC 4.0. Third-party material retains its own rights; the metadata carries that qualification. These data exports do not change the license.
