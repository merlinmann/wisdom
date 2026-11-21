# Building the Books

Prepared by Codex for Merlin Mann

`wisdom.md` remains the manuscript. GitHub Actions produces five reading formats from the same source commit: EPUB3, a 6 × 9-inch PDF, offline HTML, Kindle AZW3, and image-free Markdown. JSON and SQLite provide the same visible manuscript as structured data. All seven preserve the visible manuscript text. The PDF and HTML use Source Serif 4; the EPUB and AZW3 preserve reader font controls. The Markdown retains headings, emphasis, links, and image captions as text, without HTML layout or embedded images, and begins with YAML edition metadata. The downloadable Markdown uses a UTF-8 signature so download previews recognize its curly quotes, accented letters, and copyright symbols.

## Publication

A pull request or push receives quick structure, link, and publication-rule checks. These checks install only Pandoc; they do not build ebooks, install Calibre, render pages, or produce release artifacts. Successful pushes also update the compatibility branch, keeping the online manuscript and old links current.

Downloadable editions are batched once daily, at approximately **5:17 a.m. Pacific**, using GitHub’s timezone-aware schedule. The job compares the actual book inputs against the last published edition before installing conversion tools. No changed inputs means no rebuild and no new edition. README, data-guide, test, quick-check, and compatibility-helper changes alone do not count; a changed manuscript, image, design file, conversion tool, or format validator does. An edit followed by a complete revert also leaves the published inputs unchanged.

For an urgent edition, choose **Actions → Publish Books → Run workflow** on `main`. This uses the same change detection and full verification as the daily run. A repeated request with unchanged inputs does not create another edition. Full builds run only from `main`, and publication runs do not overlap.

For a complete review without a new release, uncheck **Publish the verified edition** in that same form. This explicitly requested run builds and validates all seven formats even if the inputs are unchanged, retains the review files as an Actions artifact, and cannot publish them or update the compatibility branch. Reviews use separate concurrency groups, so they cannot displace a waiting publication. Routine edits do not request this extra work.

A local save remains an unpublished draft and syncs between Macs. Committing and pushing makes the online manuscript current; the downloadable books wait for the next daily batch or Publish Books request. GitHub may delay scheduled runs, so the time is approximate. Published editions keep their existing immutable URLs and files.

If GitHub disables the schedule after 60 days without repository activity, the next successful checks on a push resume it. An intentionally disabled schedule is left disabled.

## Versions

Versions follow the year-and-sequence approach demonstrated for this project. The first November 2026 edition is `2026.11`; another edition that November becomes `2026.12`. Within a year, the next sequence is the larger of the current month and the previous sequence plus one. A new year starts a new sequence. Versions are calculated from the source commit date in America/Los_Angeles.

Tags have a `v` prefix and identify exact source commits. Existing tags and draft releases reserve their numbers. A retry reuses the same draft; a published source commit produces no new edition. Newer source commits prevent older builds from replacing the latest edition. Published assets are never overwritten by this workflow. GitHub release immutability is enabled, so published assets and their source tags are protected from replacement.

A small planning job reads publication metadata with the repository permission required to see unpublished drafts. It performs no repository or release writes. The plan and version then pass to a separate build job with read-only repository permissions. Third-party conversion tools never receive a write-enabled token. A superseded draft remains preserved and reserves its number, so the next source commit can receive a new number without colliding with it. Published editions must name an immutable source commit; a moving branch name is rejected before comparison.

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
- `.github/workflows/checks.yml`: quick checks for edits and compatibility updates for existing reading links.
- `.github/workflows/books.yml`: daily or manually requested editions, with separate metadata planning, read-only conversion, compatibility, and publication jobs.

Pandoc 3.14 and EPUBCheck 5.4.0 downloads are checked against pinned SHA-256 digests. Calibre 9.18.0 uses its official Linux binary with a pinned SHA-512 digest. GitHub actions are pinned to full commit SHAs. Builds use Python 3.12.12 on Ubuntu 24.04. The workflow checks byte-for-byte reproducibility within that environment; future operating-system updates may change rendering, so the recorded source and tool versions remain part of each edition’s provenance.

Generated books and supporting files live in the ignored `builds/ebooks/` directory. Releases hold the public downloads; generated books are not committed to the source branch.

## Font Source

Source Serif 4, release 4.005R, comes from Adobe’s [source-serif repository](https://github.com/adobe-fonts/source-serif/tree/2823e993c53fca27c5c8749f529b56a5a7c77b6b), under the accompanying [SIL Open Font License](fonts/LICENSE.md). The PDF embeds subsets of the supplied fonts. The HTML embeds the fonts and includes their license in its source. The existing private font setup is separate from this public build.

## Existing Links and Earlier Work

`main` is the default authoring and release branch. The former `master` branch preserves earlier public paths. After successful quick checks on a push, GitHub Actions copies the current maintained files to `master` without removing historical files or copying workflows. The publication workflow also verifies compatibility before releasing an edition. This keeps `wisdom.limo`, old Markdown links, image URLs, and historical downloads available. Work on `main`; `master` is maintained by the compatibility job.

The [pre-cleanup archive](https://github.com/merlinmann/wisdom/tree/archive/pre-cleanup-2026-11-20) preserves the former tree and its history. The old site experiments, typography demos, side works, and sync tests are outside the current working branch. Private local build files are preserved in the private Wisdom project store.

The compatibility job is idempotent, refuses stale source commits, and uses a non-forced update with the existing `master` commit as its parent. The publication job waits for it to succeed. A no-change daily run and a review-only run do not invoke compatibility; ordinary pushes reach it only after quick checks pass. The old branch does not publish editions.
