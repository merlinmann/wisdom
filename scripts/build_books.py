#!/usr/bin/env python3
"""Build both books from the same Markdown, date, version, and source commit."""
import argparse
import base64
import hashlib
import html
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from string import Template
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BOOK_FILES = ("wisdom.epub", "wisdom.pdf", "wisdom.html", "wisdom.azw3", "wisdom.md")


def data_uri(path):
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{media_type};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def offline_html(content, metadata, day):
    """Embed the project's images, fonts, and CSS; no network is needed to read it."""
    def image(match):
        path = (ROOT / html.unescape(match[1])).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"Offline HTML requires a repository image: {match[1]}")
        return 'src="' + data_uri(path) + '"'
    content = re.sub(r'src="([^"]+)"', image, content)
    css = (ROOT / "book/html.css").read_text()
    css = re.sub(r'url\("([^"]+)"\)', lambda match: 'url("' + data_uri(ROOT / "book" / match[1]) + '")', css)
    font_license = html.escape((ROOT / "book/fonts/LICENSE.md").read_text(), quote=True)
    return f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(metadata['title'])}</title><meta name="author" content="{html.escape(metadata['author'])}">
<meta name="dcterms.date" content="{day}"><style>{css}</style>
<meta name="embedded-font-license" content="{font_license}">
</head><body><main>{content}</main></body></html>'''


def copyright_page(metadata, version, day, *, print_edition):
    """One text template; edition and date come from the release's own metadata."""
    date = datetime.strptime(day, "%Y-%m-%d")
    fields = {"title": metadata["title"], "author": metadata["author"],
              "version": version, "iso_date": day,
              "display_date": f"{date:%B} {date.day}, {date.year}"}
    fields = {key: html.escape(value) for key, value in fields.items()}
    fields["type_credit"] = "Set in Source Serif 4.<br />" if print_edition else ""
    return Template((ROOT / "book/copyright.html").read_text()).substitute(fields)


def split_front_matter(source):
    """Keep the authored title text together, ahead of the copyright and epigraphs."""
    first_section = re.search(r"^## Epigraphs\s*$", source, re.M)
    assert first_section, "Expected Epigraphs as the first manuscript section"
    title, rest = source[:first_section.start()], source[first_section.start():]
    assert not re.search(r"^## ", title, re.M), "A new front-matter section needs placement review"
    # The title's closing rule is a web separator, not part of the printed title page.
    title = re.sub(r"\n-{3,}\s*\Z", "\n", title)
    assert len(re.findall(r"^# .+$", title, re.M)) == 1, "The manuscript needs its title heading"
    return title, rest


def command(*args, **kwargs):
    return subprocess.check_output(args, cwd=ROOT, text=True, **kwargs)


def normalized_zip(path, epoch):
    """Fix ZIP metadata, ordering, and timestamps while retaining the EPUB mimetype rule."""
    with zipfile.ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    # Pandoc puts the visible contents ahead of the authored title by default.
    # Keep the title/copyright pair together, then show the contents.
    opf_path = "EPUB/content.opf"
    opf_ns = "http://www.idpf.org/2007/opf"
    ns = {"o": opf_ns}
    opf = ET.fromstring(files[opf_path])
    items = opf.findall("o:manifest/o:item", ns)
    nav_id = next(item.get("id") for item in items if "nav" in item.get("properties", "").split())
    copyright_id = next(item.get("id") for item in items
                        if item.get("media-type") == "application/xhtml+xml"
                        and b'epub:type="copyright-page"' in files["EPUB/" + item.get("href")])
    spine = opf.find("o:spine", ns)
    nav_ref = next(item for item in spine if item.get("idref") == nav_id)
    spine.remove(nav_ref)
    position = next(i for i, item in enumerate(spine) if item.get("idref") == copyright_id)
    spine.insert(position + 1, nav_ref)
    ET.register_namespace("", opf_ns)
    ET.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
    files[opf_path] = ET.tostring(opf, encoding="utf-8", xml_declaration=True)
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
    title_source, rest = split_front_matter(source)
    title_html = command("pandoc", "--from=markdown", "--to=html5", "--strip-comments", "--wrap=none", input=title_source)
    body = command("pandoc", "--from=markdown", "--to=html5", "--section-divs", "--strip-comments", "--wrap=none", input=rest)
    headings = re.findall(r'<h2[^>]*id="([^"]+)"[^>]*>(.*?)</h2>', body, re.S)
    if not headings:
        headings = re.findall(r'<section id="([^"]+)" class="level2">\s*<h2[^>]*>(.*?)</h2>', body, re.S)
    assert headings, "The manuscript needs section headings for navigation"
    toc = '<section class="contents"><h1>Contents</h1><ol>' + ''.join(f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in headings) + '</ol></section>'
    colophon = f'''<section class="edition" id="edition"><h2>About This Edition</h2>
