#!/usr/bin/env python3
"""Check source preservation and render evidence from the actual ebook files."""
import argparse
from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import posixpath
import re
import subprocess
import unicodedata
import zipfile
from xml.etree import ElementTree as ET


def canonical(text):
    return ''.join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.units = []
        self.active = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script"):
            self.ignored += 1
            return
        attrs = dict(attrs)
        if tag in ("p", "li", "h1", "h2") or (tag == "div" and attrs.get("class") == "csl-entry"):
            self.active.append([tag, []])

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.ignored -= 1
            return
        if self.active and self.active[-1][0] == tag:
            self.units.append(''.join(self.active.pop()[1]))

    def handle_data(self, value):
        if self.ignored:
            return
        self.text.append(value)
        for _, parts in self.active:
            parts.append(value)


def validate(folder):
    import pymupdf
    from PIL import Image, ImageDraw
    support = folder / "Supporting files"
    edition = json.loads((folder / "edition.json").read_text())
    day = date.fromisoformat(edition["source_date"])
    display_date = f"{day:%B} {day.day}, {day.year}"
    edition_label = f"Digital edition {edition['version']}"
    license_url = "https://creativecommons.org/licenses/by-nc/4.0/"
    source = Text()
    source.feed((support / "source.html").read_text())
    units = [canonical(x) for x in source.units if len(canonical(x)) > 3]
    with zipfile.ZipFile(folder / "wisdom.epub") as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        opf_path = next(container.iter("{urn:oasis:names:tc:opendocument:xmlns:container}rootfile")).attrib["full-path"]
        opf = ET.fromstring(archive.read(opf_path))
        ns = {"o": "http://www.idpf.org/2007/opf"}
        items = {x.attrib["id"]: x.attrib["href"] for x in opf.findall("o:manifest/o:item", ns)}
        spine = [items[x.attrib["idref"]] for x in opf.findall("o:spine/o:itemref", ns)]
        epub_text = []
        documents = []
        chapter = None
        longest = 0
        for item in spine:
            path = str(Path(opf_path).parent / item)
            body = archive.read(path).decode()
            reader = Text()
            reader.feed(body)
            epub_text.extend(reader.text)
            documents.append((path, ET.fromstring(body), canonical(' '.join(reader.text))))
            if len("".join(reader.text)) > longest:
                chapter, longest = path, len("".join(reader.text))
        epub = canonical(' '.join(epub_text))
        missing = [unit for unit in units if unit not in epub]
        assert not missing, f"EPUB omitted {len(missing)} source passages: {missing[:2]}"
        xhtml = "{http://www.w3.org/1999/xhtml}"
        epub_type = "{http://www.idpf.org/2007/ops}type"
        copyright_documents = [(i, path, root, text) for i, (path, root, text) in enumerate(documents)
                               if any("copyright-page" in node.get(epub_type, "").split() for node in root.iter())]
        assert len(copyright_documents) == 1, "EPUB needs exactly one copyright page"
        copyright_index, copyright_path, copyright_root, copyright_text = copyright_documents[0]
        assert copyright_index == 2, "EPUB must open with cover, title page, then copyright"
        assert any(node.get(epub_type) == "titlepage" for node in documents[1][1].iter()), "The preceding EPUB document must be the title page"
        assert copyright_root.find(xhtml + "body").get(epub_type) == "frontmatter", "Copyright is EPUB front matter"
        assert canonical(edition_label) in copyright_text, "EPUB edition differs from release"
        assert canonical(display_date) in copyright_text, "EPUB copyright date differs from release"
        assert any(node.get("href") == license_url for node in copyright_root.iter(xhtml + "a")), "EPUB license link missing"
        badge = next(node for node in copyright_root.iter(xhtml + "img") if "Creative Commons" in node.get("alt", ""))
        badge_path = posixpath.normpath(posixpath.join(posixpath.dirname(copyright_path), badge.get("src")))
        assert archive.read(badge_path).strip(), "The official CC badge must be embedded"
        assert any(node.get(epub_type) == "toc" for node in documents[3][1].iter()), "Contents must follow copyright"
        assert "epigraphs" in documents[4][2], "Epigraphs must follow the front matter"
        preview = support / "epub-preview"
        for item in archive.infolist():
            assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
        archive.extractall(preview)
        assert chapter
        (support / "epub-preview-path.txt").write_text(str((preview / chapter).resolve()))
        (support / "epub-copyright-path.txt").write_text(str((preview / copyright_path).resolve()))

    web = (folder / "wisdom.html").read_text()
    assert all(src.startswith("data:") for src in re.findall(r'src="([^"]+)"', web)), "HTML images must work offline"
    assert all(url.startswith("data:") for url in re.findall(r'url\("([^"]+)"\)', web)), "HTML fonts must work offline"
    web_reader = Text()
    web_reader.feed(web)
    web_text = canonical(' '.join(web_reader.text))
    assert all(unit in web_text for unit in units), "HTML omitted manuscript text"
    markdown = (folder / "wisdom.md").read_text()
    assert not re.search(r'!\[|<img\b|data:image/', markdown, re.I), "Markdown must not embed images"
    markdown_html = subprocess.check_output(["pandoc", str(folder / "wisdom.md"), "--from=gfm", "--to=html5"], text=True)
    markdown_reader = Text()
    markdown_reader.feed(markdown_html)
    markdown_text = canonical(' '.join(markdown_reader.text))
    assert all(unit in markdown_text for unit in units), "Image-free Markdown omitted manuscript text"
    assert not re.search(r'<(?:div|span|p|img|figure)\b', markdown), "Markdown must use Markdown rather than HTML layout"
    markdown_ids = set(re.findall(r'id="([^"]+)"', markdown_html))
    markdown_fragments = re.findall(r'href="#([^"]+)"', markdown_html)
    assert all(target in markdown_ids for target in markdown_fragments), "Markdown has broken internal links"
    def label_text(markup):
        reader = Text()
        reader.feed(markup)
        return canonical(' '.join(reader.text))
    markdown_headings = {identifier: label_text(label) for identifier, label in re.findall(
        r'<h[1-6]\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h[1-6]>', markdown_html, re.S)}
    for target, label in re.findall(r'<a\b[^>]*href="#([^"]+)"[^>]*>(.*?)</a>', markdown_html, re.S):
        label = label_text(label)
        if label in markdown_headings.values():
            assert markdown_headings.get(target) == label, "Markdown contents link reaches the wrong section"
    kindle_parts = []
    for path in sorted((support / "kindle-preview").rglob("*")):
        if path.suffix.lower() in (".html", ".htm", ".xhtml"):
            reader = Text()
            reader.feed(path.read_text())
            text = canonical(' '.join(reader.text))
            kindle_parts.append(text)
            if canonical(edition_label) in text:
                (support / "kindle-preview-path.txt").write_text(str(path.resolve()))
    kindle_text = ''.join(kindle_parts)
    assert (support / "kindle-preview-path.txt").is_file(), "Kindle copyright page missing"
    assert all(unit in kindle_text for unit in units), "AZW3 omitted manuscript text"
    for label, text in (("HTML", web_text), ("Markdown", markdown_text), ("AZW3", kindle_text)):
        assert canonical(edition_label) in text and canonical(display_date) in text, f"{label} edition/date mismatch"

    doc = pymupdf.open(folder / "wisdom.pdf")
    pages = []
    clipped = []
    for number, page in enumerate(doc):
        # Exclude running headers and folios before comparing paragraph content.
        pages.append(page.get_text(clip=pymupdf.Rect(0, 39, page.rect.width, page.rect.height - 38)))
        for word in page.get_text("words"):
            if word[0] < -1 or word[1] < -1 or word[2] > page.rect.width + 1 or word[3] > page.rect.height + 1:
                clipped.append(number + 1)
    pdf = canonical(' '.join(pages))
    missing = [unit for unit in units if unit not in pdf]
    assert not missing, f"PDF omitted {len(missing)} source passages: {missing[:3]}"
    assert not clipped, f"Text outside page bounds: {clipped}"
    copyright_pages = [n for n, text in enumerate(pages) if canonical(edition_label) in canonical(text)]
    assert copyright_pages == [2], f"Copyright must occupy one page immediately after the title: {copyright_pages}"
    assert canonical(edition["title"]) in canonical(pages[1]), "Title page must precede copyright"
    assert canonical(display_date) in canonical(pages[2]), "PDF copyright date differs from release"
    assert "Creative Commons" in pages[2] and "NonCommercial" in pages[2], "PDF license missing"
    assert any(link.get("uri") == license_url for link in doc[2].get_links()), "PDF license link missing"
    assert "Epigraphs" not in pages[2], "Copyright must not share its page with the epigraphs"
    assert not doc[2].get_text(clip=pymupdf.Rect(0, 0, 432, 39)).strip(), "Copyright page must have no running header"
    assert not doc[2].get_text(clip=pymupdf.Rect(0, 610, 432, 648)).strip(), "Copyright page must have no folio"
    empty_pages = [n + 1 for n, text in enumerate(pages) if n > 0 and len(text.strip()) <= 12 and not doc[n].get_image_info()]
    assert doc.get_toc(), "PDF bookmarks are missing"

    renders = support / "rendered"
    renders.mkdir(exist_ok=True)
    thumbs = []
    for number, page in enumerate(doc):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(.55, .55), alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        thumbs.append(image)
    for batch in range(0, len(thumbs), 12):
        tile_w, tile_h = thumbs[0].width + 16, thumbs[0].height + 28
        sheet = Image.new("RGB", (tile_w * 4, tile_h * 3), "#d9d5cf")
        draw = ImageDraw.Draw(sheet)
        for offset, thumb in enumerate(thumbs[batch:batch+12]):
            x, y = offset % 4 * tile_w + 8, offset // 4 * tile_h + 20
            sheet.paste(thumb, (x, y))
            draw.text((x, y - 16), str(batch + offset + 1), fill="black")
        sheet.save(renders / f"overview-{batch//12+1}.png")
    selected = sorted({0, 1, 2, 3, 4, 5, 8, len(doc)//2, len(doc)-2, len(doc)-1} & set(range(len(doc))))
    for number in selected:
        doc[number].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(renders / f"page-{number+1:03}.png")
    report = {"source_passages_checked": len(units), "epub_content_preserved": True,
              "pdf_content_preserved": True, "pdf_pages": len(doc), "pdf_bookmarks": len(doc.get_toc()),
              "empty_pages": empty_pages, "text_outside_pages": clipped, "pdf_fonts": sorted({font[3] for page in doc for font in page.get_fonts()}),
              "copyright_page": {"pdf_page": 3, "epub_spine_position": copyright_index + 1,
                                 "edition": edition["version"], "date": display_date, "license": "CC BY-NC 4.0"},
              "html_self_contained": True, "markdown_image_free": True,
              "html_content_preserved": True, "markdown_content_preserved": True, "azw3_content_preserved": True}
    (support / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    assert not empty_pages, f"Unexpected empty pages: {empty_pages}"
    assert any("sourceserif" in canonical(name) for name in report["pdf_fonts"]), "The book font was not embedded"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=Path("builds/ebooks"))
    validate(parser.parse_args().folder)
