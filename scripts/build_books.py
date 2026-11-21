#!/usr/bin/env python3
"""Build both books from the same Markdown, date, version, and source commit."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


def command(*args, **kwargs):
    return subprocess.check_output(args, cwd=ROOT, text=True, **kwargs)


def normalized_zip(path, epoch):
    """Fix ZIP metadata, ordering, and timestamps while retaining the EPUB mimetype rule."""
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    stamp = time.gmtime(max(epoch, 315532800))[:6]
    with zipfile.ZipFile(path, "w") as archive:
        for name in ["mimetype", *sorted(set(files) - {"mimetype"})]:
            info = zipfile.ZipInfo(name, stamp)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name], compresslevel=9)


def build(version, output):
    if not re.fullmatch(r"20\d{2}\.[1-9]\d*", version):
        raise ValueError("Expected a year-and-sequence version such as 2026.11")
    output.mkdir(parents=True, exist_ok=True)
    support = output / "Supporting files"
    support.mkdir(exist_ok=True)
    sha = command("git", "rev-parse", "HEAD").strip()
    epoch = int(command("git", "show", "-s", "--format=%ct", "HEAD"))
    os.environ["SOURCE_DATE_EPOCH"] = str(epoch)
    utc = datetime.fromtimestamp(epoch, timezone.utc)
    day = utc.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
    metadata = json.loads((ROOT / "book/metadata.json").read_text())
    metadata.update(date=day, identifier=f"urn:wisdom.limo:edition:{version}")
    metadata_path = support / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")

    # The cover becomes each format's cover, rather than appearing twice in the book.
    source = (ROOT / "wisdom.md").read_text()
    assert source.count("![Your Author](/i/cover.jpg)") == 1
    source = source.replace("![Your Author](/i/cover.jpg)", "")
    source = re.sub(r"(?<=\()/i/", "i/", source)
    manuscript = support / "manuscript.md"
    manuscript.write_text(source)
    body = command("pandoc", str(manuscript), "--from=markdown", "--to=html5", "--section-divs", "--strip-comments", "--wrap=none")
    (support / "source.html").write_text(body)
    headings = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', body, re.S)
    if not headings:
        headings = re.findall(r'<section id="([^"]+)" class="level2">\s*<h2[^>]*>(.*?)</h2>', body, re.S)
    assert len(headings) == 5, f"Unexpected chapter count: {len(headings)}"
    toc = '<section class="contents"><h1>Contents</h1><ol>' + ''.join(f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in headings) + '</ol></section>'
    colophon = f'''<section class="edition" id="edition"><h2>About This Edition</h2>
<p>Merlin’s Wisdom Project<br>Merlin Mann</p>
<p>Edition {version}<br>{day}</p>
<p>Published editions: <a href="https://github.com/merlinmann/wisdom/releases">github.com/merlinmann/wisdom/releases</a></p>
<p>Source: <a href="https://github.com/merlinmann/wisdom/commit/{sha}"><code>{sha}</code></a></p>
<p>Copyright Merlin Mann.</p></section>'''
    (support / "colophon.html").write_text(colophon)
    pdf_body = body.replace('<section id="epigraphs"', toc + '<section id="epigraphs"', 1)
    assert pdf_body != body
    pdf_html = f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8">
<title>{html.escape(metadata['title'])}</title><meta name="author" content="Merlin Mann">
<meta name="dcterms.created" content="{utc.isoformat()}"><meta name="dcterms.modified" content="{utc.isoformat()}">
</head><body><div class="cover"><img src="i/cover.jpg" alt="Cover of Merlin’s Wisdom Project"></div>{pdf_body}{colophon}</body></html>'''
    (support / "book.html").write_text(pdf_html)

    command("pandoc", str(manuscript), "--from=markdown", "--to=epub3", "--standalone", "--strip-comments",
            f"--metadata-file={metadata_path}", "--epub-title-page=false", "--epub-cover-image=i/cover.jpg",
            "--css=book/epub.css", "--toc", "--toc-depth=2", "--split-level=2", "--resource-path=.",
            f"--include-after-body={support / 'colophon.html'}", f"--output={output / 'wisdom.epub'}")
    normalized_zip(output / "wisdom.epub", epoch)
    from weasyprint import HTML, CSS
    HTML(string=pdf_html, base_url=str(ROOT) + "/").write_pdf(output / "wisdom.pdf", stylesheets=[CSS(filename=ROOT / "book/print.css")])
    manifest = {
        "title": metadata["title"], "version": version, "source_commit": sha, "source_date": day,
        "source_date_epoch": epoch, "source_sha256": hashlib.sha256((ROOT / "wisdom.md").read_bytes()).hexdigest(),
        "pandoc": command("pandoc", "--version").splitlines()[0],
        "weasyprint": command("python", "-m", "weasyprint", "--version").strip(),
        "files": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ("wisdom.epub", "wisdom.pdf")},
    }
    (output / "edition.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    names = ["wisdom.epub", "wisdom.pdf", "edition.json"]
    (output / "SHA256SUMS").write_text(''.join(f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n" for name in names))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "builds/ebooks")
    args = parser.parse_args()
    build(args.version, args.output.resolve())