<p>Merlin’s Wisdom Project<br />Merlin Mann</p>
<p>Edition {version}<br />{day}</p>
<p>Published editions: <a href="https://github.com/merlinmann/wisdom/releases">github.com/merlinmann/wisdom/releases</a></p>
<p>Source: <a href="https://github.com/merlinmann/wisdom/commit/{sha}"><code>{sha}</code></a></p>
<p>Copyright Merlin Mann.</p></section>'''
    (support / "colophon.html").write_text(colophon)
    copyright_print = copyright_page(metadata, version, day, print_edition=True)
    copyright_epub = copyright_page(metadata, version, day, print_edition=False)
    (support / "copyright.html").write_text(copyright_print)
    pdf_body = f'<section class="title-page">{title_html}</section><section class="copyright-page" id="copyright-page" aria-label="Copyright">{copyright_print}</section>{toc}{body}'
    pdf_html = f'''<!doctype html><html lang="en-US"><head><meta charset="utf-8">
<title>{html.escape(metadata['title'])}</title><meta name="author" content="Merlin Mann">
<meta name="dcterms.created" content="{utc.isoformat()}"><meta name="dcterms.modified" content="{utc.isoformat()}">
</head><body><div class="cover"><img src="i/cover.jpg" alt="Cover of Merlin’s Wisdom Project"></div>{pdf_body}{colophon}</body></html>'''
    (support / "book.html").write_text(pdf_html)

    epub_manuscript = support / "manuscript-epub.md"
    epub_title = re.sub(r"^(# .+)$", r'\1 {epub:type=titlepage}', title_source, count=1, flags=re.M)
    epub_manuscript.write_text(epub_title + '\n\n## Copyright {#copyright-page .copyright-page epub:type=copyright-page}\n\n```{=html}\n' + copyright_epub + '\n```\n\n' + rest + "\n\n" + colophon + "\n")
    command("pandoc", str(epub_manuscript), "--from=markdown", "--to=epub3", "--standalone", "--strip-comments",
            f"--metadata-file={metadata_path}", "--epub-title-page=false", "--epub-cover-image=i/cover.jpg",
            "--css=book/epub.css", "--toc", "--toc-depth=2", "--split-level=2", "--resource-path=.",
            f"--output={output / 'wisdom.epub'}")
    normalized_zip(output / "wisdom.epub", epoch)
    web_body = f'<div class="cover"><img src="i/cover.jpg" alt="Cover of Merlin’s Wisdom Project"></div>{pdf_body}{colophon}'
    (output / "wisdom.html").write_text(offline_html(web_body, metadata, day))
    markdown = command("pandoc", "--from=html", "--to=gfm-raw_html", "--wrap=none",
                       "--lua-filter=book/text-only.lua", input=web_body.replace(copyright_print, copyright_epub))
    (output / "wisdom.md").write_text(markdown)
    command("calibre-debug", "-e", "scripts/convert_kindle_book.py", "--",
            str(output / "wisdom.epub"), str(output / "wisdom.azw3"), str(epoch),
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    # Read the completed Kindle file back into browser-viewable pages for checks.
    command("ebook-convert", str(output / "wisdom.azw3"), str(support / "kindle-preview"),
            "--disable-font-rescaling", "--chapter", "/", "--page-breaks-before", "/",
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"})
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    fonts = FontConfiguration()
    stylesheet = CSS(filename=ROOT / "book/print.css", font_config=fonts)
    HTML(string=pdf_html, base_url=str(ROOT) + "/").write_pdf(output / "wisdom.pdf", stylesheets=[stylesheet], font_config=fonts)
    manifest = {
        "title": metadata["title"], "version": version, "source_commit": sha, "source_date": day,
        "source_date_epoch": epoch, "source_sha256": hashlib.sha256((ROOT / "wisdom.md").read_bytes()).hexdigest(),
        "pandoc": command("pandoc", "--version").splitlines()[0],
        "weasyprint": command("python", "-m", "weasyprint", "--version").strip(),
        "calibre": command("ebook-convert", "--version").strip(),
        "files": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in BOOK_FILES},
    }
    (output / "edition.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    names = [*BOOK_FILES, "edition.json"]
    (output / "SHA256SUMS").write_text(''.join(f"{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n" for name in names))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "builds/ebooks")
    args = parser.parse_args()
    build(args.version, args.output.resolve())
