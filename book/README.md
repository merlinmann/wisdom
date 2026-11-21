# Building the Books

Prepared by Codex for Merlin Mann

`wisdom.md` remains the manuscript. GitHub Actions produces five reading formats from the same source commit: EPUB3, a 6 × 9-inch PDF, offline HTML, Kindle AZW3, and image-free Markdown. JSON and SQLite provide the same visible manuscript as structured data. All seven preserve the visible manuscript text. The PDF and HTML use Source Serif 4; the EPUB and AZW3 preserve reader font controls. The Markdown retains headings, emphasis, links, and image captions as text, without HTML layout or embedded images, and begins with YAML edition metadata.

## Publication

A pull request that changes the manuscript, its images, or the book tooling receives a read-only build with downloadable review artifacts. A push of those changes to `main` builds and publishes a GitHub Release. README-only changes do not create editions. The Actions “Run workflow” button provides a manual retry.

A local save does not publish the book. Publication starts when the relevant changes reach GitHub.

## Versions

Versions follow the year-and-sequence approach demonstrated for this project. The first November 2026 edition is `2026.11`; another edition that November becomes `2026.12`. Within a year, the next sequence is the larger of the current month and the previous sequence plus one. A new year starts a new sequence. Versions are calculated from the source commit date in America/Los_Angeles.

Tags have a `v` prefix and identify exact source commits. Existing tags and draft releases reserve their numbers. A retry reuses the same draft; a published source commit produces no new edition. Newer source commits prevent older builds from replacing the latest edition. Published assets are never overwritten by this workflow. GitHub release immutability is enabled, so published assets and their source tags are protected from replacement.

## Files and Verification

The EPUB and PDF place a dedicated copyright page immediately after the authored title page, followed by contents and epigraphs. The HTML, AZW3, and Markdown carry the same copyright text near the beginning. The page includes the official CC BY-NC 4.0 badge (omitted with all other images in Markdown), linked license terms, the publisher, and an automatically filled edition number and date. `book/copyright.html` supplies the shared text; the version and America/Los_Angeles source date are the same values recorded in `edition.json`. Retries retain that date instead of using the rebuild time.

The PDF adapts the approved copyright-page layout to the book’s Source Serif 4 type, with small caps, restrained italics, and generous space above. Title and copyright pages have no running header or visible page number; the title starts the interior page count. The EPUB marks these pages as `titlepage` and `copyright-page` front matter, keeps the copyright page in its own reading-order document, and preserves reader font controls. The original licensing section remains at the end of the manuscript.

Every release contains `wisdom.epub`, `wisdom.pdf`, `wisdom.html`, `wisdom.azw3`, `wisdom.md`, `wisdom.json`, `wisdom.sqlite`, `edition.json`, and `SHA256SUMS`. Consistent filenames support stable latest-download URLs; each release also supplies permanent version-specific URLs. The HTML embeds all images, fonts, and styles in one file and needs no internet connection to read. The [data format guide](data-formats.md) describes JSON, SQLite, full-text search, YAML fields, and the scope of record IDs.

For wireless delivery to Kindle, upload the EPUB through [Send to Kindle](https://www.amazon.com/sendtokindle). The AZW3 is for USB transfer or [Calibre](https://calibre-ebook.com/); it is not a Send to Kindle upload format. Amazon documents its supported upload formats and current Mac USB-transfer options in [Kindle file transfers](https://digprjsurvey.amazon.com/csad/help/node/TCUBEdEkbIhK07ysFu).

The build runs EPUBCheck, verifies source passages in all seven formats (including text extracted from the finished AZW3), checks PDF text bounds and bookmarks, and rebuilds all seven files to compare their bytes. It also checks copyright placement, edition/date consistency, image-free Markdown, YAML metadata, and self-contained HTML assets. An independent reader compares every SQLite section, entry, link, and metadata value with JSON, checks database integrity and references, and exercises full-text search. Rendered PDF pages, narrow/wide EPUB and HTML screenshots, and an extracted Kindle-page preview are retained with the Actions artifact. Browser previews do not replace device-specific reading-system tests.

GitHub artifact attestations identify the workflow and source that produced the books. Verify a downloaded EPUB with:

```sh
gh attestation verify wisdom.epub --repo merlinmann/wisdom
```

After downloading all release files, verify their checksums with:

```sh
shasum -a 256 -c SHA256SUMS
```

## Build Inputs

- `book/metadata.json`: shared title, author, and publication metadata. Dates and edition identifiers are generated per source commit.
- `book/copyright.html`: shared copyright-page text and release metadata placeholders.
- `book/epub.css`: reflowable ebook styling, without fixed text colors or embedded fonts.
- `book/print.css`: page design and embedded PDF fonts.
- `book/html.css`: offline browser-edition layout and embedded fonts.
- `book/text-only.lua`: removes images while retaining readable text and captions for Markdown.
- `book/requirements.txt`: pinned Python dependencies.
- `scripts/build_books.py`: conversion and deterministic ZIP metadata.
- `scripts/convert_kindle_book.py`: Calibre conversion with edition-derived IDs and timestamps for reproducible AZW3 output.
- `scripts/validate_books.py`: content checks and review renders.
- `scripts/data_books.py`: structured JSON, SQLite, and YAML metadata.
- `scripts/validate_data_books.py`: independent data-file and search checks.
- `scripts/release_books.py`: version allocation and verified publication.
- `.github/workflows/books.yml`: remote execution with separate read-only build and write-enabled publication jobs.

Pandoc 3.14 and EPUBCheck 5.4.0 downloads are checked against pinned SHA-256 digests. Calibre 9.18.0 uses its official Linux binary with a pinned SHA-512 digest. GitHub actions are pinned to full commit SHAs. Builds use Python 3.12.12 on Ubuntu 24.04. The workflow checks byte-for-byte reproducibility within that environment; future operating-system updates may change rendering, so the recorded source and tool versions remain part of each edition’s provenance.

Generated books and supporting files live in the ignored `builds/ebooks/` directory. Releases hold the public downloads; generated books are not committed to the source branch.

## Font Source

Source Serif 4, release 4.005R, comes from Adobe’s [source-serif repository](https://github.com/adobe-fonts/source-serif/tree/2823e993c53fca27c5c8749f529b56a5a7c77b6b), under the accompanying [SIL Open Font License](fonts/LICENSE.md). The PDF embeds subsets of the supplied fonts. The HTML embeds the fonts and includes their license in its source. The existing private font setup is separate from this public build.

## Existing Links and Earlier Work

`main` is the default authoring and release branch. The former `master` branch preserves earlier public paths. After a successful book build, GitHub Actions copies the current maintained files to `master` without removing historical files or copying workflows. This keeps `wisdom.limo`, old Markdown links, image URLs, and historical downloads available. Work on `main`; `master` is maintained by the compatibility job.

The [pre-cleanup archive](https://github.com/merlinmann/wisdom/tree/archive/pre-cleanup-2026-11-20) preserves the former tree and its history. The old site experiments, typography demos, side works, and sync tests are outside the current working branch. Private local build files are preserved in the private Wisdom project store.

The compatibility job is idempotent, refuses stale source commits, and uses a non-forced update with the existing `master` commit as its parent. The publication job waits for it to succeed. The old branch does not publish editions.
