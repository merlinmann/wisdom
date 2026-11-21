# Building the Books

Prepared by Codex for Merlin Mann

`wisdom.md` remains the manuscript. GitHub Actions produces an EPUB3 and a 6 × 9-inch PDF from the same source commit. The existing cover and all visible manuscript text are retained. The PDF uses Source Serif 4; the EPUB respects reader font and size preferences.

## Publication

A push that changes the manuscript, its images, or the book tooling runs the Books workflow. Branch builds produce downloadable review artifacts. A successful build on `master` publishes a GitHub Release. Pull requests from forks receive read-only builds. README-only changes do not create editions. The Actions “Run workflow” button provides a manual retry.

A local save does not publish the book. Publication starts when the relevant changes reach GitHub.

## Versions

Versions follow the year-and-sequence approach demonstrated for this project. The first November 2026 edition is `2026.11`; another edition that November becomes `2026.12`. Within a year, the next sequence is the larger of the current month and the previous sequence plus one. A new year starts a new sequence. Versions are calculated from the source commit date in America/Los_Angeles.

Tags have a `v` prefix and identify exact source commits. Existing tags and draft releases reserve their numbers. A retry reuses the same draft; a published source commit produces no new edition. Newer source commits prevent older builds from replacing the latest edition. Published assets are never overwritten by this workflow.

## Files and Verification

Every release contains `wisdom.epub`, `wisdom.pdf`, `edition.json`, and `SHA256SUMS`. Consistent filenames support stable latest-download URLs; each release also supplies permanent version-specific URLs.

The build runs EPUBCheck, verifies that source passages appear in both formats, checks PDF text bounds and bookmarks, and rebuilds both books to compare their bytes. Rendered PDF pages and narrow/wide EPUB chapter screenshots are retained with the Actions artifact for review. These browser screenshots check EPUB layout; they do not replace device-specific reading-system tests.

GitHub artifact attestations identify the workflow and source that produced the books. Verify a downloaded EPUB with:

```sh
gh attestation verify wisdom.epub --repo merlinmann/wisdom
```

After downloading all four release files, verify their checksums with:

```sh
shasum -a 256 -c SHA256SUMS
```

## Build Inputs

- `book/metadata.json`: shared title, author, and publication metadata. Dates and edition identifiers are generated per source commit.
- `book/epub.css`: reflowable ebook styling, without fixed text colors or embedded fonts.
- `book/print.css`: page design and embedded PDF fonts.
- `book/requirements.txt`: pinned Python dependencies.
- `scripts/build_books.py`: conversion and deterministic ZIP metadata.
- `scripts/validate_books.py`: content checks and review renders.
- `scripts/release_books.py`: version allocation and verified publication.
- `.github/workflows/books.yml`: remote execution with separate read-only build and write-enabled publication jobs.

Pandoc 3.14 and EPUBCheck 5.4.0 downloads are checked against pinned SHA-256 digests. GitHub actions are pinned to full commit SHAs. Builds use Python 3.12.12 on Ubuntu 24.04. The workflow checks byte-for-byte reproducibility within that environment; future operating-system updates may change rendering, so the recorded source and tool versions remain part of each edition’s provenance.

Generated books and supporting files live in the ignored `builds/ebooks/` directory. Releases hold the public downloads; generated books are not committed to the source branch.

## Font Source

Source Serif 4, release 4.005R, comes from Adobe’s [source-serif repository](https://github.com/adobe-fonts/source-serif/tree/2823e993c53fca27c5c8749f529b56a5a7c77b6b), under the accompanying [SIL Open Font License](fonts/LICENSE.md). The PDF embeds subsets of the supplied fonts. The existing private font setup is separate from this public build.
